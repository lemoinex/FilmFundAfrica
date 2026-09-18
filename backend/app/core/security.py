"""Hashage des mots de passe et emission/verification des jetons JWT."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    # bcrypt ne prend en compte que les 72 premiers octets.
    return pwd_context.hash(password[:72])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password[:72], hashed_password)
    except ValueError:
        return False


def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(
    subject: str, role: str | None = None, token_version: int = 0
) -> str:
    """Jeton d'acces.

    Le claim `tv` porte la version de jeton du compte : elle est incrementee a
    chaque changement de mot de passe, ce qui invalide immediatement tous les
    jetons emis auparavant.
    """
    claims: dict[str, Any] = {"tv": token_version}
    if role:
        claims["role"] = role
    return _create_token(
        subject,
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
        claims,
    )


def create_refresh_token(subject: str, token_version: int = 0) -> str:
    return _create_token(
        subject,
        "refresh",
        timedelta(days=settings.refresh_token_expire_days),
        {"tv": token_version},
    )


def decode_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any] | None:
    """Retourne le payload si le jeton est valide, sinon None."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    if expected_type and payload.get("type") != expected_type:
        return None
    return payload


def generate_url_token() -> str:
    """Jeton opaque transmis par e-mail (reinitialisation, verification).

    Stocke hashe en base : une fuite de la table ne permet pas de forger un
    lien valide.
    """
    return secrets.token_urlsafe(48)


def hash_url_token(token: str) -> str:
    import hashlib

    return hashlib.sha256(token.encode("utf-8")).hexdigest()
