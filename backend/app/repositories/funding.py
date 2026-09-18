"""Acces a la base des opportunites de financement."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import selectinload

from app.models.enums import FundingStatus
from app.models.funding import FundingOpportunity, ProjectFundingMatch
from app.repositories.base import BaseRepository
from app.schemas.funding import OpportunitySearch

#: Colonnes listees dans les facettes proposees a l'interface.
FACET_COLUMNS = {
    "countries": FundingOpportunity.eligible_countries,
    "genres": FundingOpportunity.genres,
    "languages": FundingOpportunity.languages,
}


class FundingRepository(BaseRepository[FundingOpportunity]):
    model = FundingOpportunity

    # ------------------------------------------------------------------
    def get_with_requirements(self, opportunity_id: str) -> FundingOpportunity | None:
        return self.db.scalar(
            select(FundingOpportunity)
            .options(selectinload(FundingOpportunity.requirement_items))
            .where(FundingOpportunity.id == opportunity_id)
        )

    # ------------------------------------------------------------------
    def _apply_filters(self, stmt: Select, search: OpportunitySearch) -> Select:
        if search.query:
            pattern = f"%{search.query.strip()}%"
            stmt = stmt.where(
                or_(
                    FundingOpportunity.name.ilike(pattern),
                    FundingOpportunity.organization.ilike(pattern),
                    FundingOpportunity.description.ilike(pattern),
                    FundingOpportunity.requirements.ilike(pattern),
                )
            )

        if search.country:
            # Liste vide = ouvert à tous les pays, on la conserve donc.
            needle = f"%{search.country.strip()}%"
            stmt = stmt.where(
                or_(
                    FundingOpportunity.eligible_countries.ilike(needle),
                    FundingOpportunity.eligible_countries == "",
                )
            )

        if search.project_type:
            stmt = stmt.where(
                or_(
                    FundingOpportunity.project_types.ilike(f"%{search.project_type}%"),
                    FundingOpportunity.project_types == "",
                )
            )

        if search.genre:
            stmt = stmt.where(
                or_(
                    FundingOpportunity.genres.ilike(f"%{search.genre.strip()}%"),
                    FundingOpportunity.genres == "",
                )
            )

        if search.language:
            stmt = stmt.where(
                or_(
                    FundingOpportunity.languages.ilike(f"%{search.language.strip()}%"),
                    FundingOpportunity.languages == "",
                )
            )

        if search.category:
            stmt = stmt.where(FundingOpportunity.category == search.category)

        # Un dispositif sans montant renseigné reste visible : l'absence
        # d'information n'est pas une exclusion.
        if search.min_amount is not None:
            stmt = stmt.where(
                or_(
                    FundingOpportunity.maximum_budget.is_(None),
                    FundingOpportunity.maximum_budget >= search.min_amount,
                )
            )
        if search.max_amount is not None:
            stmt = stmt.where(
                or_(
                    FundingOpportunity.minimum_budget.is_(None),
                    FundingOpportunity.minimum_budget <= search.max_amount,
                )
            )

        if search.deadline_after:
            stmt = stmt.where(
                or_(
                    FundingOpportunity.deadline.is_(None),
                    FundingOpportunity.deadline >= search.deadline_after,
                )
            )
        if search.deadline_before:
            stmt = stmt.where(
                or_(
                    FundingOpportunity.deadline.is_(None),
                    FundingOpportunity.deadline <= search.deadline_before,
                )
            )

        if not search.include_closed:
            stmt = stmt.where(
                FundingOpportunity.status != FundingStatus.CLOSED,
                or_(
                    FundingOpportunity.deadline.is_(None),
                    FundingOpportunity.deadline >= date.today(),
                ),
            )

        if not search.include_demo:
            stmt = stmt.where(FundingOpportunity.is_demo.is_(False))

        return stmt

    # ------------------------------------------------------------------
    @staticmethod
    def _apply_sort(stmt: Select, sort: str) -> Select:
        if sort == "recent":
            return stmt.order_by(FundingOpportunity.created_at.desc())
        if sort == "amount":
            return stmt.order_by(
                FundingOpportunity.maximum_budget.desc().nullslast(),
                FundingOpportunity.name,
            )
        if sort == "name":
            return stmt.order_by(FundingOpportunity.name)
        # Par défaut : l'échéance la plus proche d'abord, sans date à la fin.
        return stmt.order_by(
            FundingOpportunity.deadline.asc().nullslast(), FundingOpportunity.name
        )

    # ------------------------------------------------------------------
    def search(self, search: OpportunitySearch) -> tuple[list[FundingOpportunity], int]:
        stmt = self._apply_filters(select(FundingOpportunity), search)

        total = int(
            self.db.scalar(
                self._apply_filters(
                    select(func.count()).select_from(FundingOpportunity), search
                )
            )
            or 0
        )

        stmt = self._apply_sort(stmt, search.sort)
        stmt = stmt.limit(search.page_size).offset((search.page - 1) * search.page_size)
        return list(self.db.scalars(stmt)), total

    # ------------------------------------------------------------------
    def eligible_for_matching(self, include_demo: bool = True) -> list[FundingOpportunity]:
        """Dispositifs candidats au rapprochement : tout sauf les clos."""
        stmt = (
            select(FundingOpportunity)
            .options(selectinload(FundingOpportunity.requirement_items))
            .where(FundingOpportunity.status != FundingStatus.CLOSED)
        )
        if not include_demo:
            stmt = stmt.where(FundingOpportunity.is_demo.is_(False))
        return list(self.db.scalars(stmt))

    # ------------------------------------------------------------------
    def facets(self) -> dict[str, list[str]]:
        """Valeurs distinctes présentes en base, pour alimenter les filtres."""
        result: dict[str, list[str]] = {}
        for name, column in FACET_COLUMNS.items():
            values: set[str] = set()
            for raw in self.db.scalars(select(column).where(column != "")):
                values.update(item.strip() for item in raw.split(",") if item.strip())
            result[name] = sorted(values)

        result["categories"] = sorted(
            {str(value) for value in self.db.scalars(select(FundingOpportunity.category))}
        )
        return result


class MatchRepository(BaseRepository[ProjectFundingMatch]):
    model = ProjectFundingMatch

    def list_for_project(self, project_id: str) -> list[ProjectFundingMatch]:
        return list(
            self.db.scalars(
                select(ProjectFundingMatch)
                .options(selectinload(ProjectFundingMatch.opportunity))
                .where(ProjectFundingMatch.project_id == project_id)
                .order_by(ProjectFundingMatch.compatibility_score.desc())
            )
        )

    def get_pair(self, project_id: str, opportunity_id: str) -> ProjectFundingMatch | None:
        return self.db.scalar(
            select(ProjectFundingMatch).where(
                ProjectFundingMatch.project_id == project_id,
                ProjectFundingMatch.opportunity_id == opportunity_id,
            )
        )

    def clear_for_project(self, project_id: str) -> None:
        for match in self.db.scalars(
            select(ProjectFundingMatch).where(ProjectFundingMatch.project_id == project_id)
        ):
            self.db.delete(match)
        self.db.flush()
