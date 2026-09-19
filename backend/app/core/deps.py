"""Dependances FastAPI : authentification, roles, acces aux ressources."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.errors import AuthenticationError, NotFoundError, PermissionDeniedError
from app.core.i18n import is_locale, request_locale, translate
from app.core.security import decode_token
from app.models.project import Project
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_translator(request: Request) -> Callable[..., str]:
    """Traduit dans la langue de l'appelant, au moment de l'appel.

    La langue est relue a chaque appel, et non capturee ici : la preference du
    compte n'est connue qu'apres `get_current_user`, et rien ne garantit
    l'ordre dans lequel FastAPI resout deux dependances soeurs.
    """

    def _translate(key: str, **params: object) -> str:
        return translate(request_locale(request), key, **params)

    return _translate


#: Injecte dans une route qui renvoie un message a afficher tel quel.
Translator = Annotated[Callable[..., str], Depends(get_translator)]


def get_current_user(
    request: Request,
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("auth.required")

    payload = decode_token(credentials.credentials, expected_type="access")
    if payload is None:
        raise AuthenticationError("auth.tokenInvalidOrExpired")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("auth.tokenInvalid")

    user = db.scalar(
        select(User).options(selectinload(User.profile)).where(User.id == user_id)
    )
    if user is None:
        raise AuthenticationError("auth.userNotFound")
    if not user.is_active:
        raise PermissionDeniedError("auth.accountSuspended")
    if payload.get("tv") != user.token_version:
        # Jeton emis avant un changement de mot de passe : il n'est plus valable.
        raise AuthenticationError("auth.sessionPasswordChanged")

    # La langue du compte l'emporte sur l'en-tete du navigateur des qu'on sait
    # a qui l'on parle : elle suit la personne d'un appareil a l'autre.
    preferred = user.profile.preferred_locale if user.profile else None
    if is_locale(preferred):
        request.state.locale = preferred
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_admin(current_user: CurrentUser) -> User:
    if not current_user.is_admin:
        raise PermissionDeniedError("auth.adminOnly")
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
        raise NotFoundError("project.notFound")
    return project


OwnedProject = Annotated[Project, Depends(get_owned_project)]


def require_subscription_open(current_user: CurrentUser) -> User:
    """Ferme la souscription pendant la beta privee.

    Pendant la phase interne, la plateforme n'est pas commercialisee : il ne
    doit pas etre possible d'engager un paiement. **Rien n'est supprime** —
    offres, prestataires, abonnements et historiques restent en place, et
    rouvrir tient au seul `PLATFORM_MODE=public`.

    La fermeture vaut pour **tout le monde, administrateurs compris** : ce
    n'est pas une contrainte d'offre opposee a un compte, c'est l'etat du
    produit. D'ou un controle sur le mode, et non sur l'utilisateur.

    Deux actions restent ouvertes, volontairement. **Resilier** : empecher
    quelqu'un de mettre fin a un abonnement souscrit avant la beta serait
    abusif. **Le webhook du prestataire** : un paiement deja engage doit
    pouvoir aboutir, sans quoi on encaisserait sans rien accorder.
    """
    from app.core.errors import AppError
    from app.core.platform import is_internal

    if is_internal():
        raise AppError(
            "billing.subscriptionClosed",
            code="subscription_closed",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    return current_user


def require_matching_access(db: DbSession, current_user: CurrentUser) -> User:
    """Réserve le rapprochement aux offres qui l'incluent (`allows_matching`).

    **La recherche de financements reste ouverte à tous** : c'est le cœur du
    produit, et un dispositif qu'on ne peut pas trouver ne sert à personne.
    Ce qui se réserve, c'est le calcul de compatibilité d'un projet et son
    explication — le travail, pas le catalogue.

    Ce drapeau existait depuis l'origine dans les offres (`FREE: false`,
    `PRO: true`) et la page de tarification l'annonçait déjà, mais rien ne
    l'appliquait : l'écran promettait une limite que le serveur ignorait.
    """
    from app.core.errors import QuotaExceededError
    from app.core.platform import commercial_rules_apply
    from app.services.credit_service import CreditService

    if not commercial_rules_apply(current_user):
        return current_user

    plan = CreditService(db).plan_for_user(current_user)
    if not plan.allows_matching:
        raise QuotaExceededError(
            "quota.matchingNotIncluded",
            params={"plan": plan.name},
            code="matching_not_included",
        )
    return current_user


def require_export_access(db: DbSession, current_user: CurrentUser) -> User:
    """Réserve l'export aux offres qui l'incluent (`allows_export`).

    Le drapeau vit en base et est modifiable depuis l'administration : ouvrir
    l'export à l'offre gratuite ne demande aucun changement de code.

    L'exemption des administrateurs passe par `commercial_rules_apply`, comme
    les quotas de projets et de crédits. Elle était auparavant inconditionnelle
    ici : deux définitions concurrentes de la même exemption auraient fini par
    diverger, et celle-ci ignorait le cycle de vie de la plateforme.
    """
    from app.core.errors import QuotaExceededError
    from app.core.platform import commercial_rules_apply
    from app.services.credit_service import CreditService

    if not commercial_rules_apply(current_user):
        return current_user

    plan = CreditService(db).plan_for_user(current_user)
    if not plan.allows_export:
        raise QuotaExceededError(
            "quota.exportNotIncluded",
            params={"plan": plan.name},
            code="export_not_included",
        )
    return current_user
