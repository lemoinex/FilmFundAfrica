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
from reportlab.lib import colors
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

    # ------------------------------------------------------------------
    def agent_dossier_to_pdf(
        self,
        project: Project,
        dossier,
        *,
        exportable: bool,
        verdict: str | None,
        findings: list | None = None,
    ) -> bytes:
        """Le dossier construit par la chaine d'agents, en PDF.

        Deux documents differents selon l'etat, et c'est voulu.

        **Validé** : un dossier propre, destine a un comite de lecture. Les
        constats internes n'y figurent pas — ils relevent de l'assurance
        qualite, et les exposer a un financeur desservirait le projet.

        **Non validé** : le meme contenu, mais marque « brouillon » des la
        premiere page et suivi des constats a traiter. C'est la seule raison
        de produire ce PDF-la, et il ne doit jamais pouvoir passer pour le
        document final.
        """
        buffer = io.BytesIO()
        label = "dossier" if exportable else "brouillon"
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2.2 * cm,
            rightMargin=2.2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            title=f"{project.title} — {label}",
            author="FilmFund Africa",
        )
        styles = getSampleStyleSheet()
        body = ParagraphStyle(
            "DossierBody",
            parent=styles["BodyText"],
            alignment=TA_JUSTIFY,
            fontSize=10.5,
            leading=15,
            spaceAfter=6,
        )
        cover_title = ParagraphStyle(
            "DossierCover", parent=styles["Title"], fontSize=26, leading=30, spaceAfter=18
        )
        warning = ParagraphStyle(
            "DossierWarning",
            parent=styles["BodyText"],
            fontSize=12,
            leading=17,
            # Un avertissement en noir se lit comme du corps de texte : la
            # couleur est ce qui empeche de prendre un brouillon pour un final.
            textColor=colors.HexColor("#B03812"),
            spaceAfter=10,
        )

        story: list = [Spacer(1, 3.5 * cm), Paragraph(_escape_xml(project.title), cover_title)]

        meta = " · ".join(
            part
            for part in [
                str(project.project_type).replace("_", " ").title(),
                project.genre,
                f"{project.duration} min" if project.duration else None,
                project.country,
            ]
            if part
        )
        if meta:
            story.append(Paragraph(_escape_xml(meta), styles["Heading3"]))

        story.append(Spacer(1, 1 * cm))
        story.extend(self._dossier_banner(dossier, exportable, verdict, warning, body))
        story.extend(
            [
                Spacer(1, 2 * cm),
                Paragraph(
                    f"Généré le {date.today():%d/%m/%Y} — FilmFund Africa",
                    styles["Normal"],
                ),
                PageBreak(),
            ]
        )

        story.extend(self._dossier_sections(dossier, body, styles))

        if not exportable and findings:
            story.append(PageBreak())
            story.extend(self._dossier_findings(findings, body, styles))

        doc.build(story)
        return buffer.getvalue()

    # ------------------------------------------------------------------
    @staticmethod
    def _dossier_banner(dossier, exportable: bool, verdict, warning, body) -> list:
        """Ce que le lecteur doit savoir avant la premiere ligne du dossier."""
        blocks: list = []
        if exportable:
            lead, rest = VALIDATED_NOTICE
            blocks.append(Paragraph(f"<b>{_escape_xml(lead)}</b> {_escape_xml(rest)}", body))
        else:
            lead, rest = DRAFT_WARNING
            blocks.append(
                Paragraph(f"<b>{_escape_xml(lead)}</b> {_escape_xml(rest)}", warning)
            )
        if verdict:
            # Le libellé, pas la valeur de l'énumération : « BLOCKED » dans un
            # document français destiné à être lu par un tiers fait négligé.
            label = VERDICT_LABELS.get(str(verdict), str(verdict))
            blocks.append(Paragraph(f"Verdict du dernier contrôle : {label}", body))

        # La logline porte son statut de provenance : une hypothese ne doit pas
        # se lire comme un fait etabli, meme dans un brouillon.
        logline = getattr(dossier, "logline", None) or {}
        if logline.get("value"):
            blocks.append(Spacer(1, 0.6 * cm))
            blocks.append(Paragraph(_inline_to_reportlab(str(logline["value"])), body))
            if logline.get("status") not in TRUSTED_STATUSES:
                blocks.append(
                    Paragraph(f"<i>{_escape_xml(UNVERIFIED_NOTICE)}</i>", body)
                )
        return blocks

    # ------------------------------------------------------------------
    @staticmethod
    def _dossier_sections(dossier, body, styles) -> list:
        """Les sections remplies, dans l'ordre de la chaine.

        Une section vide est passee : un titre suivi de rien laisserait croire
        a un oubli de mise en page plutot qu'a une etape non faite.
        """
        story: list = []
        rendered = 0
        for attribute, label in DOSSIER_SECTIONS:
            content = getattr(dossier, attribute, None) or {}
            if not content:
                continue
            if rendered:
                story.append(Spacer(1, 0.8 * cm))
            story.append(Paragraph(_escape_xml(label), styles["Heading1"]))
            story.append(Spacer(1, 0.3 * cm))
            for key, value in content.items():
                story.append(
                    Paragraph(
                        f"<b>{_escape_xml(str(key))}</b> : "
                        f"{_escape_xml(_render_value(value))}",
                        body,
                    )
                )
            rendered += 1

        if rendered == 0:
            story.append(Paragraph(_escape_xml(EMPTY_DOSSIER_NOTICE), body))
        return story

    # ------------------------------------------------------------------
    @staticmethod
    def _dossier_findings(findings: list, body, styles) -> list:
        """Les constats a traiter, avec l'agent capable de les corriger."""
        story: list = [
            Paragraph(FINDINGS_TITLE, styles["Heading1"]),
            Spacer(1, 0.3 * cm),
            Paragraph(_escape_xml(FINDINGS_NOTICE), body),
            Spacer(1, 0.4 * cm),
        ]
        for finding in findings:
            severity = SEVERITY_LABELS.get(str(finding.severity), str(finding.severity))
            owner = AGENT_LABELS.get(str(finding.owner or ""), "")
            story.append(
                Paragraph(
                    f"<b>{_escape_xml(severity)} — {_escape_xml(finding.element)}</b>",
                    body,
                )
            )
            story.append(Paragraph(_escape_xml(finding.description), body))
            if owner:
                story.append(Paragraph(f"<i>À corriger par : {_escape_xml(owner)}</i>", body))
            if finding.suggested_correction:
                story.append(
                    Paragraph(
                        f"<i>Proposition : {_escape_xml(finding.suggested_correction)}</i>",
                        body,
                    )
                )
            story.append(Spacer(1, 0.35 * cm))
        return story

    # ------------------------------------------------------------------
    def agent_dossier_to_docx(
        self,
        project: Project,
        dossier,
        *,
        exportable: bool,
        verdict: str | None,
        findings: list | None = None,
    ) -> bytes:
        """Le dossier de la chaine en Word, aux memes regles que le PDF.

        Certains fonds n'acceptent que du Word, et souvent parce qu'ils
        annotent le dossier avant de le rendre. Le contenu et les
        avertissements sont donc identiques au PDF — ils sont partages — mais
        le document reste modifiable, ce qui est tout l'interet du format.
        """
        docx = DocxDocument()
        style = docx.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(11)

        heading = docx.add_heading(project.title, level=0)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

        meta = " · ".join(
            part
            for part in [
                str(project.project_type).replace("_", " ").title(),
                project.genre,
                f"{project.duration} min" if project.duration else None,
                project.country,
            ]
            if part
        )
        if meta:
            subtitle = docx.add_paragraph(meta)
            subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
            subtitle.runs[0].font.color.rgb = RGBColor(0x6B, 0x6B, 0x6B)

        docx.add_paragraph()
        self._docx_banner(docx, dossier, exportable, verdict)
        docx.add_paragraph()
        docx.add_paragraph(f"Généré le {date.today():%d/%m/%Y} — FilmFund Africa")

        self._docx_sections(docx, dossier)

        if not exportable and findings:
            docx.add_page_break()
            self._docx_findings(docx, findings)

        buffer = io.BytesIO()
        docx.save(buffer)
        return buffer.getvalue()

    # ------------------------------------------------------------------
    @staticmethod
    def _docx_banner(docx, dossier, exportable: bool, verdict) -> None:
        lead, rest = VALIDATED_NOTICE if exportable else DRAFT_WARNING
        paragraph = docx.add_paragraph()
        run = paragraph.add_run(lead)
        run.bold = True
        if not exportable:
            # Le gras seul ne suffit pas : dans un document que l'on parcourt,
            # c'est la couleur qui empeche de confondre brouillon et final.
            run.font.color.rgb = RGBColor(0xB0, 0x38, 0x12)
        paragraph.add_run(" " + rest)

        if verdict:
            label = VERDICT_LABELS.get(str(verdict), str(verdict))
            docx.add_paragraph(f"Verdict du dernier contrôle : {label}")

        logline = getattr(dossier, "logline", None) or {}
        if logline.get("value"):
            docx.add_paragraph()
            docx.add_paragraph(str(logline["value"]))
            if logline.get("status") not in TRUSTED_STATUSES:
                unverified = docx.add_paragraph(UNVERIFIED_NOTICE)
                unverified.runs[0].italic = True

    # ------------------------------------------------------------------
    @staticmethod
    def _docx_sections(docx, dossier) -> None:
        rendered = 0
        for attribute, label in DOSSIER_SECTIONS:
            content = getattr(dossier, attribute, None) or {}
            if not content:
                continue
            docx.add_heading(label, level=1)
            for key, value in content.items():
                paragraph = docx.add_paragraph()
                paragraph.add_run(f"{key} : ").bold = True
                paragraph.add_run(_render_value(value))
            rendered += 1

        if rendered == 0:
            docx.add_paragraph(EMPTY_DOSSIER_NOTICE)

    # ------------------------------------------------------------------
    @staticmethod
    def _docx_findings(docx, findings: list) -> None:
        docx.add_heading(FINDINGS_TITLE, level=1)
        notice = docx.add_paragraph(FINDINGS_NOTICE)
        notice.runs[0].italic = True

        for finding in findings:
            severity = SEVERITY_LABELS.get(str(finding.severity), str(finding.severity))
            paragraph = docx.add_paragraph()
            paragraph.add_run(f"{severity} — {finding.element}").bold = True
            docx.add_paragraph(finding.description)
            owner = AGENT_LABELS.get(str(finding.owner or ""), "")
            if owner:
                line = docx.add_paragraph(f"À corriger par : {owner}")
                line.runs[0].italic = True
            if finding.suggested_correction:
                line = docx.add_paragraph(f"Proposition : {finding.suggested_correction}")
                line.runs[0].italic = True

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


