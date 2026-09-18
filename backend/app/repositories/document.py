"""Acces aux documents et a leurs versions."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentVersion
from app.models.enums import DocumentType
from app.models.project import Project
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    model = Document

    def list_for_project(self, project_id: str) -> list[Document]:
        stmt = (
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.updated_at.desc())
        )
        return list(self.db.scalars(stmt))

    def get_by_type(self, project_id: str, document_type: DocumentType) -> Document | None:
        return self.db.scalar(
            select(Document).where(
                Document.project_id == project_id,
                Document.document_type == document_type,
            )
        )

    def get_with_versions(self, document_id: str) -> Document | None:
        return self.db.scalar(
            select(Document)
            .options(selectinload(Document.versions))
            .where(Document.id == document_id)
        )

    def count_for_user(self, user_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(Document)
                .join(Project, Project.id == Document.project_id)
                .where(Project.user_id == user_id)
            )
            or 0
        )

    def contents_by_type(self, project_id: str) -> dict[DocumentType, str]:
        rows = self.db.execute(
            select(Document.document_type, Document.content).where(
                Document.project_id == project_id
            )
        )
        return {doc_type: content for doc_type, content in rows if content and content.strip()}


class DocumentVersionRepository(BaseRepository[DocumentVersion]):
    model = DocumentVersion

    def list_for_document(self, document_id: str) -> list[DocumentVersion]:
        stmt = (
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())
        )
        return list(self.db.scalars(stmt))

    def get_version(self, document_id: str, version_number: int) -> DocumentVersion | None:
        return self.db.scalar(
            select(DocumentVersion).where(
                DocumentVersion.document_id == document_id,
                DocumentVersion.version_number == version_number,
            )
        )

    def next_version_number(self, document_id: str) -> int:
        current = self.db.scalar(
            select(func.max(DocumentVersion.version_number)).where(
                DocumentVersion.document_id == document_id
            )
        )
        return int(current or 0) + 1
