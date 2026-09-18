"""Inscription, connexion, rafraichissement et reinitialisation de mot de passe."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AuthenticationError, NotFoundError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_url_token,
    hash_password,
    hash_url_token,
    verify_password,
)
from app.models.enums import PlanCode
from app.models.user import EmailVerificationToken, PasswordResetToken, Profile, User
from app.repositories.user import (
    EmailVerificationRepository,
    PasswordResetRepository,
    UserRepository,
)
from app.schemas.auth import AuthResponse, RegisterRequest, TokenPair
from app.schemas.user import UserRead
from app.services.credit_service import CreditService
from app.services.email_service import EmailService

logger = logging.getLogger("filmfund.auth")

#: Hachage d'un mot de passe inexistant, verifie lorsqu'un compte est introuvable
#: afin que la reponse prenne le meme temps qu'une authentification reelle.
DUMMY_PASSWORD_HASH = hash_password("mot-de-passe-inexistant-pour-temps-constant")


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.resets = PasswordResetRepository(db)
        self.verifications = EmailVerificationRepository(db)
        self.credits = CreditService(db)
        self.email = EmailService()

    # ------------------------------------------------------------------
    def register(self, payload: RegisterRequest) -> str | None:
        """Cree un compte non confirme et envoie le lien d'activation.

        La reponse est la MEME que l'adresse soit libre ou deja prise : un 409
        sur adresse existante permettait a n'importe qui de tester si une
        personne est inscrite. C'est le titulaire de l'adresse, et lui seul, qui
        apprend la tentative — par e-mail.

        Le mot de passe est hache dans les deux cas : sans cela, la branche
        « adresse deja prise » repondrait en quelques millisecondes la ou l'autre
        en prend deux cents, et l'ecart de temps rendrait le 409 supprime.

        Retourne le jeton en clair UNIQUEMENT en environnement `development`,
        comme la reinitialisation de mot de passe : le renvoyer ailleurs
        permettrait d'activer un compte ouvert avec l'adresse d'autrui.
        """
        email = payload.email.strip().lower()
        hashed = hash_password(payload.password)

        existing = self.users.get_by_email(email)
        if existing is not None:
            self.email.send_registration_attempt(existing.email)
            logger.info(
                "inscription sur adresse déjà utilisée",
                extra={"event": "register_existing_email"},
            )
            return None

        user = User(
            email=email,
            hashed_password=hashed,
            user_type=payload.user_type,
            is_active=True,
            is_verified=False,
        )
        user.profile = Profile(
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            country=payload.country,
            city=payload.city,
            profession=payload.profession,
        )
        self.users.add(user)
        self.credits.attach_default_plan(user)
        self.db.commit()
        self.db.refresh(user)

        logger.info("inscription", extra={"event": "user_registered"})
        return self._issue_verification(user)

    # ------------------------------------------------------------------
    def _issue_verification(self, user: User) -> str | None:
        """Emet un lien de confirmation et invalide les precedents."""
        self.verifications.invalidate_for_user(user.id)
        raw_token = generate_url_token()
        self.verifications.add(
            EmailVerificationToken(
                user_id=user.id,
                token_hash=hash_url_token(raw_token),
                expires_at=datetime.now(UTC)
                + timedelta(minutes=settings.email_verification_expire_minutes),
                created_at=datetime.now(UTC),
            )
        )
        self.db.commit()

        verify_url = f"{settings.frontend_url}/verifier-email?token={raw_token}"
        self.email.send_email_verification(user.email, verify_url)
        return raw_token if settings.is_development else None

    # ------------------------------------------------------------------
    def verify_email(self, raw_token: str) -> AuthResponse:
        """Active le compte et ouvre la session dans la foulee."""
        token = self.verifications.get_valid(hash_url_token(raw_token))
        if token is None:
            raise AuthenticationError("Lien de confirmation invalide ou expiré.")
        user = self.users.get(token.user_id)
        if user is None:
            raise NotFoundError("Compte introuvable.")

        user.is_verified = True
        token.used_at = datetime.now(UTC)
        user.last_login_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(user)
        logger.info("adresse confirmée", extra={"event": "email_verified"})
        return self._auth_response(user)

    # ------------------------------------------------------------------
    def resend_verification(self, email: str) -> str | None:
        """Renvoie le lien de confirmation, sans jamais dire si le compte existe."""
        user = self.users.get_by_email(email)
        if user is None or user.is_verified:
            return None
        return self._issue_verification(user)

    # ------------------------------------------------------------------
    def login(self, email: str, password: str) -> AuthResponse:
        user = self.users.get_by_email(email)
        # Message identique dans tous les cas : pas d'enumeration de comptes.
        invalid = AuthenticationError("Adresse e-mail ou mot de passe incorrect.")

        # Le hachage est verifie meme lorsque le compte n'existe pas : sans cela,
        # l'ecart de temps de reponse revele quelles adresses sont inscrites.
        if user is None:
            verify_password(password, DUMMY_PASSWORD_HASH)
            raise invalid
        if not verify_password(password, user.hashed_password):
            raise invalid
        if not user.is_active:
            raise AuthenticationError("Ce compte est suspendu.")
        if not user.is_verified:
            # Ce message n'est atteignable qu'avec le bon mot de passe : il ne
            # revele donc rien a qui ne connait pas deja le compte.
            raise AuthenticationError(
                "Adresse non confirmée. Ouvrez le lien reçu par e-mail, "
                "ou demandez-en un nouveau.",
                code="email_not_verified",
            )

        user.last_login_at = datetime.now(UTC)
        self.credits.refresh_period_if_needed(user)
        self.db.commit()
        self.db.refresh(user)
        return self._auth_response(user)

    # ------------------------------------------------------------------
    def refresh(self, refresh_token: str) -> TokenPair:
        payload = decode_token(refresh_token, expected_type="refresh")
        if payload is None:
            raise AuthenticationError("Jeton de rafraîchissement invalide ou expiré.")
        user = self.users.get(payload.get("sub", ""))
        if user is None or not user.is_active:
            raise AuthenticationError("Compte introuvable ou suspendu.")
        if payload.get("tv") != user.token_version:
            # Le mot de passe a change depuis l'emission de ce jeton.
            raise AuthenticationError(
                "Session expirée : le mot de passe a été modifié. Reconnectez-vous."
            )
        return self._token_pair(user)

    # ------------------------------------------------------------------
    def request_password_reset(self, email: str) -> str | None:
        """Cree un jeton de reinitialisation.

        Retourne le jeton en clair UNIQUEMENT en environnement `development`
        (pour les tests et le developpement local sans SMTP). En staging comme
        en production, il n'est jamais renvoye par l'API : le renvoyer
        permettrait de prendre le controle de n'importe quel compte connu.
        L'appelant repond toujours la meme chose, que le compte existe ou non.
        """
        user = self.users.get_by_email(email)
        if user is None:
            return None

        self.resets.invalidate_for_user(user.id)
        raw_token = generate_url_token()
        self.resets.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_url_token(raw_token),
                expires_at=datetime.now(UTC)
                + timedelta(minutes=settings.password_reset_expire_minutes),
                created_at=datetime.now(UTC),
            )
        )
        self.db.commit()

        reset_url = f"{settings.frontend_url}/reinitialiser-mot-de-passe?token={raw_token}"
        self.email.send_password_reset(user.email, reset_url)
        return raw_token if settings.is_development else None

    # ------------------------------------------------------------------
    def reset_password(self, raw_token: str, new_password: str) -> None:
        token = self.resets.get_valid(hash_url_token(raw_token))
        if token is None:
            raise AuthenticationError("Lien de réinitialisation invalide ou expiré.")
        user = self.users.get(token.user_id)
        if user is None:
            raise NotFoundError("Compte introuvable.")

        user.hashed_password = hash_password(new_password)
        # Invalide tous les jetons emis avant la reinitialisation : c'est la
        # remediation d'un compte compromis, l'attaquant doit etre deconnecte.
        user.token_version += 1
        token.used_at = datetime.now(UTC)
        self.db.commit()

    # ------------------------------------------------------------------
    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Mot de passe actuel incorrect.")
        user.hashed_password = hash_password(new_password)
        user.token_version += 1
        self.db.commit()

    # ------------------------------------------------------------------
    def _token_pair(self, user: User) -> TokenPair:
        return TokenPair(
            access_token=create_access_token(
                user.id, role=str(user.user_type), token_version=user.token_version
            ),
            refresh_token=create_refresh_token(user.id, token_version=user.token_version),
            expires_in=settings.access_token_expire_minutes * 60,
        )

    def _auth_response(self, user: User) -> AuthResponse:
        tokens = self._token_pair(user)
        return AuthResponse(
            **tokens.model_dump(),
            user=serialize_user(user),
        )


def serialize_user(user: User) -> UserRead:
    plan_code: PlanCode | None = None
    if user.subscription is not None and user.subscription.plan is not None:
        plan_code = user.subscription.plan.code
    data = UserRead.model_validate(user)
    return data.model_copy(update={"plan_code": plan_code})
