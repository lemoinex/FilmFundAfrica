"""Schemas du budget previsionnel, du plan de financement et du calendrier."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import BudgetCategory, FundingSourceType
from app.schemas.common import ORMModel


class BudgetItemRead(ORMModel):
    id: str
    category: BudgetCategory
    label: str
    quantity: float
    unit: str | None = None
    unit_price: float
    #: Toujours calcule (quantite x prix unitaire), jamais saisi.
    amount: float
    sort_order: int


class BudgetItemCreate(BaseModel):
    category: BudgetCategory
    label: str = Field(min_length=1, max_length=255)
    quantity: float = Field(default=1.0, ge=0)
    unit: str | None = Field(default=None, max_length=60)
    unit_price: float = Field(default=0.0, ge=0)


class BudgetItemUpdate(BaseModel):
    category: BudgetCategory | None = None
    label: str | None = Field(default=None, min_length=1, max_length=255)
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=60)
    unit_price: float | None = Field(default=None, ge=0)
    sort_order: int | None = None


class CategoryTotal(BaseModel):
    category: BudgetCategory
    amount: float
    item_count: int
    #: Part de cette phase dans le budget total, en pourcentage.
    share: float


class BudgetRead(ORMModel):
    id: str
    project_id: str
    currency: str
    total_amount: float
    notes: str | None = None
    items: list[BudgetItemRead] = Field(default_factory=list)
    totals_by_category: list[CategoryTotal] = Field(default_factory=list)
    updated_at: datetime


class BudgetUpdate(BaseModel):
    currency: str | None = Field(default=None, max_length=10)
    notes: str | None = None


class BudgetGenerateRequest(BaseModel):
    """Installe la trame de postes attendue pour ce type de projet.

    `replace` efface les lignes existantes : par defaut, on complete sans
    toucher au travail deja fait.
    """

    replace: bool = False


class FundingPlanLineRead(ORMModel):
    id: str
    source_type: FundingSourceType
    source_name: str | None = None
    amount: float
    is_secured: bool
    expected_date: date | None = None


class FundingPlanLineCreate(BaseModel):
    source_type: FundingSourceType
    source_name: str | None = Field(default=None, max_length=255)
    amount: float = Field(default=0.0, ge=0)
    is_secured: bool = False
    expected_date: date | None = None


class FundingPlanLineUpdate(BaseModel):
    source_type: FundingSourceType | None = None
    source_name: str | None = Field(default=None, max_length=255)
    amount: float | None = Field(default=None, ge=0)
    is_secured: bool | None = None
    expected_date: date | None = None


class FundingPlanRead(BaseModel):
    currency: str
    #: Suit le budget : il n'est jamais saisi a la main.
    total_budget: float
    #: Somme des lignes marquees acquises.
    secured_amount: float
    #: Somme de toutes les lignes, acquises ou seulement esperees.
    identified_amount: float
    #: Ce qu'il reste a financer par rapport a l'acquis.
    sought_amount: float
    funded_percentage: float
    #: Ce que meme les sources esperees ne couvrent pas encore.
    uncovered_amount: float
    lines: list[FundingPlanLineRead] = Field(default_factory=list)


class SchedulePhaseRead(ORMModel):
    id: str
    phase: BudgetCategory
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None


class SchedulePhaseUpsert(BaseModel):
    phase: BudgetCategory
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = Field(default=None, max_length=500)
