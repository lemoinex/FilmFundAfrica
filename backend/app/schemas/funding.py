"""Schemas du module Funding Intelligence.

Regle produit tenue par ces schemas : une opportunite n'est jamais exposee
sans sa source (`source_name`, `source_url`) ni sa date de derniere
verification, et le score de compatibilite est toujours accompagne du
rappel qu'il ne garantit aucun financement.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import FundingCategory, FundingStatus, ProjectType
from app.schemas.common import ORMModel

#: Rappel affiche avec tout resultat de matching.
SCORE_DISCLAIMER = (
    "Le score de compatibilité est un indicateur d'aide à la décision. Il ne garantit en "
    "aucun cas l'obtention d'un financement : les conditions officielles de l'organisme "
    "font foi et doivent être vérifiées sur son site."
)


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _join_csv(values: list[str] | None) -> str:
    return ",".join(item.strip() for item in (values or []) if item.strip())


# ---------------------------------------------------------------------------
# Exigences
# ---------------------------------------------------------------------------
class RequirementBase(BaseModel):
    label: str = Field(min_length=1, max_length=255)
    description: str | None = None
    is_mandatory: bool = True
    #: Type de document attendu (voir DocumentType), si le dossier en exige un.
    required_document_type: str | None = Field(default=None, max_length=30)


class RequirementCreate(RequirementBase):
    pass


class RequirementRead(ORMModel, RequirementBase):
    id: str
    opportunity_id: str


# ---------------------------------------------------------------------------
# Opportunites
# ---------------------------------------------------------------------------
class OpportunityBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    organization: str = Field(min_length=1, max_length=255)
    description: str = ""
    website: str | None = Field(default=None, max_length=512)
    country: str | None = Field(default=None, max_length=120)
    eligible_countries: list[str] = Field(default_factory=list)
    project_types: list[ProjectType] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    category: FundingCategory = FundingCategory.FUND
    minimum_budget: float | None = Field(default=None, ge=0)
    maximum_budget: float | None = Field(default=None, ge=0)
    currency: str = Field(default="EUR", max_length=10)
    deadline: date | None = None
    opening_date: date | None = None
    application_url: str | None = Field(default=None, max_length=512)
    requirements: str = ""

    @model_validator(mode="after")
    def _check_budget_range(self) -> OpportunityBase:
        if (
            self.minimum_budget is not None
            and self.maximum_budget is not None
            and self.minimum_budget > self.maximum_budget
        ):
            raise ValueError("Le montant minimum ne peut pas dépasser le montant maximum.")
        return self


class OpportunityCreate(OpportunityBase):
    """Création par un administrateur.

    La source est obligatoire : sans elle, l'opportunité ne peut pas être
    présentée comme active aux utilisateurs.
    """

    source_name: str = Field(min_length=1, max_length=255)
    source_url: str = Field(min_length=1, max_length=512)
    status: FundingStatus = FundingStatus.UNVERIFIED
    is_demo: bool = False
    requirement_items: list[RequirementCreate] = Field(default_factory=list)

    @field_validator("source_url")
    @classmethod
    def _check_source_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("La source doit être une URL commençant par http:// ou https://")
        return value

    @model_validator(mode="after")
    def _open_requires_verification(self) -> OpportunityCreate:
        # Une opportunité annoncée ouverte engage la plateforme : elle doit
        # avoir été vérifiée, donc porter une source consultable.
        if self.status == FundingStatus.OPEN and not self.source_url:
            raise ValueError(
                "Une opportunité ne peut pas être publiée comme ouverte sans sa source."
            )
        return self


class OpportunityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    organization: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    website: str | None = Field(default=None, max_length=512)
    country: str | None = Field(default=None, max_length=120)
    eligible_countries: list[str] | None = None
    project_types: list[ProjectType] | None = None
    genres: list[str] | None = None
    languages: list[str] | None = None
    category: FundingCategory | None = None
    minimum_budget: float | None = Field(default=None, ge=0)
    maximum_budget: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=10)
    deadline: date | None = None
    opening_date: date | None = None
    application_url: str | None = Field(default=None, max_length=512)
    requirements: str | None = None
    status: FundingStatus | None = None
    source_name: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=512)


class OpportunityRead(ORMModel):
    id: str
    name: str
    organization: str
    description: str
    website: str | None = None
    country: str | None = None
    eligible_countries: list[str] = Field(default_factory=list)
    project_types: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    category: FundingCategory
    minimum_budget: float | None = None
    maximum_budget: float | None = None
    currency: str
    deadline: date | None = None
    opening_date: date | None = None
    application_url: str | None = None
    requirements: str
    status: FundingStatus
    #: Traçabilité — jamais omise.
    source_name: str | None = None
    source_url: str | None = None
    last_verified_at: datetime | None = None
    is_demo: bool
    created_at: datetime
    updated_at: datetime
    requirement_items: list[RequirementRead] = Field(default_factory=list)

    @field_validator(
        "eligible_countries", "project_types", "genres", "languages", mode="before"
    )
    @classmethod
    def _parse_csv(cls, value):
        return _split_csv(value) if isinstance(value, str) else value

    @property
    def amount_label(self) -> str | None:
        return format_amount(self.minimum_budget, self.maximum_budget, self.currency)


def format_amount(low: float | None, high: float | None, currency: str) -> str | None:
    def fmt(value: float) -> str:
        return f"{value:,.0f}".replace(",", " ")

    if low and high:
        return f"{fmt(low)} – {fmt(high)} {currency}"
    if high:
        return f"jusqu'à {fmt(high)} {currency}"
    if low:
        return f"à partir de {fmt(low)} {currency}"
    return None


# ---------------------------------------------------------------------------
# Recherche
# ---------------------------------------------------------------------------
SortOption = Literal["deadline", "recent", "amount", "name"]


class OpportunitySearch(BaseModel):
    """Filtres de recherche (cahier des charges §17)."""

    query: str | None = Field(default=None, max_length=200)
    country: str | None = Field(default=None, max_length=120)
    project_type: ProjectType | None = None
    genre: str | None = Field(default=None, max_length=120)
    language: str | None = Field(default=None, max_length=60)
    category: FundingCategory | None = None
    min_amount: float | None = Field(default=None, ge=0)
    max_amount: float | None = Field(default=None, ge=0)
    deadline_before: date | None = None
    deadline_after: date | None = None
    #: Par défaut, on masque les dispositifs clos : ils ne sont plus actionnables.
    include_closed: bool = False
    include_demo: bool = True
    sort: SortOption = "deadline"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class OpportunitySummary(BaseModel):
    id: str
    name: str
    organization: str
    category: FundingCategory
    country: str | None = None
    amount_label: str | None = None
    deadline: date | None = None
    days_left: int | None = None
    status: FundingStatus
    is_demo: bool
    source_name: str | None = None
    source_url: str | None = None
    last_verified_at: datetime | None = None


class OpportunityPage(BaseModel):
    items: list[OpportunitySummary]
    total: int
    page: int
    page_size: int
    #: Valeurs distinctes présentes en base, pour alimenter les filtres.
    facets: dict[str, list[str]] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------
class MatchCriterion(BaseModel):
    key: str
    label: str
    weight: int
    earned: int
    #: `met` — rempli · `unmet` — non rempli · `unknown` — non vérifiable
    state: Literal["met", "unmet", "unknown"]
    detail: str
    #: Un critère bloquant non rempli rend la candidature inéligible.
    blocking: bool = False


class MatchResult(BaseModel):
    opportunity: OpportunitySummary
    compatibility: int = Field(ge=0, le=100)
    eligible: bool
    #: Part de la grille réellement évaluable avec les données du projet.
    assessed_ratio: int = Field(ge=0, le=100)
    criteria: list[MatchCriterion]
    met_conditions: list[str]
    missing_conditions: list[str]
    unknown_conditions: list[str]
    required_documents: list[str]
    missing_documents: list[str]
    computed_at: datetime
    has_explanation: bool = False


class MatchListResponse(BaseModel):
    project_id: str
    project_title: str
    total: int
    results: list[MatchResult]
    computed_at: datetime
    disclaimer: str = SCORE_DISCLAIMER


class MatchExplanation(BaseModel):
    opportunity_id: str
    compatibility: int
    explanation: str
    credits_consumed: int
    credits_remaining: int
    provider: str
    model: str
    prompt_version: str
    disclaimer: str = SCORE_DISCLAIMER
