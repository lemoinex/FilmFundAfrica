"""Schemas d'authentification."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import UserType
from app.schemas.user import UserRead

MIN_PASSWORD_LENGTH = 8


def _validate_password_strength(value: str) -> str:
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères.")
    if value.isdigit() or value.isalpha():
        raise ValueError("Le mot de passe doit mêler lettres et chiffres.")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    user_type: UserType = UserType.AUTHOR
    country: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    profession: str | None = Field(default=None, max_length=160)

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return _validate_password_strength(value)

    @field_validator("user_type")
    @classmethod
    def forbid_self_admin(cls, value: UserType) -> UserType:
        # Le role ADMIN ne peut jamais etre obtenu par inscription publique.
        if value == UserType.ADMIN:
            raise ValueError("Ce type de compte ne peut pas être créé par inscription.")
        return value


class RegistrationStatus(BaseModel):
    """Etat de l'inscription, lisible sans etre authentifie.

    Le formulaire ne peut pas le deviner : sans cette reponse il proposerait
    une creation de compte que le serveur refuse, ou — s'il la masquait en
    dur — resterait ferme apres l'ouverture commerciale. La seule chose
    publiee est ce booleen ; ni le mode ni les dates de la beta n'ont a
    sortir d'ici.
    """

    open: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResponse(TokenPair):
    user: UserRead


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)

    @field_validator("new_password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return _validate_password_strength(value)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)

    @field_validator("new_password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return _validate_password_strength(value)
