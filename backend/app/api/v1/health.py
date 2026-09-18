"""Sonde de sante et informations de configuration non sensibles."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.deps import DbSession
from app.core.rate_limit import backend_status

router = APIRouter(tags=["Système"])


@router.get("/health", summary="Sonde de santé")
def health(db: DbSession) -> dict:
    database_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - la sonde ne doit jamais lever
        database_ok = False

    # Un deploiement configure pour une limite partagee qui ne l'obtient plus
    # applique en realite une limite par replique : la sonde doit le dire.
    rate_limit = backend_status()
    healthy = database_ok and rate_limit != "redis-unreachable"

    return {
        "status": "ok" if healthy else "degraded",
        "app": settings.app_name,
        "environment": settings.environment,
        "database": "ok" if database_ok else "unreachable",
        "rate_limit": rate_limit,
        "ai_provider": settings.ai_provider,
        "ai_configured": settings.ai_provider == "mock" or bool(settings.ai_api_key),
    }
