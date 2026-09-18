"""Logique métier du module Funding Intelligence.

Recherche, administration des dispositifs, persistance des rapprochements et
explication IA à la demande.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.core.i18n import Locale
from app.models.enums import AIOperation, FundingStatus, NotificationType
from app.models.funding import FundingOpportunity, FundingRequirement, ProjectFundingMatch
from app.models.project import Project
from app.models.user import User
from app.prompts import PromptContext, build_funding_match_prompt
from app.repositories.funding import FundingRepository, MatchRepository
from app.schemas.funding import (
    MatchExplanation,
    MatchListResponse,
    MatchResult,
    OpportunityCreate,
    OpportunityPage,
    OpportunityRead,
    OpportunitySearch,
    OpportunityUpdate,
)
from app.services.ai.service import AIService
from app.services.credit_service import CreditService
from app.services.matching_service import MatchingService
from app.services.notification_service import build_notification

logger = logging.getLogger("filmfund.funding")

#: Séparateur des listes stockées en CSV.
JOIN = ","


def _join(values: list | None) -> str:
    return JOIN.join(str(value).strip() for value in (values or []) if str(value).strip())


class FundingService:
    def __init__(
        self,
        db: Session,
        ai_service: AIService | None = None,
        locale: Locale = "fr",
    ) -> None:
        self.db = db
        self.locale = locale
        self.opportunities = FundingRepository(db)
        self.matches = MatchRepository(db)
        self.matching = MatchingService(db, locale=locale)
        self.credits = CreditService(db)
        self._ai_service = ai_service

    @property
    def ai(self) -> AIService:
        if self._ai_service is None:
            self._ai_service = AIService()
        return self._ai_service

    # ------------------------------------------------------------------
    # Consultation
    # ------------------------------------------------------------------
    def search(self, search: OpportunitySearch) -> OpportunityPage:
        rows, total = self.opportunities.search(search)
        return OpportunityPage(
            items=[MatchingService.to_summary(row) for row in rows],
            total=total,
            page=search.page,
            page_size=search.page_size,
            facets=self.opportunities.facets(),
        )

    def get(self, opportunity_id: str) -> OpportunityRead:
        opportunity = self.opportunities.get_with_requirements(opportunity_id)
        if opportunity is None:
            raise NotFoundError("funding.opportunityNotFound")
        return OpportunityRead.model_validate(opportunity)

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------
    def compute_matches(
        self, project: Project, *, persist: bool = True, notify_user: User | None = None
    ) -> MatchListResponse:
        opportunities = self.opportunities.eligible_for_matching()
        results = self.matching.score_project(project, opportunities)

        if persist:
            self._persist(project, results)
            if notify_user is not None:
                self._notify_new_matches(notify_user, project, results)
            self.db.commit()

        return MatchListResponse(
            project_id=project.id,
            project_title=project.title,
            total=len(results),
            results=results,
            computed_at=datetime.now(UTC),
        )

    def stored_matches(self, project: Project) -> MatchListResponse:
        """Rapprochements déjà calculés, recalculés si aucun n'existe encore."""
        stored = self.matches.list_for_project(project.id)
        if not stored:
            return self.compute_matches(project)

        documents = None
        results: list[MatchResult] = []
        for match in stored:
            # Le score est recalculé à la volée : une échéance a pu passer
            # depuis le dernier calcul, et afficher un score périmé tromperait
            # l'utilisateur sur ce qui lui reste réellement ouvert.
            result = self.matching.score_one(project, match.opportunity, documents)
            result.has_explanation = bool(match.rationale)
            results.append(result)

        results.sort(key=lambda item: (item.eligible, item.compatibility), reverse=True)
        return MatchListResponse(
            project_id=project.id,
            project_title=project.title,
            total=len(results),
            results=results,
            computed_at=datetime.now(UTC),
        )

    def _persist(self, project: Project, results: list[MatchResult]) -> None:
        now = datetime.now(UTC)
        for result in results:
            match = self.matches.get_pair(project.id, result.opportunity.id)
            if match is None:
                match = ProjectFundingMatch(
                    project_id=project.id, opportunity_id=result.opportunity.id
                )
                self.db.add(match)
            match.compatibility_score = result.compatibility
            match.met_conditions = "\n".join(result.met_conditions)
            match.missing_conditions = "\n".join(result.missing_conditions)
            match.computed_at = now
        self.db.flush()

    def _notify_new_matches(
        self, user: User, project: Project, results: list[MatchResult], threshold: int = 70
    ) -> None:
        strong = [r for r in results if r.eligible and r.compatibility >= threshold]
        if not strong:
            return
        link = f"/projets/{project.id}/financements"
        self.db.add(
            build_notification(
                user_id=user.id,
                notification_type=NotificationType.MATCH_FOUND,
                title_key="notification.matchFound.title",
                body_key="notification.matchFound.body",
                params={
                    "count": len(strong),
                    "project": project.title,
                    "threshold": threshold,
                },
                link=link,
            )
        )

    # ------------------------------------------------------------------
    # Explication IA (à la demande, 1 crédit)
    # ------------------------------------------------------------------
    def explain_match(
        self, user: User, project: Project, opportunity_id: str, *, refresh: bool = False
    ) -> MatchExplanation:
        opportunity = self.opportunities.get_with_requirements(opportunity_id)
        if opportunity is None:
            raise NotFoundError("funding.opportunityNotFound")

        result = self.matching.score_one(project, opportunity)
        match = self.matches.get_pair(project.id, opportunity_id)

        # Explication déjà rédigée : on la rend sans débiter à nouveau.
        if match is not None and match.rationale and not refresh:
            return MatchExplanation(
                opportunity_id=opportunity_id,
                compatibility=result.compatibility,
                explanation=match.rationale,
                credits_consumed=0,
                credits_remaining=user.ai_credits_remaining,
                provider="cache",
                model="—",
                prompt_version="—",
            )

        self.credits.check_credits(user, AIOperation.MATCH_FUNDING)
        prompt = build_funding_match_prompt(
            PromptContext.from_project(project),
            self._opportunity_facts(opportunity, result),
            result.compatibility,
        )

        try:
            response = self.ai.run(prompt)
        except AppError as exc:
            self.credits.record_usage(
                user,
                operation=AIOperation.MATCH_FUNDING,
                provider=self.ai.provider.name,
                model=self.ai.model,
                project_id=project.id,
                prompt_name=prompt.prompt_name,
                prompt_version=prompt.prompt_version,
                success=False,
                error_message=str(getattr(exc, "detail", exc)),
                consume=False,
            )
            self.db.commit()
            raise

        if match is None:
            match = ProjectFundingMatch(
                project_id=project.id, opportunity_id=opportunity_id
            )
            self.db.add(match)
        match.compatibility_score = result.compatibility
        match.met_conditions = "\n".join(result.met_conditions)
        match.missing_conditions = "\n".join(result.missing_conditions)
        match.rationale = response.text
        match.computed_at = datetime.now(UTC)

        consumed = self.credits.record_usage(
            user,
            operation=AIOperation.MATCH_FUNDING,
            provider=response.provider,
            model=response.model,
            project_id=project.id,
            prompt_name=prompt.prompt_name,
            prompt_version=prompt.prompt_version,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=response.latency_ms,
        )
        self.db.commit()

        return MatchExplanation(
            opportunity_id=opportunity_id,
            compatibility=result.compatibility,
            explanation=response.text,
            credits_consumed=consumed,
            credits_remaining=user.ai_credits_remaining,
            provider=response.provider,
            model=response.model,
            prompt_version=prompt.prompt_version,
        )

    @staticmethod
    def _opportunity_facts(
        opportunity: FundingOpportunity, result: MatchResult
    ) -> dict[str, str]:
        """Faits transmis à l'IA — uniquement ce qui est en base, jamais d'inférence."""
        facts: dict[str, str] = {
            "Nom": opportunity.name,
            "Organisme": opportunity.organization,
            "Catégorie": str(opportunity.category),
            "Description": opportunity.description,
            "Pays éligibles": opportunity.eligible_countries or "non précisé",
            "Types de projet acceptés": opportunity.project_types or "non précisé",
            "Genres": opportunity.genres or "non précisé",
            "Langues": opportunity.languages or "non précisé",
            "Montant": result.opportunity.amount_label or "non précisé",
            "Date limite": (
                f"{opportunity.deadline:%d/%m/%Y}" if opportunity.deadline else "non précisée"
            ),
            "Pièces à fournir": opportunity.requirements or "non précisées",
            "Statut": str(opportunity.status),
            "Source": opportunity.source_url or "non précisée",
            "Dernière vérification": (
                f"{opportunity.last_verified_at:%d/%m/%Y}"
                if opportunity.last_verified_at
                else "jamais vérifiée"
            ),
        }
        if result.met_conditions:
            facts["Conditions remplies (calculées)"] = " | ".join(result.met_conditions)
        if result.missing_conditions:
            facts["Conditions non remplies (calculées)"] = " | ".join(result.missing_conditions)
        if result.unknown_conditions:
            facts["Points non vérifiables (calculés)"] = " | ".join(result.unknown_conditions)
        return facts

    # ------------------------------------------------------------------
    # Administration
    # ------------------------------------------------------------------
    def create(self, payload: OpportunityCreate) -> OpportunityRead:
        data = payload.model_dump(exclude={"requirement_items"})
        for field in ("eligible_countries", "project_types", "genres", "languages"):
            data[field] = _join(data.get(field))

        opportunity = FundingOpportunity(
            **data,
            source=payload.source_name,
            last_verified_at=datetime.now(UTC),
        )
        for requirement in payload.requirement_items:
            opportunity.requirement_items.append(
                FundingRequirement(**requirement.model_dump())
            )

        self.db.add(opportunity)
        self.db.commit()
        self.db.refresh(opportunity)
        logger.info("dispositif créé", extra={"event": "funding_created"})
        return OpportunityRead.model_validate(opportunity)

    def update(self, opportunity_id: str, payload: OpportunityUpdate) -> OpportunityRead:
        opportunity = self.opportunities.get_with_requirements(opportunity_id)
        if opportunity is None:
            raise NotFoundError("funding.opportunityNotFound")

        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            if value is None:
                continue
            if field in ("eligible_countries", "project_types", "genres", "languages"):
                value = _join(value)
            setattr(opportunity, field, value)

        if payload.status == FundingStatus.OPEN and not opportunity.source_url:
            raise AppError("funding.sourceRequiredToPublish", code="source_required")

        self.db.commit()
        self.db.refresh(opportunity)
        return OpportunityRead.model_validate(opportunity)

    def mark_verified(self, opportunity_id: str, status: FundingStatus) -> OpportunityRead:
        """Enregistre une vérification humaine de la fiche."""
        opportunity = self.opportunities.get_with_requirements(opportunity_id)
        if opportunity is None:
            raise NotFoundError("funding.opportunityNotFound")
        if not opportunity.source_url:
            raise AppError("funding.sourceRequiredToVerify", code="source_required")
        opportunity.status = status
        opportunity.last_verified_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(opportunity)
        return OpportunityRead.model_validate(opportunity)

    def delete(self, opportunity_id: str) -> None:
        opportunity = self.opportunities.get(opportunity_id)
        if opportunity is None:
            raise NotFoundError("funding.opportunityNotFound")
        self.db.delete(opportunity)
        self.db.commit()

    def add_requirement(self, opportunity_id: str, payload) -> OpportunityRead:
        opportunity = self.opportunities.get_with_requirements(opportunity_id)
        if opportunity is None:
            raise NotFoundError("funding.opportunityNotFound")
        opportunity.requirement_items.append(FundingRequirement(**payload.model_dump()))
        self.db.commit()
        self.db.refresh(opportunity)
        return OpportunityRead.model_validate(opportunity)

    def delete_requirement(self, opportunity_id: str, requirement_id: str) -> OpportunityRead:
        opportunity = self.opportunities.get_with_requirements(opportunity_id)
        if opportunity is None:
            raise NotFoundError("funding.opportunityNotFound")
        target = next(
            (item for item in opportunity.requirement_items if item.id == requirement_id), None
        )
        if target is None:
            raise NotFoundError("funding.requirementNotFound")
        self.db.delete(target)
        self.db.commit()
        self.db.refresh(opportunity)
        return OpportunityRead.model_validate(opportunity)
