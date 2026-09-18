"""Schemas documents, versions et generation IA."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import DocumentStatus, DocumentType
from app.schemas.common import ORMModel

RefineAction = Literal["IMPROVE", "SHORTEN", "EXPAND", "CORRECT"]


class DocumentRead(ORMModel):
    id: str
    project_id: str
    document_type: DocumentType
    title: str
    content: str
    status: DocumentStatus
    current_version: int
    word_count: int
    created_at: datetime
    updated_at: datetime


class DocumentSummary(ORMModel):
    id: str
    project_id: str
    document_type: DocumentType
    title: str
    status: DocumentStatus
    current_version: int
    word_count: int
    updated_at: datetime


class DocumentUpdate(BaseModel):
    """Sauvegarde manuelle depuis l'editeur."""

    content: str
    title: str | None = Field(default=None, max_length=255)
    status: DocumentStatus | None = None
    note: str | None = Field(default=None, max_length=255)


class DocumentVersionRead(ORMModel):
    id: str
    document_id: str
    version_number: int
    word_count: int
    origin: str
    prompt_version: str | None = None
    ai_model: str | None = None
    note: str | None = None
    created_at: datetime


class DocumentVersionDetail(DocumentVersionRead):
    content: str


class GenerateRequest(BaseModel):
    """Options de generation.

    `target_duration_minutes` pilote la longueur cible d'un scenario
    (1 page A4 ~= 1 minute a l'ecran).
    """

    language: Literal["fr", "en"] | None = None
    target_duration_minutes: int | None = Field(default=None, ge=1, le=1200)
    additional_instructions: str | None = Field(default=None, max_length=2000)
    overwrite: bool = True


class RefineRequest(BaseModel):
    action: RefineAction
    instructions: str | None = Field(default=None, max_length=2000)


class GenerationResult(BaseModel):
    document: DocumentRead
    credits_consumed: int
    credits_remaining: int
    provider: str
    model: str
    prompt_version: str
    latency_ms: int
    #: Nombre d'appels au fournisseur (> 1 pour un scenario long, ecrit par segments).
    passes: int = 1
    #: Champs du projet que l'IA a juges manquants (voir regle "Information non fournie").
    missing_information: list[str] = Field(default_factory=list)
