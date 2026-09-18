"""Dependances FastAPI : authentification, roles, acces aux ressources."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.errors import AuthenticationError, NotFoundError, PermissionDeniedError
from app.core.security import decode_token
from app.models.project import Project
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Authentification requise.")

    payload = decode_token(credentials.credentials, expected_type="access")
    if payload is None:
        raise AuthenticationError("Jeton invalide ou expiré.")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Jeton invalide.")

    user = db.scalar(
        select(User).options(selectinload(User.profile)).where(User.id == user_id)
    )
    if user is None:
        raise AuthenticationError("Utilisateur introuvable.")
    if not user.is_active:
        raise PermissionDeniedError("Ce compte est suspendu.")
    if payload.get("tv") != user.token_version:
        # Jeton emis avant un changement de mot de passe : il n'est plus valable.
        raise AuthenticationError(
            "Session expirée : le mot de passe a été modifié. Reconnectez-vous."
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_admin(current_user: CurrentUser) -> User:
    if not current_user.is_admin:
        raise PermissionDeniedError("Accès réservé aux administrateurs.")
    return current_user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]


def get_owned_project(project_id: str, db: DbSession, current_user: CurrentUser) -> Project:
    """Charge un projet en garantissant l'isolation des donnees utilisateur.

    Un utilisateur ne peut jamais acceder au projet d'un autre utilisateur :
    on renvoie 404 (et non 403) pour ne pas divulguer l'existence du projet.
    """
    project = db.scalar(
        select(Project)
        .options(selectinload(Project.characters))
        .where(Project.id == project_id)
    )
    if project is None or project.user_id != current_user.id:
        raise NotFoundError("Projet introuvable.")
    return project


OwnedProject = Annotated[Project, Depends(get_owned_project)]


def require_export_access(db: DbSession, current_user: CurrentUser) -> User:
    """Réserve l'export aux offres qui l'incluent (`allows_export`).

    Le drapeau vit en base et est modifiable depuis l'administration : ouvrir
    l'export à l'offre gratuite ne demande aucun changement de code.
    """
    from app.core.errors import QuotaExceededError
    from app.services.credit_service import CreditService

    plan = CreditService(db).plan_for_user(current_user)
    if not plan.allows_export and not current_user.is_admin:
        raise QuotaExceededError(
            f"L'export n'est pas inclus dans l'offre « {plan.name} ». "
            "Passez à une offre supérieure pour exporter votre dossier.",
            code="export_not_included",
        )
    return current_user


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
