"""Routes profil utilisateur."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.models.user import Profile
from app.schemas.user import ProfileUpdate, UserRead
from app.services.auth_service import serialize_user

router = APIRouter(prefix="/users", tags=["Utilisateurs"])


@router.get("/me", response_model=UserRead, summary="Mon compte")
def read_me(current_user: CurrentUser) -> UserRead:
    return serialize_user(current_user)


@router.put("/me/profile", response_model=UserRead, summary="Modifier mon profil")
def update_profile(
    payload: ProfileUpdate, db: DbSession, current_user: CurrentUser
) -> UserRead:
    if current_user.profile is None:
        current_user.profile = Profile(user_id=current_user.id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(current_user.profile, field, value)

    db.commit()
    db.refresh(current_user)
    return serialize_user(current_user)