#: Avertissements portes par le dossier exporte, quel que soit le format.
#:
#: Partages entre le PDF et le DOCX a dessein : s'ils divergeaient, un des deux
#: formats finirait par etre moins clair que l'autre sur ce qui compte le plus
#: — qu'un brouillon ne passe pas pour un document abouti.
#:
#: Chacun se lit en deux parties : une amorce mise en valeur, puis le reste.
DRAFT_WARNING = (
    "BROUILLON — dossier non validé.",
    "Les contrôles ont relevé des points à traiter : ce document ne doit pas être "
    "soumis en l'état. Les constats figurent en fin de document.",
)

VALIDATED_NOTICE = (
    "Dossier contrôlé.",
    "Une relecture humaine reste due avant toute soumission : ce document est une "
    "aide à la constitution, pas une garantie d'éligibilité.",
)

#: Une information dont la provenance n'est pas etablie ne doit pas se lire
#: comme un fait, meme dans un brouillon.
UNVERIFIED_NOTICE = "Information non vérifiée — à confirmer avant soumission."

FINDINGS_TITLE = "Points à traiter"
FINDINGS_NOTICE = (
    "Cette section est interne : elle n'a pas vocation à être transmise à un financeur."
)

EMPTY_DOSSIER_NOTICE = (
    "Aucune section n'a encore été produite. Lancez la chaîne d'agents pour "
    "construire le dossier."
)


