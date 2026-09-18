"""Acces aux utilisateurs, profils et jetons de reinitialisation."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.user import EmailVerificationToken, PasswordResetToken, Profile, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(
            select(User)
            .options(selectinload(User.profile))
            .where(User.email == email.strip().lower())
        )

    def get_with_profile(self, user_id: str) -> User | None:
        return self.db.scalar(
            select(User).options(selectinload(User.profile)).where(User.id == user_id)
        )

    def email_exists(self, email: str) -> bool:
        return self.get_by_email(email) is not None

    def list_paginated(self, limit: int, offset: int) -> list[User]:
        stmt = (
            select(User)
            .options(selectinload(User.profile))
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(stmt))


class ProfileRepository(BaseRepository[Profile]):
    model = Profile

    def get_by_user(self, user_id: str) -> Profile | None:
        return self.db.scalar(select(Profile).where(Profile.user_id == user_id))


class _SingleUseTokenRepository(BaseRepository):
    """Jetons a usage unique envoyes par e-mail.

    Meme regle pour la reinitialisation et la confirmation d'adresse : un jeton
    deja consomme ou expire est traite comme inexistant, et emettre un nouveau
    jeton invalide les precedents.
    """

    def get_valid(self, token_hash: str):
        token = self.db.scalar(
            select(self.model).where(self.model.token_hash == token_hash)
        )
        if token is None or token.used_at is not None:
            return None
        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            return None
        return token

    def invalidate_for_user(self, user_id: str) -> None:
        now = datetime.now(UTC)
        tokens = self.db.scalars(
            select(self.model).where(
                self.model.user_id == user_id,
                self.model.used_at.is_(None),
            )
        )
        for token in tokens:
            token.used_at = now


class PasswordResetRepository(_SingleUseTokenRepository):
    model = PasswordResetToken


class EmailVerificationRepository(_SingleUseTokenRepository):
    model = EmailVerificationToken
