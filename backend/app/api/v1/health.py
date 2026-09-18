"""Sonde de sante et informations de configuration non sensibles."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.deps import DbSession
from app.core.observability import sentry_status
from app.core.rate_limit import backend_status
from app.services.job_queue import job_queue

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

    # Sans worker, l'API genere elle-meme : c'est fonctionnel mais lent sur un
    # scenario long. L'etat doit etre visible sans lire les journaux.
    if not settings.redis_url.strip():
        generation = "inline"
    else:
        generation = "worker" if job_queue.worker_alive() else "inline-no-worker"

    return {
        "status": "ok" if healthy else "degraded",
        "app": settings.app_name,
        "environment": settings.environment,
        "database": "ok" if database_ok else "unreachable",
        "rate_limit": rate_limit,
        "generation": generation,
        "jobs_pending": job_queue.pending(),
        # `unavailable` : un DSN est configure mais le paquet manque. Le
        # deploiement croit alors etre suivi sans l'etre — d'ou la sonde.
        "error_tracking": sentry_status(),
        "ai_provider": settings.ai_provider,
        "ai_configured": settings.ai_provider == "mock" or bool(settings.ai_api_key),
    }