#: Sections du dossier d'agents, dans l'ordre ou la chaine les remplit.
DOSSIER_SECTIONS: tuple[tuple[str, str], ...] = (
    ("concept", "Concept"),
    ("synopsis", "Synopsis"),
    ("screenplay", "Scénario"),
    ("director_vision", "Vision de réalisation"),
    ("production_plan", "Plan de production"),
    ("budget", "Budget"),
    ("financing_plan", "Plan de financement"),
    ("cultural_analysis", "Analyse culturelle"),
    ("impact_analysis", "Impact"),
)

#: Statuts d'information qui engagent un dossier. Les autres sont signales.
TRUSTED_STATUSES = frozenset({"VERIFIED", "PROVIDED_BY_USER"})

SEVERITY_LABELS = {
    "CRITICAL": "Bloquant",
    "MAJOR": "Important",
    "MINOR": "Mineur",
    "PASS": "Conforme",
}

VERDICT_LABELS = {
    "PASS": "conforme",
    "PASS_WITH_WARNINGS": "conforme, avec réserves",
    "REQUIRES_CORRECTION": "à corriger",
    "BLOCKED": "bloqué",
}

AGENT_LABELS = {
    "DEVELOPMENT": "Développement",
    "SCREENWRITER": "Scénario",
    "DIRECTOR": "Réalisation",
    "PRODUCER": "Production",
    "FINANCING": "Financement",
    "IMPACT": "Impact",
    "CONSISTENCY_VALIDATOR": "Contrôle de cohérence",
    "FUNDING_PACKAGE_VALIDATOR": "Contrôle du dossier",
}


def _render_value(value) -> str:
    """Rend une valeur de section en texte lisible.

    Les sections sont des dictionnaires libres : leur contenu change d'un
    projet a l'autre, et l'export ne peut pas presumer de leur forme.
    """
    if isinstance(value, list):
        return " · ".join(_render_value(item) for item in value)
    if isinstance(value, dict):
        return " · ".join(f"{key} : {_render_value(item)}" for key, item in value.items())
    if isinstance(value, bool):
        return "oui" if value else "non"
    return str(value)
