"""Sonde de sante et informations de configuration non sensibles."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.deps import DbSession

router = APIRouter(tags=["Système"])


@router.get("/health", summary="Sonde de santé")
def health(db: DbSession) -> dict:
    database_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - la sonde ne doit jamais lever
        database_ok = False

    return {
        "status": "ok" if database_ok else "degraded",
        "app": settings.app_name,
        "environment": settings.environment,
        "database": "ok" if database_ok else "unreachable",
        "ai_provider": settings.ai_provider,
        "ai_configured": settings.ai_provider == "mock" or bool(settings.ai_api_key),
    }
