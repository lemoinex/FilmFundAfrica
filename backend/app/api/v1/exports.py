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


def _dossier_filename(title: str, exportable: bool, extension: str) -> str:
    """Le nom dit l'état : il survit au téléchargement, l'écran non."""
    suffix = "dossier" if exportable else "dossier_BROUILLON"
    return _filename(f"{title}_{suffix}", extension)


def _attachment(content: bytes, media_type: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _agent_dossier_context(project, db):
    """Dossier, verdict et constats du dernier passage.

    Partage par les deux formats : leur decision d'affichage repose sur les
    memes faits, et les dupliquer les ferait diverger tot ou tard.
    """
    from sqlalchemy import select

    from app.agents import is_exportable
    from app.models.agents import AgentRun, DossierFinding
    from app.services.dossier_service import DossierService

    dossier = DossierService(db).get_or_create(project.id)
    last = db.scalar(
        select(AgentRun)
        .where(AgentRun.dossier_id == dossier.id)
        .order_by(AgentRun.created_at.desc())
        .limit(1)
    )
    if last is None:
        # Rien a exporter tant que la chaine n'a pas tourne : un document vide
        # serait plus deroutant qu'une erreur qui dit quoi faire.
        raise AppError("export.dossierNotBuilt", code="dossier_not_built")

    findings = list(
        db.scalars(
            select(DossierFinding).where(
                DossierFinding.dossier_id == dossier.id,
                DossierFinding.resolved_at.is_(None),
            )
        )
    )
    exportable = bool(last.verdict and is_exportable(last.verdict))
    return dossier, exportable, last.verdict, findings


@router.get("/pdf", summary="Exporter le dossier complet en PDF")
def export_pdf(project: OwnedProject, db: DbSession) -> Response:
    documents = DocumentService(db).documents.list_for_project(project.id)
    if not documents:
        raise AppError("export.nothingToExport", code="nothing_to_export")
    content = ExportService(db).dossier_to_pdf(project, documents)
    return _attachment(content, "application/pdf", _filename(project.title, "pdf"))


@router.get("/dossier/pdf", summary="Exporter le dossier de la chaîne d'agents en PDF")
def export_agent_dossier_pdf(project: OwnedProject, db: DbSession) -> Response:
    """Le dossier construit par la chaîne, en PDF.

    Deux documents selon l'état, et la différence est volontaire. Validé, le
    PDF est propre et destiné à un comité de lecture. Non validé, il porte
    « BROUILLON » dès la première page et liste les points à traiter — c'est
    la seule raison de le produire, et il ne doit pas pouvoir passer pour le
    document final.

    L'export n'est jamais refusé : un auteur a le droit de lire son travail en
    cours. Ce qui est interdit, c'est qu'un brouillon se présente comme abouti.
    """
    dossier, exportable, verdict, findings = _agent_dossier_context(project, db)
    content = ExportService(db).agent_dossier_to_pdf(
        project, dossier, exportable=exportable, verdict=verdict, findings=findings
    )
    return _attachment(
        content, "application/pdf", _dossier_filename(project.title, exportable, "pdf")
    )


@router.get("/dossier/docx", summary="Exporter le dossier de la chaîne d'agents en Word")
def export_agent_dossier_docx(project: OwnedProject, db: DbSession) -> Response:
    """Le même dossier, modifiable.

    Certains fonds n'acceptent que du Word, souvent parce qu'ils annotent le
    dossier avant de le rendre. Contenu et avertissements sont identiques au
    PDF : ils sont partagés, pas recopiés.
    """
    dossier, exportable, verdict, findings = _agent_dossier_context(project, db)
    content = ExportService(db).agent_dossier_to_docx(
        project, dossier, exportable=exportable, verdict=verdict, findings=findings
    )
    return _attachment(
        content,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        _dossier_filename(project.title, exportable, "docx"),
    )


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
