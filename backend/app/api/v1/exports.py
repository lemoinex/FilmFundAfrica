"""Routes d'export : PDF, DOCX, archive ZIP et budget XLSX."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.core.deps import DbSession, OwnedProject, require_export_access
from app.core.errors import AppError
from app.services.document_service import DocumentService
from app.services.export_service import ExportService

#: L'export est une fonctionnalité d'offre : la dépendance le vérifie pour
#: toutes les routes de ce routeur.
router = APIRouter(
    prefix="/projects/{project_id}/export",
    tags=["Export"],
    dependencies=[Depends(require_export_access)],
)


def _filename(value: str, extension: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip()
    slug = re.sub(r"[\s-]+", "_", slug) or "dossier"
    return f"{slug}.{extension}"


def _attachment(content: bytes, media_type: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/pdf", summary="Exporter le dossier complet en PDF")
def export_pdf(project: OwnedProject, db: DbSession) -> Response:
    documents = DocumentService(db).documents.list_for_project(project.id)
    if not documents:
        raise AppError("export.nothingToExport", code="nothing_to_export")
    content = ExportService(db).dossier_to_pdf(project, documents)
    return _attachment(content, "application/pdf", _filename(project.title, "pdf"))


@router.get("/docx/{document_id}", summary="Exporter un document en Word")
def export_docx(document_id: str, project: OwnedProject, db: DbSession) -> Response:
    service = DocumentService(db)
    document = service.get_owned_document(document_id, project)
    content = ExportService(db).document_to_docx(document, project)
    return _attachment(
        content,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        _filename(document.title, "docx"),
    )


@router.get("/zip", summary="Exporter tout le projet en archive ZIP")
def export_zip(project: OwnedProject, db: DbSession) -> Response:
    content = ExportService(db).project_to_zip(project)
    return _attachment(content, "application/zip", _filename(project.title, "zip"))


@router.get("/xlsx", summary="Exporter le budget et le plan de financement en tableur")
def export_budget_xlsx(project: OwnedProject, db: DbSession) -> Response:
    """Classeur à trois feuilles : budget, plan de financement, calendrier.

    Les totaux y sont des formules : un financeur qui corrige un prix voit le
    total suivre, au lieu de lire un chiffre figé qui ne correspond plus.
    """
    content = ExportService(db).budget_to_xlsx(project)
    return _attachment(
        content,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        _filename(f"{project.title}_budget", "xlsx"),
    )
