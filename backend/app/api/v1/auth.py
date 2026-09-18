"""Routes d'authentification."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.core.rate_limit import rate_limit_auth
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenPair,
)
from app.schemas.common import Message
from app.schemas.user import UserRead
from app.services.auth_service import AuthService, serialize_user

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_auth)],
    summary="Créer un compte",
)
def register(payload: RegisterRequest, db: DbSession) -> AuthResponse:
    return AuthService(db).register(payload)


@router.post(
    "/login",
    response_model=AuthResponse,
    dependencies=[Depends(rate_limit_auth)],
    summary="Se connecter",
)
def login(payload: LoginRequest, db: DbSession) -> AuthResponse:
    return AuthService(db).login(payload.email, payload.password)


@router.post("/refresh", response_model=TokenPair, summary="Rafraîchir le jeton d'accès")
def refresh(payload: RefreshRequest, db: DbSession) -> TokenPair:
    return AuthService(db).refresh(payload.refresh_token)


@router.post(
    "/logout",
    response_model=Message,
    summary="Se déconnecter",
)
def logout(_: CurrentUser) -> Message:
    # Les jetons sont sans etat : la deconnexion est effectuee cote client en
    # supprimant les jetons stockes. La route existe pour tracer l'action et
    # offrir un point d'extension (liste de revocation).
    return Message(detail="Déconnexion effectuée.")


@router.get("/me", response_model=UserRead, summary="Profil de l'utilisateur connecté")
def me(current_user: CurrentUser) -> UserRead:
    return serialize_user(current_user)


@router.post(
    "/forgot-password",
    response_model=Message,
    dependencies=[Depends(rate_limit_auth)],
    summary="Demander un lien de réinitialisation",
)
def forgot_password(payload: ForgotPasswordRequest, db: DbSession) -> Message:
    debug_token = AuthService(db).request_password_reset(payload.email)
    # Reponse identique que le compte existe ou non : pas d'enumeration.
    message = (
        "Si un compte existe pour cette adresse, un lien de réinitialisation vient d'être envoyé."
    )
    if debug_token and not settings.is_production:
        message += f" [DEV] Jeton : {debug_token}"
    return Message(detail=message)


@router.post(
    "/reset-password",
    response_model=Message,
    dependencies=[Depends(rate_limit_auth)],
    summary="Définir un nouveau mot de passe",
)
def reset_password(payload: ResetPasswordRequest, db: DbSession) -> Message:
    AuthService(db).reset_password(payload.token, payload.new_password)
    return Message(detail="Mot de passe mis à jour. Vous pouvez vous connecter.")


@router.post(
    "/change-password",
    response_model=Message,
    summary="Changer son mot de passe",
)
def change_password(
    payload: ChangePasswordRequest, db: DbSession, current_user: CurrentUser
) -> Message:
    AuthService(db).change_password(
        current_user, payload.current_password, payload.new_password
    )
    return Message(detail="Mot de passe mis à jour.")
