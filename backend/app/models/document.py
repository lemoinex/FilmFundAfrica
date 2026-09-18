"""Documents generes et historique de versions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import DocumentStatus, DocumentType

if TYPE_CHECKING:  # pragma: no cover
    from app.models.project import Project


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Un document par type et par projet : son contenu courant est `content`.

    Chaque sauvegarde cree une entree dans `document_versions`.
    """

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("project_id", "document_type", name="uq_document_project_type"),
    )

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, native_enum=False, length=30), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus, native_enum=False, length=20),
        default=DocumentStatus.DRAFT,
        nullable=False,
    )
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Langue dans laquelle le document est redige, et non celle du projet : un
    # film en wolof se presente a un fonds francophone en francais. Sans elle,
    # un retravail repartirait sur la langue par defaut et corrigerait un texte
    # anglais selon la typographie francaise.
    language: Mapped[str] = mapped_column(String(2), default="fr", nullable=False)

    project: Mapped[Project] = relationship(back_populates="documents")
    versions: Mapped[list[DocumentVersion]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.version_number.desc()",
    )


class DocumentVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_version_document_number"),
    )

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: MANUAL | AI_GENERATE | AI_IMPROVE | AI_SHORTEN | AI_EXPAND | AI_CORRECT | RESTORE
    origin: Mapped[str] = mapped_column(String(30), default="MANUAL", nullable=False)
    #: Version du prompt utilisee, pour tracer la qualite des generations.
    prompt_version: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    document: Mapped[Document] = relationship(back_populates="versions")
