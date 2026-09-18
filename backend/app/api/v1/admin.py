"""Routes d'administration.

Toutes les routes exigent le role ADMIN. Les statistiques projets sont
anonymisees : aucun titre ni contenu de projet n'est exposé ici.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.core.config import settings
from app.core.deps import CurrentAdmin, DbSession
from app.core.errors import NotFoundError
from app.models.billing import AIUsage, SubscriptionPlan
from app.models.document import Document
from app.models.enums import PlanCode, ProjectStatus, ProjectType
from app.models.project import Project
from app.models.user import User
from app.schemas.common import Message
from app.schemas.user import AdminUserUpdate, UserRead
from app.services.auth_service import serialize_user
from app.services.credit_service import CreditService

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
        raise NotFoundError("Utilisateur introuvable.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return serialize_user(user)


@router.post("/users/{user_id}/suspend", response_model=Message, summary="Suspendre un compte")
def suspend_user(user_id: str, db: DbSession, admin: CurrentAdmin) -> Message:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Utilisateur introuvable.")
    if user.id == admin.id:
        from app.core.errors import AppError

        raise AppError("Vous ne pouvez pas suspendre votre propre compte.")
    user.is_active = False
    db.commit()
    return Message(detail="Compte suspendu.")


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
# IA
# ---------------------------------------------------------------------------
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
    return {
        "provider": settings.ai_provider,
        "model": settings.ai_model,
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
def update_plan(plan_code: PlanCode, payload: dict, db: DbSession, _: CurrentAdmin) -> dict:
    plan = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == plan_code))
    if plan is None:
        raise NotFoundError("Offre introuvable.")

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
    return {"detail": "Offre mise à jour.", "code": str(plan.code)}
