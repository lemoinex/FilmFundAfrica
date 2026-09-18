"""Export du dossier : PDF, DOCX et archive ZIP.

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
