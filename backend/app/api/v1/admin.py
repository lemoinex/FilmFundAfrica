"""Routes d'administration.

Toutes les routes exigent le role ADMIN. Les statistiques projets sont
anonymisees : aucun titre ni contenu de projet n'est exposé ici.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.core.deps import CurrentAdmin, DbSession, Translator
from app.core.errors import NotFoundError
from app.models.billing import AIUsage, SubscriptionPlan
from app.models.document import Document
from app.models.enums import CandidateStatus, PlanCode, ProjectStatus, ProjectType
from app.models.payment import Payment
from app.models.project import Project
from app.models.user import User
from app.schemas.billing import PaymentRead
from app.schemas.common import Message
from app.schemas.ingestion import (
    CandidateApproval,
    CandidateRead,
    CandidateRejection,
)
from app.schemas.settings import (
    AIConfigRead,
    AIConfigTestResult,
    AIConfigUpdate,
    PlatformStatusRead,
)
from app.schemas.user import AdminUserUpdate, UserRead
from app.services.ai_config_service import AIConfigService
from app.services.auth_service import serialize_user
from app.services.credit_service import CreditService
from app.services.ingestion_service import IngestionService
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/admin", tags=["Administration"])


# ---------------------------------------------------------------------------
# Utilisateurs
# ---------------------------------------------------------------------------
@router.get("/users", response_model=list[UserRead], summary="Lister les utilisateurs")
def list_users(
    db: DbSession,
    _: CurrentAdmin,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[UserRead]:
    from app.repositories.user import UserRepository

    return [
        serialize_user(user) for user in UserRepository(db).list_paginated(limit, offset)
    ]


@router.put("/users/{user_id}", response_model=UserRead, summary="Modifier un utilisateur")
def update_user(
    user_id: str, payload: AdminUserUpdate, db: DbSession, _: CurrentAdmin
) -> UserRead:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("admin.userNotFound")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return serialize_user(user)


@router.post("/users/{user_id}/suspend", response_model=Message, summary="Suspendre un compte")
def suspend_user(
    user_id: str, db: DbSession, admin: CurrentAdmin, t: Translator
) -> Message:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("admin.userNotFound")
    if user.id == admin.id:
        from app.core.errors import AppError

        raise AppError("admin.cannotSuspendSelf")
    user.is_active = False
    db.commit()
    return Message(detail=t("admin.accountSuspended"))


# ---------------------------------------------------------------------------
# Statistiques anonymisées
# ---------------------------------------------------------------------------
@router.get("/stats/projects", summary="Statistiques projets (anonymisées)")
def project_stats(db: DbSession, _: CurrentAdmin) -> dict:
    by_type = dict(
        db.execute(select(Project.project_type, func.count()).group_by(Project.project_type)).all()
    )
    by_status = dict(
        db.execute(select(Project.status, func.count()).group_by(Project.status)).all()
    )
    return {
        "total": int(db.scalar(select(func.count()).select_from(Project)) or 0),
        "documents": int(db.scalar(select(func.count()).select_from(Document)) or 0),
        "average_readiness_score": round(
            float(db.scalar(select(func.avg(Project.readiness_score))) or 0), 1
        ),
        "by_type": {str(key): value for key, value in by_type.items()}
        or {str(t): 0 for t in ProjectType},
        "by_status": {str(key): value for key, value in by_status.items()}
        or {str(s): 0 for s in ProjectStatus},
    }


# ---------------------------------------------------------------------------
# Cycle de vie de la plateforme
# ---------------------------------------------------------------------------
@router.get(
    "/platform",
    response_model=PlatformStatusRead,
    summary="Mode de la plateforme (bêta interne ou commercial)",
)
def platform_mode(_: CurrentAdmin) -> PlatformStatusRead:
    """En bêta interne, les administrateurs ne se voient opposer aucun quota.

    C'est voulu, et c'est exactement pour cela que l'information doit être
    visible : sans elle, on croirait les règles d'offre éprouvées alors
    qu'elles ne s'appliquent à personne dans l'équipe.
    """
    from app.core.platform import platform_status

    return PlatformStatusRead(**platform_status())


# ---------------------------------------------------------------------------
# IA
# ---------------------------------------------------------------------------
@router.get(
    "/ai/config", response_model=AIConfigRead, summary="Configuration du fournisseur d'IA"
)
def ai_config(db: DbSession, _: CurrentAdmin) -> AIConfigRead:
    return AIConfigService(db).read()


@router.put(
    "/ai/config", response_model=AIConfigRead, summary="Modifier la configuration d'IA"
)
def update_ai_config(
    payload: AIConfigUpdate, db: DbSession, admin: CurrentAdmin
) -> AIConfigRead:
    result = AIConfigService(db).update(payload, actor_id=admin.id)
    db.commit()
    return result


@router.post(
    "/ai/test",
    response_model=AIConfigTestResult,
    summary="Éprouver la configuration par un appel réel",
)
def test_ai_config(db: DbSession, admin: CurrentAdmin) -> AIConfigTestResult:
    """Appel réel et facturé : c'est la seule preuve qu'une clé fonctionne."""
    result = AIConfigService(db).test(actor_id=admin.id)
    db.commit()
    return result



@router.get("/stats/ai", summary="Consommation IA")
def ai_stats(db: DbSession, _: CurrentAdmin) -> dict:
    totals = db.execute(
        select(
            func.count(AIUsage.id),
            func.coalesce(func.sum(AIUsage.input_tokens), 0),
            func.coalesce(func.sum(AIUsage.output_tokens), 0),
            func.coalesce(func.sum(AIUsage.credits_consumed), 0),
            func.coalesce(func.avg(AIUsage.latency_ms), 0),
        )
    ).one()
    failures = int(
        db.scalar(select(func.count()).select_from(AIUsage).where(AIUsage.success.is_(False))) or 0
    )
    # L'etat effectif, pas les variables d'environnement : le fournisseur
    # et le modele peuvent avoir ete changes depuis l'administration, et
    # c'est ce qui part reellement qu'un administrateur doit lire ici.
    config = AIConfigService(db).read()
    return {
        "provider": config.active_provider,
        "model": config.effective_model or "non configuré",
        "calls": int(totals[0]),
        "input_tokens": int(totals[1]),
        "output_tokens": int(totals[2]),
        "credits_consumed": int(totals[3]),
        "average_latency_ms": round(float(totals[4]), 1),
        "failures": failures,
    }


# ---------------------------------------------------------------------------
# Abonnements
# ---------------------------------------------------------------------------
@router.get("/plans", summary="Lister les offres")
def list_plans(db: DbSession, _: CurrentAdmin) -> list[dict]:
    plans = CreditService(db).ensure_plans()
    db.commit()
    return [
        {
            "id": plan.id,
            "code": str(plan.code),
            "name": plan.name,
            "description": plan.description,
            "price_amount": plan.price_amount,
            "price_currency": plan.price_currency,
            "max_projects": plan.max_projects,
            "monthly_ai_credits": plan.monthly_ai_credits,
            "allows_export": plan.allows_export,
            "allows_matching": plan.allows_matching,
            "allows_collaboration": plan.allows_collaboration,
            "allows_advanced_budget": plan.allows_advanced_budget,
            "is_active": plan.is_active,
        }
        for plan in sorted(plans.values(), key=lambda item: item.sort_order)
    ]


@router.put("/plans/{plan_code}", summary="Modifier le prix ou les quotas d'une offre")
def update_plan(
    plan_code: PlanCode, payload: dict, db: DbSession, _: CurrentAdmin, t: Translator
) -> dict:
    plan = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == plan_code))
    if plan is None:
        raise NotFoundError("billing.planNotFound")

    editable = {
        "name",
        "description",
        "price_amount",
        "price_currency",
        "max_projects",
        "monthly_ai_credits",
        "allows_export",
        "allows_matching",
        "allows_collaboration",
        "allows_advanced_budget",
        "is_active",
    }
    for field, value in payload.items():
        if field in editable:
            setattr(plan, field, value)
    db.commit()
    db.refresh(plan)
    return {"detail": t("billing.planUpdated"), "code": str(plan.code)}


# ---------------------------------------------------------------------------
# Paiements et abonnements
# ---------------------------------------------------------------------------
@router.get("/payments", response_model=list[PaymentRead], summary="Paiements")
def list_payments(
    db: DbSession,
    _: CurrentAdmin,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[PaymentRead]:
    return [
        PaymentRead.model_validate(payment)
        for payment in SubscriptionService(db).list_payments(limit=limit)
    ]


@router.post(
    "/payments/{payment_id}/validate",
    response_model=PaymentRead,
    summary="Valider un encaissement hors ligne",
)
def validate_payment(payment_id: str, db: DbSession, admin: CurrentAdmin) -> PaymentRead:
    """Active l'abonnement d'un paiement encaissé hors ligne.

    C'est la contrepartie du mode `manual` : sans prestataire qui notifie, la
    validation est humaine — et tracée, le paiement gardant le nom de qui l'a
    validé.
    """
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise NotFoundError("billing.paymentNotFound")
    return PaymentRead.model_validate(
        SubscriptionService(db).mark_paid_manually(payment, admin)
    )


# ---------------------------------------------------------------------------
# Veille automatisée : validation des candidats
# ---------------------------------------------------------------------------
@router.get(
    "/candidates", response_model=list[CandidateRead], summary="File de validation de la veille"
)
def list_candidates(
    db: DbSession,
    _: CurrentAdmin,
    status: CandidateStatus | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[CandidateRead]:
    return [
        CandidateRead.model_validate(candidate)
        for candidate in IngestionService(db).list_candidates(status, limit)
    ]


@router.post(
    "/candidates/{candidate_id}/approve",
    response_model=Message,
    summary="Publier un candidat après relecture",
)
def approve_candidate(
    candidate_id: str,
    payload: CandidateApproval,
    db: DbSession,
    admin: CurrentAdmin,
    t: Translator,
) -> Message:
    """Crée le dispositif à partir du candidat relu.

    Les corrections apportées ici l'emportent sur ce qu'a extrait la veille :
    c'est la personne qui a lu la source.
    """
    service = IngestionService(db)
    candidate = service.get(candidate_id)
    opportunity = service.approve(candidate, admin, payload.model_dump(exclude_unset=True))
    return Message(detail=t("funding.opportunityPublished", name=opportunity.name))


@router.post(
    "/candidates/{candidate_id}/reject",
    response_model=CandidateRead,
    summary="Écarter un candidat",
)
def reject_candidate(
    candidate_id: str, payload: CandidateRejection, db: DbSession, admin: CurrentAdmin
) -> CandidateRead:
    service = IngestionService(db)
    candidate = service.get(candidate_id)
    return CandidateRead.model_validate(service.reject(candidate, admin, payload.note))
