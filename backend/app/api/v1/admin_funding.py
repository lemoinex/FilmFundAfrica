"""Administration de la base des dispositifs de financement.

Règle tenue par ces routes : on ne peut pas publier un dispositif comme
ouvert sans son URL source, et chaque vérification humaine met à jour
`last_verified_at`. C'est ce qui permet à l'interface d'afficher, à côté de
chaque opportunité, d'où elle vient et quand elle a été contrôlée.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentAdmin, DbSession
from app.models.enums import FundingStatus
from app.schemas.common import Message
from app.schemas.funding import (
    OpportunityCreate,
    OpportunityPage,
    OpportunityRead,
    OpportunitySearch,
    OpportunityUpdate,
    RequirementCreate,
)
from app.services.funding_service import FundingService

router = APIRouter(prefix="/admin/funding", tags=["Administration"])


@router.get("", response_model=OpportunityPage, summary="Lister les dispositifs")
def list_opportunities(
    db: DbSession,
    _: CurrentAdmin,
    query: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> OpportunityPage:
    """Vue d'administration : inclut les dispositifs clos et non vérifiés."""
    return FundingService(db).search(
        OpportunitySearch(
            query=query,
            include_closed=True,
            include_demo=True,
            sort="recent",
            page=page,
            page_size=page_size,
        )
    )


@router.post(
    "",
    response_model=OpportunityRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter un dispositif",
)
def create_opportunity(
    payload: OpportunityCreate, db: DbSession, _: CurrentAdmin
) -> OpportunityRead:
    return FundingService(db).create(payload)


@router.get("/{opportunity_id}", response_model=OpportunityRead, summary="Lire un dispositif")
def read_opportunity(opportunity_id: str, db: DbSession, _: CurrentAdmin) -> OpportunityRead:
    return FundingService(db).get(opportunity_id)


@router.put("/{opportunity_id}", response_model=OpportunityRead, summary="Modifier un dispositif")
def update_opportunity(
    opportunity_id: str, payload: OpportunityUpdate, db: DbSession, _: CurrentAdmin
) -> OpportunityRead:
    return FundingService(db).update(opportunity_id, payload)


@router.post(
    "/{opportunity_id}/verify",
    response_model=OpportunityRead,
    summary="Marquer comme vérifié",
)
def verify_opportunity(
    opportunity_id: str,
    db: DbSession,
    _: CurrentAdmin,
    new_status: FundingStatus = Query(
        default=FundingStatus.OPEN, description="Statut à appliquer après vérification"
    ),
) -> OpportunityRead:
    """Horodate la vérification et applique le statut choisi.

    Exige une URL source : sans elle, la fiche ne peut pas être présentée
    comme active aux utilisateurs.
    """
    return FundingService(db).mark_verified(opportunity_id, new_status)


@router.delete("/{opportunity_id}", response_model=Message, summary="Supprimer un dispositif")
def delete_opportunity(opportunity_id: str, db: DbSession, _: CurrentAdmin) -> Message:
    FundingService(db).delete(opportunity_id)
    return Message(detail="Dispositif supprimé.")


# ---------------------------------------------------------------------------
# Pièces exigées
# ---------------------------------------------------------------------------
@router.post(
    "/{opportunity_id}/requirements",
    response_model=OpportunityRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter une pièce exigée",
)
def add_requirement(
    opportunity_id: str, payload: RequirementCreate, db: DbSession, _: CurrentAdmin
) -> OpportunityRead:
    return FundingService(db).add_requirement(opportunity_id, payload)


@router.delete(
    "/{opportunity_id}/requirements/{requirement_id}",
    response_model=OpportunityRead,
    summary="Retirer une pièce exigée",
)
def delete_requirement(
    opportunity_id: str, requirement_id: str, db: DbSession, _: CurrentAdmin
) -> OpportunityRead:
    return FundingService(db).delete_requirement(opportunity_id, requirement_id)
