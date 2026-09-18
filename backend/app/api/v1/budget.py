"""Routes du budget previsionnel, du plan de financement et du calendrier."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import DbSession, OwnedProject
from app.core.errors import NotFoundError
from app.models.enums import BudgetCategory
from app.schemas.budget import (
    BudgetGenerateRequest,
    BudgetItemCreate,
    BudgetItemRead,
    BudgetItemUpdate,
    BudgetRead,
    BudgetUpdate,
    CategoryTotal,
    FundingPlanLineCreate,
    FundingPlanLineRead,
    FundingPlanLineUpdate,
    FundingPlanRead,
    SchedulePhaseRead,
    SchedulePhaseUpsert,
)
from app.schemas.common import Message
from app.services.budget_service import BudgetService
from app.services.scoring_service import ScoringService

router = APIRouter(prefix="/projects/{project_id}", tags=["Budget"])


def _read(service: BudgetService, project) -> BudgetRead:
    budget = service.get_or_create(project)
    data = BudgetRead.model_validate(budget)
    return data.model_copy(
        update={
            "totals_by_category": [
                CategoryTotal.model_validate(total)
                for total in service.totals_by_category(budget)
            ]
        }
    )


def _commit(db, project, service: BudgetService) -> None:
    """Enregistre, puis recalcule le score de maturité du projet.

    Le critère « Budget » du Project Readiness Score lit ces tables : sans ce
    recalcul, l'auteur chiffrerait son dossier sans voir son score bouger.
    """
    db.commit()
    db.refresh(project)
    ScoringService(db).compute(project)


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------
@router.get("/budget", response_model=BudgetRead, summary="Budget prévisionnel")
def get_budget(project: OwnedProject, db: DbSession) -> BudgetRead:
    service = BudgetService(db)
    data = _read(service, project)
    db.commit()
    return data


@router.put("/budget", response_model=BudgetRead, summary="Devise et notes du budget")
def update_budget(payload: BudgetUpdate, project: OwnedProject, db: DbSession) -> BudgetRead:
    service = BudgetService(db)
    budget = service.get_or_create(project, currency=payload.currency)
    if payload.notes is not None:
        budget.notes = payload.notes
    service.recompute(project, budget)
    data = _read(service, project)
    _commit(db, project, service)
    return data


@router.post(
    "/budget/generate",
    response_model=BudgetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Installer la trame de postes du type de projet",
)
def generate_budget(
    payload: BudgetGenerateRequest, project: OwnedProject, db: DbSession
) -> BudgetRead:
    """Propose les postes attendus, sans aucun montant.

    Un tarif inventé serait un chiffre faux dans un dossier de financement :
    la trame donne la structure, l'auteur renseigne quantités et prix.
    """
    service = BudgetService(db)
    service.generate_from_template(project, replace=payload.replace)
    data = _read(service, project)
    _commit(db, project, service)
    return data


@router.post(
    "/budget/items",
    response_model=BudgetItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter un poste",
)
def add_item(payload: BudgetItemCreate, project: OwnedProject, db: DbSession) -> BudgetItemRead:
    service = BudgetService(db)
    item = service.add_item(project, **payload.model_dump())
    data = BudgetItemRead.model_validate(item)
    _commit(db, project, service)
    return data


@router.put("/budget/items/{item_id}", response_model=BudgetItemRead, summary="Modifier un poste")
def update_item(
    item_id: str, payload: BudgetItemUpdate, project: OwnedProject, db: DbSession
) -> BudgetItemRead:
    service = BudgetService(db)
    budget = service.get_or_create(project)
    item = service.get_owned_item(budget, item_id)
    if item is None:
        raise NotFoundError("Poste budgétaire introuvable.")
    service.update_item(project, item, **payload.model_dump(exclude_unset=True))
    data = BudgetItemRead.model_validate(item)
    _commit(db, project, service)
    return data


@router.delete("/budget/items/{item_id}", response_model=Message, summary="Supprimer un poste")
def delete_item(item_id: str, project: OwnedProject, db: DbSession) -> Message:
    service = BudgetService(db)
    budget = service.get_or_create(project)
    item = service.get_owned_item(budget, item_id)
    if item is None:
        raise NotFoundError("Poste budgétaire introuvable.")
    service.delete_item(project, item)
    _commit(db, project, service)
    return Message(detail="Poste supprimé.")


# ---------------------------------------------------------------------------
# Plan de financement
# ---------------------------------------------------------------------------
@router.get("/funding-plan", response_model=FundingPlanRead, summary="Plan de financement")
def get_plan(project: OwnedProject, db: DbSession) -> FundingPlanRead:
    service = BudgetService(db)
    plan = service.get_or_create_plan(project)
    service.recompute(project, project.budget)
    data = FundingPlanRead(
        **service.plan_summary(plan),
        lines=[FundingPlanLineRead.model_validate(line) for line in plan.lines],
    )
    db.commit()
    return data


@router.post(
    "/funding-plan/lines",
    response_model=FundingPlanLineRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter une source de financement",
)
def add_plan_line(
    payload: FundingPlanLineCreate, project: OwnedProject, db: DbSession
) -> FundingPlanLineRead:
    service = BudgetService(db)
    line = service.add_plan_line(project, **payload.model_dump())
    data = FundingPlanLineRead.model_validate(line)
    _commit(db, project, service)
    return data


@router.put(
    "/funding-plan/lines/{line_id}",
    response_model=FundingPlanLineRead,
    summary="Modifier une source",
)
def update_plan_line(
    line_id: str, payload: FundingPlanLineUpdate, project: OwnedProject, db: DbSession
) -> FundingPlanLineRead:
    service = BudgetService(db)
    plan = service.get_or_create_plan(project)
    line = service.get_owned_plan_line(plan, line_id)
    if line is None:
        raise NotFoundError("Source de financement introuvable.")
    service.update_plan_line(plan, line, **payload.model_dump(exclude_unset=True))
    data = FundingPlanLineRead.model_validate(line)
    _commit(db, project, service)
    return data


@router.delete(
    "/funding-plan/lines/{line_id}", response_model=Message, summary="Supprimer une source"
)
def delete_plan_line(line_id: str, project: OwnedProject, db: DbSession) -> Message:
    service = BudgetService(db)
    plan = service.get_or_create_plan(project)
    line = service.get_owned_plan_line(plan, line_id)
    if line is None:
        raise NotFoundError("Source de financement introuvable.")
    service.delete_plan_line(line)
    _commit(db, project, service)
    return Message(detail="Source supprimée.")


# ---------------------------------------------------------------------------
# Calendrier de production
# ---------------------------------------------------------------------------
@router.get(
    "/schedule", response_model=list[SchedulePhaseRead], summary="Calendrier de production"
)
def get_schedule(project: OwnedProject, db: DbSession) -> list[SchedulePhaseRead]:
    return [
        SchedulePhaseRead.model_validate(row)
        for row in BudgetService(db).list_schedule(project)
    ]


@router.put(
    "/schedule", response_model=SchedulePhaseRead, summary="Définir les dates d'une phase"
)
def upsert_schedule(
    payload: SchedulePhaseUpsert, project: OwnedProject, db: DbSession
) -> SchedulePhaseRead:
    service = BudgetService(db)
    row = service.set_schedule_phase(
        project,
        payload.phase,
        start_date=payload.start_date,
        end_date=payload.end_date,
        notes=payload.notes,
    )
    data = SchedulePhaseRead.model_validate(row)
    db.commit()
    return data


@router.delete("/schedule/{phase}", response_model=Message, summary="Retirer une phase")
def delete_schedule(phase: BudgetCategory, project: OwnedProject, db: DbSession) -> Message:
    BudgetService(db).delete_schedule_phase(project, phase)
    db.commit()
    return Message(detail="Phase retirée du calendrier.")
