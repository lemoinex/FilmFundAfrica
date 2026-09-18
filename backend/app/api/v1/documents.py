"""Routes AI Writer : documents, génération, retravail et versions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUser, DbSession, OwnedProject, Translator
from app.core.rate_limit import rate_limit_ai
from app.models.enums import DocumentType
from app.prompts import PROMPT_REGISTRY
from app.schemas.common import Message
from app.schemas.document import (
    DocumentRead,
    DocumentSummary,
    DocumentUpdate,
    DocumentVersionDetail,
    DocumentVersionRead,
    GenerateRequest,
    RefineRequest,
)
from app.schemas.job import GenerationJobRead
from app.services.document_service import DocumentService
from app.services.job_service import JobService

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["AI Writer"])
catalog_router = APIRouter(prefix="/documents", tags=["AI Writer"])


@catalog_router.get(
    "/screenplay-capacity",
    summary="Capacité de génération des scénarios",
)
def screenplay_capacity() -> dict:
    """Expose le découpage réel des scénarios longs.

    Le frontend s'en sert pour annoncer le coût en crédits AVANT de lancer la
    génération, et pour ne pas proposer une durée que le fournisseur configuré
    ne peut pas produire.
    """
    from app.prompts.base import SCREENPLAY_WORDS_PER_PAGE
    from app.services.ai.service import AIService
    from app.services.screenplay_service import (
        SCREENPLAY_MAX_TOKENS_PER_CALL,
        effective_max_passes,
        max_supported_minutes,
        pages_per_pass,
    )

    budget = AIService.effective_max_output_tokens(SCREENPLAY_MAX_TOKENS_PER_CALL)
    return {
        "pages_per_pass": pages_per_pass(budget),
        "max_passes": effective_max_passes(),
        "max_minutes": max_supported_minutes(budget),
        "words_per_page": SCREENPLAY_WORDS_PER_PAGE,
    }


@catalog_router.get("/types", summary="Catalogue des documents générables")
def document_types() -> list[dict]:
    """Expose les prompts disponibles et leur version au frontend."""
    return [
        {
            "document_type": str(document_type),
            "label": template.document_label,
            "prompt_name": template.name,
            "prompt_version": template.version,
            "outline": template.outline,
            "target_pages": template.target_pages,
            "depends_on": [str(dependency) for dependency in template.depends_on],
        }
        for document_type, template in PROMPT_REGISTRY.items()
    ]


@router.get("", response_model=list[DocumentSummary], summary="Documents du projet")
def list_documents(project: OwnedProject, db: DbSession) -> list[DocumentSummary]:
    documents = DocumentService(db).documents.list_for_project(project.id)
    return [DocumentSummary.model_validate(document) for document in documents]


@router.post(
    "/{document_type}/generate",
    response_model=GenerationJobRead,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit_ai)],
    summary="Lancer la génération d'un document",
)
def generate_document(
    document_type: DocumentType,
    payload: GenerateRequest,
    project: OwnedProject,
    db: DbSession,
    current_user: CurrentUser,
) -> GenerationJobRead:
    """Accepte la demande et renvoie la tâche qui l'exécute.

    Un scénario long enchaîne plusieurs appels au fournisseur : le tenir dans
    la requête HTTP la ferait expirer. Le frontend suit l'avancement sur
    `GET /jobs/{id}`.

    Sans worker disponible, la tâche est exécutée immédiatement : la réponse
    est alors déjà `SUCCEEDED` et porte son résultat. La forme de la réponse
    ne change pas — seul le temps d'attente change.
    """
    job = JobService(db).enqueue_generate(current_user, project, document_type, payload)
    return GenerationJobRead.model_validate(job)


@router.get("/{document_id}", response_model=DocumentRead, summary="Lire un document")
def get_document(document_id: str, project: OwnedProject, db: DbSession) -> DocumentRead:
    service = DocumentService(db)
    return DocumentRead.model_validate(service.get_owned_document(document_id, project))


@router.put("/{document_id}", response_model=DocumentRead, summary="Enregistrer un document")
def save_document(
    document_id: str, payload: DocumentUpdate, project: OwnedProject, db: DbSession
) -> DocumentRead:
    service = DocumentService(db)
    document = service.get_owned_document(document_id, project)
    return DocumentRead.model_validate(service.save_manual(project, document, payload))


@router.post(
    "/{document_id}/refine",
    response_model=GenerationJobRead,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit_ai)],
    summary="Améliorer, raccourcir, développer ou corriger",
)
def refine_document(
    document_id: str,
    payload: RefineRequest,
    project: OwnedProject,
    db: DbSession,
    current_user: CurrentUser,
) -> GenerationJobRead:
    document = DocumentService(db).get_owned_document(document_id, project)
    job = JobService(db).enqueue_refine(current_user, project, document, payload)
    return GenerationJobRead.model_validate(job)


@router.delete("/{document_id}", response_model=Message, summary="Supprimer un document")
def delete_document(
    document_id: str, project: OwnedProject, db: DbSession, t: Translator
) -> Message:
    service = DocumentService(db)
    service.delete(project, service.get_owned_document(document_id, project))
    return Message(detail=t("document.deleted"))


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------
@router.get(
    "/{document_id}/versions",
    response_model=list[DocumentVersionRead],
    summary="Historique des versions",
)
def list_versions(
    document_id: str, project: OwnedProject, db: DbSession
) -> list[DocumentVersionRead]:
    service = DocumentService(db)
    document = service.get_owned_document(document_id, project)
    return [
        DocumentVersionRead.model_validate(version)
        for version in service.versions.list_for_document(document.id)
    ]


@router.get(
    "/{document_id}/versions/{version_number}",
    response_model=DocumentVersionDetail,
    summary="Lire une version",
)
def get_version(
    document_id: str, version_number: int, project: OwnedProject, db: DbSession
) -> DocumentVersionDetail:
    from app.core.errors import NotFoundError

    service = DocumentService(db)
    document = service.get_owned_document(document_id, project)
    version = service.versions.get_version(document.id, version_number)
    if version is None:
        raise NotFoundError("document.versionNotFound")
    return DocumentVersionDetail.model_validate(version)


@router.post(
    "/{document_id}/versions/{version_number}/restore",
    response_model=DocumentRead,
    summary="Restaurer une version",
)
def restore_version(
    document_id: str, version_number: int, project: OwnedProject, db: DbSession
) -> DocumentRead:
    service = DocumentService(db)
    document = service.get_owned_document(document_id, project)
    return DocumentRead.model_validate(
        service.restore_version(project, document, version_number)
    )
