"""Agregation des routes de l'API v1."""

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    admin_funding,
    auth,
    automation,
    billing,
    budget,
    dashboard,
    documents,
    dossier,
    exports,
    funding,
    jobs,
    projects,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(projects.router)
api_router.include_router(budget.router)
api_router.include_router(documents.catalog_router)
api_router.include_router(documents.router)
api_router.include_router(dossier.router)
api_router.include_router(exports.router)
api_router.include_router(funding.router)
api_router.include_router(funding.project_router)
api_router.include_router(jobs.router)
api_router.include_router(jobs.project_router)
api_router.include_router(billing.router)
api_router.include_router(dashboard.router)
api_router.include_router(admin.router)
api_router.include_router(admin_funding.router)
api_router.include_router(automation.router)

__all__ = ["api_router"]
