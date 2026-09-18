"""Routes tableau de bord et notifications."""

from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, Translator
from app.core.errors import NotFoundError
from app.models.system import Notification
from app.schemas.common import Message
from app.schemas.dashboard import DashboardResponse, NotificationRead
from app.services.dashboard_service import DashboardService

router = APIRouter(tags=["Tableau de bord"])


@router.get("/dashboard", response_model=DashboardResponse, summary="Tableau de bord")
def dashboard(db: DbSession, current_user: CurrentUser) -> DashboardResponse:
    return DashboardService(db).build(current_user)


@router.get(
    "/notifications", response_model=list[NotificationRead], summary="Mes notifications"
)
def list_notifications(
    db: DbSession,
    current_user: CurrentUser,
    unread_only: bool = Query(default=False),
    limit: int = Query(default=30, ge=1, le=100),
) -> list[NotificationRead]:
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
    return [
        NotificationRead(
            id=item.id,
            title=item.title,
            body=item.body,
            notification_type=str(item.notification_type),
            link=item.link,
            is_read=item.is_read,
            created_at=item.created_at,
        )
        for item in db.scalars(stmt)
    ]


@router.post(
    "/notifications/{notification_id}/read",
    response_model=Message,
    summary="Marquer comme lue",
)
def mark_read(
    notification_id: str, db: DbSession, current_user: CurrentUser, t: Translator
) -> Message:
    from datetime import datetime

    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != current_user.id:
        raise NotFoundError("notification.notFound")
    notification.is_read = True
    notification.read_at = datetime.now(UTC)
    db.commit()
    return Message(detail=t("notification.markedRead"))
