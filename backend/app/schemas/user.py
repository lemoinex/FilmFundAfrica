"""Schemas utilisateur et profil."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import PlanCode, UserType
from app.schemas.common import ORMModel


class ProfileRead(ORMModel):
    first_name: str
    last_name: str
    country: str | None = None
    city: str | None = None
    profession: str | None = None
    photo_url: str | None = None
    bio: str | None = None
    preferred_locale: str = "fr"


class ProfileUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    profession: str | None = Field(default=None, max_length=160)
    photo_url: str | None = Field(default=None, max_length=512)
    bio: str | None = None
    preferred_locale: str | None = Field(default=None, pattern="^(fr|en)$")


class UserRead(ORMModel):
    id: str
    email: EmailStr
    user_type: UserType
    is_active: bool
    is_verified: bool
    ai_credits_remaining: int
    created_at: datetime
    profile: ProfileRead | None = None
    plan_code: PlanCode | None = None


class AdminUserUpdate(BaseModel):
    user_type: UserType | None = None
    is_active: bool | None = None
    ai_credits_remaining: int | None = Field(default=None, ge=0)
