"""Notifications, journal d'audit et parametres applicatifs."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import NotificationType

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notifications"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        SAEnum(NotificationType, native_enum=False, length=30),
        default=NotificationType.SYSTEM,
        nullable=False,
    )
    #: Texte rendu au moment de l'ecriture. C'est un cache, pas la source :
    #: il sert aux notifications anterieures a l'internationalisation, et a la
    #: deduplication, qui compare des titres. Les nouvelles notifications
    #: portent en plus leur cle et leurs parametres, et c'est de ceux-la que
    #: le texte est reconstruit, dans la langue de qui lit.
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    title_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    body_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    #: Variables des deux messages. Vide pour une notification sans cle.
    params: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="notifications")


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "audit_logs"

    user_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class AppSetting(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Parametres modifiables depuis l'administration (cles/valeurs typees)."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, default="", nullable=False)
    value_type: Mapped[str] = mapped_column(String(20), default="string", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
