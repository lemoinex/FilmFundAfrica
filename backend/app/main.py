"""Point d'entree de l'API FilmFund Africa."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import api_router
from app.api.v1.health import router as health_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import request_logging_middleware, setup_logging
from app.core.rate_limit import auth_limiter

logger = logging.getLogger("filmfund")

DESCRIPTION = """
API de **FilmFund Africa** — de l'idée au financement de votre projet audiovisuel.

Modules disponibles :

* **Authentification** — inscription, connexion, réinitialisation du mot de passe.
* **Projets** — CRUD complet, personnages, Project Readiness Score.
* **AI Writer** — génération de documents professionnels, versioning, retravail.
* **Export** — PDF, DOCX, archive ZIP.
* **Administration** — utilisateurs, offres, consommation IA.

Le score de compatibilité et le score de maturité sont des indicateurs d'aide à la
décision : ils ne garantissent en aucun cas l'obtention d'un financement.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(
        "démarrage de l'API",
        extra={"event": "startup"},
    )
    if auth_limiter.backend_name == "memory" and settings.is_production:
        logger.warning(
            "limitation de débit en mémoire : chaque réplique applique sa propre "
            "limite. Renseignez REDIS_URL pour une limite partagée.",
            extra={"event": "rate_limit_not_shared"},
        )
    if settings.ai_provider == "mock":
        logger.warning(
            "AI_PROVIDER=mock : les documents ne seront pas rédigés par une IA. "
            "Renseignez AI_PROVIDER et AI_API_KEY pour activer la génération réelle."
        )
    yield
    logger.info("arrêt de l'API", extra={"event": "shutdown"})


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=DESCRIPTION,
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "Content-Disposition"],
    )
    app.middleware("http")(request_logging_middleware)

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {
            "name": settings.app_name,
            "version": __version__,
            "docs": "/docs",
            "api": settings.api_v1_prefix,
        }

    return app


app = create_app()
