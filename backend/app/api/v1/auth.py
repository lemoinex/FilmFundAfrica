"""Routes d'authentification."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUser, DbSession
from app.core.rate_limit import rate_limit_auth
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenPair,
    VerifyEmailRequest,
)
from app.schemas.common import Message
from app.schemas.user import UserRead
from app.services.auth_service import AuthService, serialize_user

router = APIRouter(prefix="/auth", tags=["Authentification"])


#: Réponse unique de l'inscription et du renvoi de lien : l'adresse soit-elle
#: libre ou déjà prise, l'appelant lit exactement la même phrase.
VERIFICATION_SENT = (
    "Si cette adresse peut être utilisée, un e-mail de confirmation vient d'être "
    "envoyé. Ouvrez le lien qu'il contient pour activer votre compte."
)


def _with_dev_token(message: str, token: str | None) -> Message:
    """Ajoute le jeton en développement, jamais ailleurs.

    Sans SMTP configuré, un développeur n'aurait aucun moyen d'activer le compte
    qu'il vient de créer. `AuthService` ne renvoie ce jeton qu'en environnement
    `development` : cette fonction ne peut donc pas le divulguer en production.
    """
    if token:
        message += f" [DEV] Jeton : {token}"
    return Message(detail=message)


@router.post(
    "/register",
    response_model=Message,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit_auth)],
    summary="Créer un compte",
)
def register(payload: RegisterRequest, db: DbSession) -> Message:
    """Accepte l'inscription sans dire si l'adresse est déjà prise.

    Répondre 409 sur une adresse existante permettait à n'importe qui de tester
    si une personne est inscrite. Le compte n'est actif qu'une fois le lien reçu
    par e-mail ouvert ; le titulaire d'une adresse déjà inscrite est prévenu de
    la tentative, et lui seul.
    """
    return _with_dev_token(VERIFICATION_SENT, AuthService(db).register(payload))


@router.post(
    "/verify-email",
    response_model=AuthResponse,
    dependencies=[Depends(rate_limit_auth)],
    summary="Confirmer son adresse e-mail",
)
def verify_email(payload: VerifyEmailRequest, db: DbSession) -> AuthResponse:
    """Active le compte et ouvre la session : le lien vaut preuve de possession."""
    return AuthService(db).verify_email(payload.token)


@router.post(
    "/resend-verification",
    response_model=Message,
    dependencies=[Depends(rate_limit_auth)],
    summary="Renvoyer le lien de confirmation",
)
def resend_verification(payload: ResendVerificationRequest, db: DbSession) -> Message:
    return _with_dev_token(VERIFICATION_SENT, AuthService(db).resend_verification(payload.email))


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
    # Reponse identique que le compte existe ou non : pas d'enumeration.
    return _with_dev_token(
        "Si un compte existe pour cette adresse, un lien de réinitialisation "
        "vient d'être envoyé.",
        AuthService(db).request_password_reset(payload.email),
    )


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
