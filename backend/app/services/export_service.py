"""Export du dossier : PDF, DOCX, archive ZIP et budget XLSX.

Le rendu prend en charge un sous-ensemble de Markdown suffisant pour les
documents produits par l'AI Writer : titres `#` a `####`, listes a puces,
gras `**` et italique `*`, citations `>`.
"""

from __future__ import annotations

import io
import re
import zipfile
from datetime import date

from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.project import Project
from app.repositories.document import DocumentRepository

INLINE_BOLD = re.compile(r"\*\*(.+?)\*\*")
INLINE_ITALIC = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip()
    return re.sub(r"[\s-]+", "_", cleaned) or "document"


def _escape_xml(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline_to_reportlab(text: str) -> str:
    escaped = _escape_xml(text)
    escaped = INLINE_BOLD.sub(r"<b>\1</b>", escaped)
    escaped = INLINE_ITALIC.sub(r"<i>\1</i>", escaped)
    return escaped


def _strip_inline(text: str) -> str:
    return INLINE_ITALIC.sub(r"\1", INLINE_BOLD.sub(r"\1", text))


class ExportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.documents = DocumentRepository(db)

    # ------------------------------------------------------------------
    def document_to_docx(self, document: Document, project: Project) -> bytes:
        docx = DocxDocument()
        style = docx.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(11)

        heading = docx.add_heading(project.title, level=0)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle = docx.add_paragraph(document.title)
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle.runs[0].font.color.rgb = RGBColor(0x6B, 0x6B, 0x6B)
        docx.add_paragraph()

        for line in document.content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                level = min(len(stripped) - len(stripped.lstrip("#")), 4)
                docx.add_heading(_strip_inline(stripped.lstrip("# ").strip()), level=level)
            elif stripped.startswith((">", "|")):
                paragraph = docx.add_paragraph(_strip_inline(stripped.lstrip("> ").strip()))
                paragraph.runs[0].italic = True
            elif stripped.startswith(("-", "*", "•")) and not stripped.startswith("**"):
                docx.add_paragraph(
                    _strip_inline(stripped.lstrip("-*• ").strip()), style="List Bullet"
                )
            elif re.match(r"^\d+\.\s", stripped):
                docx.add_paragraph(
                    _strip_inline(re.sub(r"^\d+\.\s", "", stripped)), style="List Number"
                )
            else:
                docx.add_paragraph(_strip_inline(stripped))

        buffer = io.BytesIO()
        docx.save(buffer)
        return buffer.getvalue()

    # ------------------------------------------------------------------
    def dossier_to_pdf(self, project: Project, documents: list[Document]) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2.2 * cm,
            rightMargin=2.2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            title=f"{project.title} — dossier",
            author="FilmFund Africa",
        )
        styles = getSampleStyleSheet()
        body = ParagraphStyle(
            "BodyJustified",
            parent=styles["BodyText"],
            alignment=TA_JUSTIFY,
            fontSize=10.5,
            leading=15,
            spaceAfter=6,
        )
        cover_title = ParagraphStyle(
            "CoverTitle", parent=styles["Title"], fontSize=26, leading=30, spaceAfter=18
        )

        story: list = [
            Spacer(1, 4 * cm),
            Paragraph(_escape_xml(project.title), cover_title),
            Paragraph(
                _escape_xml(
                    " · ".join(
                        part
                        for part in [
                            str(project.project_type).replace("_", " ").title(),
                            project.genre,
                            f"{project.duration} min" if project.duration else None,
                            project.country,
                        ]
                        if part
                    )
                ),
                styles["Heading3"],
            ),
        ]
        if project.logline:
            story.extend([Spacer(1, 1 * cm), Paragraph(_inline_to_reportlab(project.logline), body)])
        story.extend(
            [
                Spacer(1, 3 * cm),
                Paragraph(
                    f"Dossier généré le {date.today():%d/%m/%Y} — FilmFund Africa",
                    styles["Normal"],
                ),
                PageBreak(),
            ]
        )

        for index, document in enumerate(documents):
            story.append(Paragraph(_escape_xml(document.title), styles["Heading1"]))
            story.append(Spacer(1, 0.4 * cm))
            story.extend(self._markdown_to_flowables(document.content, body, styles))
            if index < len(documents) - 1:
                story.append(PageBreak())

        doc.build(story)
        return buffer.getvalue()

    @staticmethod
    def _markdown_to_flowables(content: str, body: ParagraphStyle, styles) -> list:
        flowables: list = []
        bullets: list[str] = []

        def flush_bullets() -> None:
            if bullets:
                flowables.append(
                    ListFlowable(
                        [ListItem(Paragraph(item, body)) for item in bullets],
                        bulletType="bullet",
                        leftIndent=14,
                    )
                )
                bullets.clear()

        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                flush_bullets()
                continue
            if stripped.startswith("#"):
                flush_bullets()
                level = min(len(stripped) - len(stripped.lstrip("#")), 4)
                heading_style = styles[f"Heading{min(level + 1, 4)}"]
                flowables.append(
                    Paragraph(_inline_to_reportlab(stripped.lstrip("# ").strip()), heading_style)
                )
            elif stripped.startswith(("-", "*", "•")) and not stripped.startswith("**"):
                bullets.append(_inline_to_reportlab(stripped.lstrip("-*• ").strip()))
            elif stripped.startswith(">"):
                flush_bullets()
                flowables.append(
                    Paragraph(f"<i>{_inline_to_reportlab(stripped.lstrip('> ').strip())}</i>", body)
                )
            else:
                flush_bullets()
                flowables.append(Paragraph(_inline_to_reportlab(stripped), body))
        flush_bullets()
        return flowables

    # ------------------------------------------------------------------
    def project_to_zip(self, project: Project) -> bytes:
        documents = self.documents.list_for_project(project.id)
        buffer = io.BytesIO()
        folder = _slugify(project.title)

        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for document in documents:
                name = _slugify(document.title)
                archive.writestr(
                    f"{folder}/{name}.docx", self.document_to_docx(document, project)
                )
                archive.writestr(f"{folder}/{name}.md", document.content)
            if documents:
                archive.writestr(
                    f"{folder}/Dossier_complet.pdf", self.dossier_to_pdf(project, documents)
                )
            archive.writestr(f"{folder}/PROJET.md", self._project_sheet(project))

        return buffer.getvalue()

    # ------------------------------------------------------------------
    def budget_to_xlsx(self, project: Project) -> bytes:
        """Classeur a trois feuilles : budget, plan de financement, calendrier.

        Les totaux sont ecrits comme des FORMULES et non comme des valeurs :
        un financeur qui corrige un prix dans le tableur doit voir le total
        suivre, sans quoi le document mentirait des la premiere modification.
        """
        from app.services.budget_service import BudgetService
        from app.services.budget_templates import CATEGORY_ORDER

        service = BudgetService(self.db)
        budget = project.budget
        plan = project.funding_plan
        currency = budget.currency if budget else "XAF"

        workbook = Workbook()
        self._budget_sheet(workbook.active, project, budget, currency, CATEGORY_ORDER)
        self._plan_sheet(workbook.create_sheet("Plan de financement"), service, plan, currency)
        self._schedule_sheet(workbook.create_sheet("Calendrier"), service, project)

        buffer = io.BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()

    # ------------------------------------------------------------------
    @staticmethod
    def _title_row(sheet, row: int, text: str, width: int) -> int:
        cell = sheet.cell(row=row, column=1, value=text)
        cell.font = Font(bold=True, size=14)
        sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=width)
        return row + 2

    @staticmethod
    def _header_row(sheet, row: int, labels: list[str]) -> int:
        fill = PatternFill("solid", fgColor="1F2933")
        for column, label in enumerate(labels, start=1):
            cell = sheet.cell(row=row, column=column, value=label)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = fill
            cell.alignment = Alignment(horizontal="center")
        return row + 1

    def _budget_sheet(self, sheet, project, budget, currency: str, order) -> None:
        sheet.title = "Budget"
        row = self._title_row(sheet, 1, f"Budget prévisionnel — {project.title}", 6)
        row = self._header_row(
            sheet, row, ["Phase", "Poste", "Quantité", "Unité", f"Prix unitaire ({currency})", f"Montant ({currency})"]
        )

        subtotal_rows: list[int] = []
        items = list(budget.items) if budget else []
        for category in order:
            lines = [item for item in items if item.category == category]
            if not lines:
                continue
            first = row
            for item in lines:
                sheet.cell(row=row, column=1, value=str(category))
                sheet.cell(row=row, column=2, value=item.label)
                sheet.cell(row=row, column=3, value=item.quantity)
                sheet.cell(row=row, column=4, value=item.unit or "")
                sheet.cell(row=row, column=5, value=item.unit_price)
                # Le montant se recalcule dans le tableur, comme dans l'application.
                sheet.cell(row=row, column=6, value=f"=C{row}*E{row}")
                row += 1

            label = sheet.cell(row=row, column=2, value=f"Sous-total {category}")
            label.font = Font(bold=True)
            total = sheet.cell(row=row, column=6, value=f"=SUM(F{first}:F{row - 1})")
            total.font = Font(bold=True)
            subtotal_rows.append(row)
            row += 2

        label = sheet.cell(row=row, column=2, value="TOTAL")
        label.font = Font(bold=True, size=12)
        formula = "+".join(f"F{line}" for line in subtotal_rows) or "0"
        grand_total = sheet.cell(row=row, column=6, value=f"={formula}")
        grand_total.font = Font(bold=True, size=12)

        if not items:
            sheet.cell(
                row=row + 2,
                column=2,
                value="Budget vide : installez la trame depuis l'application, puis chiffrez chaque poste.",
            )

        for column, width in enumerate([22, 46, 10, 12, 18, 18], start=1):
            sheet.column_dimensions[get_column_letter(column)].width = width

    def _plan_sheet(self, sheet, service, plan, currency: str) -> None:
        row = self._title_row(sheet, 1, "Plan de financement", 5)
        row = self._header_row(
            sheet, row, ["Type de source", "Source", f"Montant ({currency})", "Acquis", "Date attendue"]
        )

        lines = list(plan.lines) if plan else []
        first = row
        for line in lines:
            sheet.cell(row=row, column=1, value=str(line.source_type))
            sheet.cell(row=row, column=2, value=line.source_name or "")
            sheet.cell(row=row, column=3, value=line.amount)
            sheet.cell(row=row, column=4, value="Oui" if line.is_secured else "Non")
            sheet.cell(row=row, column=5, value=line.expected_date)
            row += 1

        summary = service.plan_summary(plan)
        row += 1
        for label, value in (
            ("Budget total", summary["total_budget"]),
            ("Financement acquis", summary["secured_amount"]),
            ("Financement identifié (acquis + espéré)", summary["identified_amount"]),
            ("Reste à financer", summary["sought_amount"]),
            ("Non couvert, même par les sources espérées", summary["uncovered_amount"]),
        ):
            sheet.cell(row=row, column=2, value=label).font = Font(bold=True)
            sheet.cell(row=row, column=3, value=value)
            row += 1

        if lines:
            sheet.cell(row=row, column=2, value="Somme des lignes ci-dessus").font = Font(italic=True)
            sheet.cell(row=row, column=3, value=f"=SUM(C{first}:C{first + len(lines) - 1})")

        for column, width in enumerate([22, 40, 18, 10, 16], start=1):
            sheet.column_dimensions[get_column_letter(column)].width = width

    def _schedule_sheet(self, sheet, service, project) -> None:
        row = self._title_row(sheet, 1, "Calendrier de production", 4)
        row = self._header_row(sheet, row, ["Phase", "Début", "Fin", "Notes"])

        phases = service.list_schedule(project)
        for phase in phases:
            sheet.cell(row=row, column=1, value=str(phase.phase))
            sheet.cell(row=row, column=2, value=phase.start_date)
            sheet.cell(row=row, column=3, value=phase.end_date)
            sheet.cell(row=row, column=4, value=phase.notes or "")
            row += 1

        if not phases:
            sheet.cell(row=row, column=1, value="Calendrier non renseigné.")

        for column, width in enumerate([24, 14, 14, 50], start=1):
            sheet.column_dimensions[get_column_letter(column)].width = width

    @staticmethod
    def _project_sheet(project: Project) -> str:
        lines = [
            f"# {project.title}",
            "",
            f"- Type : {project.project_type}",
            f"- Genre : {project.genre or 'Information non fournie.'}",
            f"- Pays : {project.country or 'Information non fournie.'}",
            f"- Langue : {project.language}",
            f"- Durée : {f'{project.duration} min' if project.duration else 'Information non fournie.'}",
            f"- Statut : {project.status}",
            f"- Score de maturité : {project.readiness_score if project.readiness_score is not None else '—'}/100",
            "",
            "## Logline",
            "",
            project.logline or "Information non fournie.",
            "",
            "## Personnages",
            "",
        ]
        if project.characters:
            for character in project.characters:
                lines.append(
                    f"- **{character.name}** — {character.role or 'rôle non précisé'} : "
                    f"{character.description or 'Information non fournie.'}"
                )
        else:
            lines.append("Information non fournie.")
        return "\n".join(lines)
