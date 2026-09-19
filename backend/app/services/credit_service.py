"""Credits IA, plans et quotas.

L'usage de l'IA n'est jamais illimite : chaque generation consomme des
credits. Les quotas proviennent du plan stocke en base (modifiable par
l'administration), avec repli sur les valeurs d'environnement.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import QuotaExceededError
from app.models.billing import AIUsage, Subscription, SubscriptionPlan
from app.models.enums import AIOperation, PlanCode, SubscriptionStatus
from app.models.user import User

logger = logging.getLogger("filmfund.credits")

#: Cout en credits par type d'operation.
OPERATION_COST: dict[AIOperation, int] = {
    AIOperation.GENERATE_DOCUMENT: 1,
    AIOperation.IMPROVE_DOCUMENT: 1,
    AIOperation.SCORE_PROJECT: 1,
    AIOperation.MATCH_FUNDING: 1,
    # Un credit par agent, et non par passage : une chaine coute huit
    # appels au fournisseur, la facturer comme un synopsis reviendrait a
    # vendre a perte. `units` porte le nombre reel d'etapes.
    AIOperation.RUN_AGENT_CHAIN: 1,
}

DEFAULT_PLANS: list[dict] = [
    {
        "code": PlanCode.FREE,
        "name": "Gratuit",
        "description": "1 projet, 1 génération IA, veille limitée.",
        "price_amount": 0,
        "price_currency": "XAF",
        "max_projects": 1,
        "monthly_ai_credits": settings.ai_credits_free,
        "allows_export": False,
        "allows_matching": False,
        "allows_collaboration": False,
        "allows_advanced_budget": False,
        "sort_order": 1,
    },
    {
        "code": PlanCode.PRO_AUTHOR,
        "name": "Pro Auteur",
        "description": "Projets illimités, génération IA complète, veille personnalisée.",
        "price_amount": 20000,
        "price_currency": "XAF",
        "max_projects": 0,  # 0 = illimite
        "monthly_ai_credits": settings.ai_credits_pro,
        "allows_export": True,
        "allows_matching": True,
        "allows_collaboration": False,
        "allows_advanced_budget": False,
        "sort_order": 2,
    },
    {
        "code": PlanCode.PRODUCER,
        "name": "Producteur",
        "description": "Multi-projets, export, budget avancé, collaboration d'équipe.",
        "price_amount": 100000,
        "price_currency": "XAF",
        "max_projects": 0,
        "monthly_ai_credits": settings.ai_credits_producer,
        "allows_export": True,
        "allows_matching": True,
        "allows_collaboration": True,
        "allows_advanced_budget": True,
        "sort_order": 3,
    },
]


class CreditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    def ensure_plans(self) -> dict[PlanCode, SubscriptionPlan]:
        """Cree les plans par defaut s'ils n'existent pas encore."""
        existing = {plan.code: plan for plan in self.db.scalars(select(SubscriptionPlan))}
        for definition in DEFAULT_PLANS:
            if definition["code"] not in existing:
                plan = SubscriptionPlan(**definition)
                self.db.add(plan)
                existing[plan.code] = plan
        self.db.flush()
        return existing

    def get_plan(self, code: PlanCode) -> SubscriptionPlan:
        plan = self.db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == code))
        if plan is None:
            plan = self.ensure_plans()[code]
        return plan

    def plan_for_user(self, user: User) -> SubscriptionPlan:
        if user.subscription is not None and user.subscription.plan is not None:
            return user.subscription.plan
        return self.get_plan(PlanCode.FREE)

    # ------------------------------------------------------------------
    def attach_default_plan(self, user: User) -> None:
        plan = self.get_plan(PlanCode.FREE)
        now = datetime.now(UTC)
        user.subscription = Subscription(
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            started_at=now,
            current_period_end=now + timedelta(days=30),
        )
        user.ai_credits_remaining = plan.monthly_ai_credits
        user.ai_credits_period_start = now

    # ------------------------------------------------------------------
    def refresh_period_if_needed(self, user: User) -> None:
        """Recharge les credits si la periode mensuelle est ecoulee."""
        now = datetime.now(UTC)
        start = user.ai_credits_period_start
        if start is None:
            user.ai_credits_period_start = now
            user.ai_credits_remaining = self.plan_for_user(user).monthly_ai_credits
            return
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        if now - start >= timedelta(days=30):
            user.ai_credits_period_start = now
            user.ai_credits_remaining = self.plan_for_user(user).monthly_ai_credits

    # ------------------------------------------------------------------
    def check_project_quota(self, user: User, current_project_count: int) -> None:
        plan = self.plan_for_user(user)
        if plan.max_projects and current_project_count >= plan.max_projects:
            raise QuotaExceededError(
                "quota.projectLimit",
                params={"plan": plan.name, "max": plan.max_projects},
                code="project_quota_exceeded",
            )

    def check_credits(self, user: User, operation: AIOperation, units: int = 1) -> int:
        """Vérifie le solde et renvoie le coût de l'opération.

        `units` vaut plus de 1 lorsqu'une même demande déclenche plusieurs
        appels au fournisseur (cas du scénario long, écrit en plusieurs passes).
        """
        self.refresh_period_if_needed(user)
        cost = OPERATION_COST.get(operation, 1) * max(units, 1)
        if user.ai_credits_remaining < cost:
            plan = self.plan_for_user(user)
            # Une generation en plusieurs passes coute plus d'un credit : le
            # message doit dire le prix, sans quoi le solde restant semble
            # suffisant a qui en a un.
            raise QuotaExceededError(
                "quota.creditsInsufficient" if cost > 1 else "quota.creditsExhausted",
                params={
                    "plan": plan.name,
                    "cost": cost,
                    "remaining": user.ai_credits_remaining,
                },
                code="ai_credits_exhausted",
            )
        return cost

    # ------------------------------------------------------------------
    def reserve(self, user: User, operation: AIOperation, units: int = 1) -> int:
        """Debite les credits avant l'execution, et renvoie le montant retenu.

        Une generation mise en file n'a pas encore consomme quoi que ce soit
        quand la suivante est demandee : sans cette reserve, un compte a un
        credit pourrait empiler autant de taches qu'il le souhaite.
        """
        cost = self.check_credits(user, operation, units=units)
        user.ai_credits_remaining = max(user.ai_credits_remaining - cost, 0)
        return cost

    def refund(self, user: User, amount: int) -> None:
        """Rend une reserve dont la generation n'a rien produit."""
        if amount <= 0:
            return
        user.ai_credits_remaining += amount
        logger.info(
            "crédits rendus après échec",
            extra={"event": "ai_credits_refunded"},
        )

    # ------------------------------------------------------------------
    def record_usage(
        self,
        user: User,
        *,
        operation: AIOperation,
        provider: str,
        model: str,
        project_id: str | None = None,
        document_type: str | None = None,
        prompt_name: str | None = None,
        prompt_version: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: int = 0,
        success: bool = True,
        error_message: str | None = None,
        consume: bool = True,
        units: int = 1,
        log_usage: bool = True,
    ) -> int:
        """Journalise l'appel IA et debite les credits en cas de succes.

        `log_usage=False` debite sans ecrire de ligne : utilise quand les appels
        ont deja ete journalises un par un (generation d'un scenario en
        plusieurs passes), pour ne pas compter deux fois les memes appels.
        """
        cost = (
            OPERATION_COST.get(operation, 1) * max(units, 1) if (consume and success) else 0
        )
        if cost:
            user.ai_credits_remaining = max(user.ai_credits_remaining - cost, 0)

        if not log_usage:
            return cost

        self.db.add(
            AIUsage(
                user_id=user.id,
                project_id=project_id,
                operation=operation,
                document_type=document_type,
                provider=provider,
                model=model,
                prompt_name=prompt_name,
                prompt_version=prompt_version,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                credits_consumed=cost,
                latency_ms=latency_ms,
                success=success,
                error_message=error_message,
            )
        )
        logger.info(
            "consommation IA",
            extra={
                "event": "ai_usage",
                "duration_ms": latency_ms,
            },
        )
        return cost
