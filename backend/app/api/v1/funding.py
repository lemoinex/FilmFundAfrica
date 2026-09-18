"""Routes Funding Intelligence : recherche, matching, explication."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from app.core.deps import CurrentUser, DbSession, OwnedProject
from app.core.i18n import request_locale
from app.core.rate_limit import rate_limit_ai
from app.models.enums import FundingCategory, ProjectType
from app.schemas.funding import (
    MatchExplanation,
    MatchListResponse,
    OpportunityPage,
    OpportunityRead,
    OpportunitySearch,
    SortOption,
)
from app.services.funding_service import FundingService

router = APIRouter(prefix="/funding", tags=["Financements"])
project_router = APIRouter(prefix="/projects/{project_id}", tags=["Financements"])


@router.get("", response_model=OpportunityPage, summary="Rechercher des financements")
def search_funding(
    db: DbSession,
    _: CurrentUser,
    query: str | None = Query(default=None, max_length=200, description="Recherche plein texte"),
    country: str | None = Query(default=None, max_length=120),
    project_type: ProjectType | None = None,
    genre: str | None = Query(default=None, max_length=120),
    language: str | None = Query(default=None, max_length=60),
    category: FundingCategory | None = None,
    min_amount: float | None = Query(default=None, ge=0),
    max_amount: float | None = Query(default=None, ge=0),
    deadline_before: date | None = None,
    deadline_after: date | None = None,
    include_closed: bool = False,
    sort: SortOption = "deadline",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> OpportunityPage:
    """Recherche filtrée dans la base des dispositifs.

    Un dispositif dont un critère n'est pas renseigné (pays, genre, montant)
    reste visible : l'absence d'information n'est pas une exclusion.
    """
    return FundingService(db).search(
        OpportunitySearch(
            query=query,
            country=country,
            project_type=project_type,
            genre=genre,
            language=language,
            category=category,
            min_amount=min_amount,
            max_amount=max_amount,
            deadline_before=deadline_before,
            deadline_after=deadline_after,
            include_closed=include_closed,
            sort=sort,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/{opportunity_id}", response_model=OpportunityRead, summary="Fiche d'un dispositif")
def get_funding(opportunity_id: str, db: DbSession, _: CurrentUser) -> OpportunityRead:
    return FundingService(db).get(opportunity_id)


# ---------------------------------------------------------------------------
# Rapprochements d'un projet
# ---------------------------------------------------------------------------
@project_router.post(
    "/match-funding",
    response_model=MatchListResponse,
    summary="Analyser les financements compatibles",
)
def compute_matches(
    request: Request, project: OwnedProject, db: DbSession, current_user: CurrentUser
) -> MatchListResponse:
    """Calcule la compatibilité du projet avec tous les dispositifs ouverts.

    Le calcul est déterministe et ne consomme aucun crédit IA.
    """
    # La langue est relue ici, dans le corps : les dependances ont fini de
    # s'executer, et celle qui identifie le compte a pose sa preference.
    return FundingService(db, locale=request_locale(request)).compute_matches(
        project, notify_user=current_user
    )


@project_router.get(
    "/matches",
    response_model=MatchListResponse,
    summary="Financements compatibles du projet",
)
def list_matches(
    request: Request, project: OwnedProject, db: DbSession
) -> MatchListResponse:
    return FundingService(db, locale=request_locale(request)).stored_matches(project)


@project_router.post(
    "/matches/{opportunity_id}/explain",
    response_model=MatchExplanation,
    dependencies=[Depends(rate_limit_ai)],
    summary="Expliquer un rapprochement (1 crédit IA)",
)
def explain_match(
    opportunity_id: str,
    project: OwnedProject,
    db: DbSession,
    current_user: CurrentUser,
    refresh: bool = Query(
        default=False, description="Régénérer l'explication même si elle existe déjà"
    ),
) -> MatchExplanation:
    """Rédige l'analyse détaillée du rapprochement.

    Seule cette route consomme un crédit : le score, lui, reste gratuit. Une
    explication déjà produite est renvoyée sans nouveau débit.
    """
    return FundingService(db).explain_match(
        current_user, project, opportunity_id, refresh=refresh
    )
