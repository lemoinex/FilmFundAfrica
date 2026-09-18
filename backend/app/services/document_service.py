"""AI Writer : generation, edition, versioning et restauration des documents.

Principe de coherence (cahier des charges §12) : un document n'est jamais
genere isolement. Le prompt recoit le contexte structure du projet ET le
contenu des documents dont il depend, afin que la note de realisation reste
coherente avec le synopsis, le traitement avec le synopsis long, etc.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import AIProviderError, AppError, NotFoundError
from app.models.document import Document, DocumentVersion
from app.models.enums import AIOperation, DocumentStatus, DocumentType
from app.models.project import Project
from app.models.user import User
from app.prompts import PromptContext, build_refine_prompt, get_prompt
from app.repositories.document import DocumentRepository, DocumentVersionRepository
from app.schemas.document import (
    DocumentRead,
    DocumentUpdate,
    GenerateRequest,
    GenerationResult,
    RefineRequest,
)
from app.services.ai.service import AIService, word_count
from app.services.credit_service import CreditService
from app.services.scoring_service import ScoringService
from app.services.screenplay_service import (
    SCREENPLAY_MAX_TOKENS_PER_CALL,
    ScreenplayState,
    assemble,
    build_segment_prompt,
    plan_segments,
)

logger = logging.getLogger("filmfund.documents")

LANGUAGE_LABELS = {"fr": "français", "en": "anglais"}

ORIGIN_BY_ACTION = {
    "IMPROVE": "AI_IMPROVE",
    "SHORTEN": "AI_SHORTEN",
    "EXPAND": "AI_EXPAND",
    "CORRECT": "AI_CORRECT",
}


@dataclass
class _Telemetry:
    """Cumul des métriques d'un ou plusieurs appels au fournisseur."""

    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    prompt_name: str | None = None


class DocumentService:
    def __init__(self, db: Session, ai_service: AIService | None = None) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.versions = DocumentVersionRepository(db)
        self.credits = CreditService(db)
        self.scoring = ScoringService(db)
        self._ai_service = ai_service

    @property
    def ai(self) -> AIService:
        if self._ai_service is None:
            self._ai_service = AIService()
        return self._ai_service

    # ------------------------------------------------------------------
    def get_owned_document(self, document_id: str, project: Project) -> Document:
        document = self.documents.get(document_id)
        if document is None or document.project_id != project.id:
            raise NotFoundError("Document introuvable.")
        return document

    # ------------------------------------------------------------------
    def build_context(self, project: Project, document_type: DocumentType) -> PromptContext:
        """Assemble le contexte du projet + les documents dont ce type depend."""
        template = get_prompt(document_type)
        available = self.documents.contents_by_type(project.id)
        dependencies: dict[str, str] = {}
        for dependency in template.depends_on:
            content = available.get(dependency)
            if content:
                dependencies[get_prompt(dependency).document_label] = content
        return PromptContext.from_project(project, existing_documents=dependencies)

    # ------------------------------------------------------------------
    def prepare_generation(
        self, project: Project, document_type: DocumentType, payload: GenerateRequest
    ) -> int:
        """Valide la demande et renvoie le nombre d'appels au fournisseur.

        Appelee avant la mise en file : un refus prévisible (type inapplicable,
        document déjà présent, scénario trop long) doit répondre tout de suite,
        pas échouer plus tard dans une tâche que l'utilisateur devra aller
        consulter. Aucun appel à l'IA ici — le découpage est déterministe.
        """
        template = get_prompt(document_type)
        if template.applies_to and project.project_type not in template.applies_to:
            raise AppError(
                f"Le document « {template.document_label} » ne s'applique pas à un projet "
                f"de type {project.project_type}.",
                code="document_type_not_applicable",
            )

        existing = self.documents.get_by_type(project.id, document_type)
        if existing is not None and existing.content.strip() and not payload.overwrite:
            raise AppError(
                "Ce document existe déjà. Activez « remplacer » pour le régénérer.",
                code="document_exists",
            )

        return len(self._plan_segments(project, document_type, payload)) or 1

    @staticmethod
    def prepare_refine(document: Document) -> None:
        if not document.content.strip():
            raise AppError(
                "Ce document est vide : générez-le avant de le retravailler.",
                code="document_empty",
            )

    def _plan_segments(
        self, project: Project, document_type: DocumentType, payload: GenerateRequest
    ) -> list:
        if document_type != DocumentType.SCREENPLAY:
            return []
        # Plafond par appel identique à celui de `/documents/screenplay-capacity` :
        # il ne dépend que du fournisseur, pas de la durée enregistrée sur le projet.
        return plan_segments(
            payload.target_duration_minutes or project.duration or 90,
            self.ai.effective_max_output_tokens(SCREENPLAY_MAX_TOKENS_PER_CALL),
        )

    # ------------------------------------------------------------------
    def generate(
        self,
        user: User,
        project: Project,
        document_type: DocumentType,
        payload: GenerateRequest,
        *,
        reserved_credits: int | None = None,
        on_pass: Callable[[int, int], None] | None = None,
    ) -> GenerationResult:
        """Génère un document.

        `reserved_credits` : les crédits ont déjà été débités à la mise en file
        de la tâche. On ne les débite donc pas une seconde fois ici, mais on
        journalise l'appel au fournisseur comme d'habitude.
        """
        template = get_prompt(document_type)
        passes = self.prepare_generation(project, document_type, payload)
        segments = self._plan_segments(project, document_type, payload)

        language = LANGUAGE_LABELS.get(payload.language or "fr", "français")
        context = self.build_context(project, document_type)

        cost = (
            self.credits.check_credits(user, AIOperation.GENERATE_DOCUMENT, units=passes)
            if reserved_credits is None
            else reserved_credits
        )

        if segments:
            text, telemetry = self._run_screenplay_passes(
                user=user,
                project=project,
                template=template,
                context=context,
                segments=segments,
                language=language,
                target_minutes=payload.target_duration_minutes or project.duration or 90,
                instructions=payload.additional_instructions,
                on_pass=on_pass,
            )
            prompt_version = template.version
        else:
            prompt = template.render(
                context,
                language=language,
                target_duration=payload.target_duration_minutes,
                additional_instructions=payload.additional_instructions,
            )
            response = self._run_or_log_failure(
                prompt, user, project, document_type, AIOperation.GENERATE_DOCUMENT
            )
            text = response.text
            prompt_version = prompt.prompt_version
            telemetry = _Telemetry(
                provider=response.provider,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
                prompt_name=prompt.prompt_name,
            )

        document = self._upsert_document(
            project=project,
            document_type=document_type,
            title=template.document_label,
            content=text,
            origin="AI_GENERATE",
            prompt_version=prompt_version,
            ai_model=telemetry.model,
        )

        consumed = self.credits.record_usage(
            user,
            operation=AIOperation.GENERATE_DOCUMENT,
            provider=telemetry.provider,
            model=telemetry.model,
            project_id=project.id,
            document_type=str(document_type),
            prompt_name=telemetry.prompt_name,
            prompt_version=prompt_version,
            input_tokens=telemetry.input_tokens,
            output_tokens=telemetry.output_tokens,
            latency_ms=telemetry.latency_ms,
            units=passes,
            # Deja debite a la mise en file : on journalise sans reprelever.
            consume=reserved_credits is None,
            # Les passes d'un scenario ont deja ete journalisees une par une.
            log_usage=not segments,
        )
        self._sync_project_fields(project, document_type, text)
        self.db.commit()
        self.db.refresh(document)
        self.scoring.compute(project)

        return GenerationResult(
            document=DocumentRead.model_validate(document),
            credits_consumed=consumed or cost,
            credits_remaining=user.ai_credits_remaining,
            provider=telemetry.provider,
            model=telemetry.model,
            prompt_version=prompt_version,
            latency_ms=telemetry.latency_ms,
            passes=passes,
            missing_information=AIService.extract_missing_information(text),
        )

    # ------------------------------------------------------------------
    def _run_or_log_failure(self, prompt, user, project, document_type, operation):
        """Exécute un prompt ; en cas d'échec, journalise sans débiter de crédit."""
        try:
            return self.ai.run(prompt)
        except AIProviderError as exc:
            self.credits.record_usage(
                user,
                operation=operation,
                provider=self.ai.provider.name,
                model=self.ai.model,
                project_id=project.id,
                document_type=str(document_type) if document_type else None,
                prompt_name=prompt.prompt_name,
                prompt_version=prompt.prompt_version,
                success=False,
                error_message=str(exc.detail),
                consume=False,
            )
            self.db.commit()
            raise

    def _run_screenplay_passes(
        self,
        *,
        user,
        project: Project,
        template,
        context,
        segments,
        language: str,
        target_minutes: int,
        instructions: str | None,
        on_pass: Callable[[int, int], None] | None = None,
    ) -> tuple[str, _Telemetry]:
        """Écrit le scénario segment par segment, avec continuité entre les passes."""
        parts: list[str] = []
        telemetry = _Telemetry(provider=self.ai.provider.name, model=self.ai.model)
        # Les faits etablis par TOUTES les passes precedentes, pas seulement la
        # derniere : un personnage du premier acte doit rester connu au dernier.
        state = ScreenplayState()

        for segment in segments:
            prompt = build_segment_prompt(
                template,
                context,
                segment,
                language=language,
                target_minutes=target_minutes,
                previous_text=parts[-1] if parts else "",
                user_instructions=instructions,
                state=state,
            )
            response = self._run_or_log_failure(
                prompt, user, project, DocumentType.SCREENPLAY, AIOperation.GENERATE_DOCUMENT
            )
            parts.append(response.text)
            state.absorb(response.text, segment.label)

            # Chaque passe réussie est journalisée immédiatement : si une passe
            # ultérieure échoue, les appels déjà facturés par le fournisseur
            # restent visibles dans les statistiques. Le débit des crédits, lui,
            # reste groupé sur la génération complète.
            self.credits.record_usage(
                user,
                operation=AIOperation.GENERATE_DOCUMENT,
                provider=response.provider,
                model=response.model,
                project_id=project.id,
                document_type=str(DocumentType.SCREENPLAY),
                prompt_name=prompt.prompt_name,
                prompt_version=prompt.prompt_version,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
                consume=False,
            )
            self.db.flush()

            telemetry.provider = response.provider
            telemetry.model = response.model
            telemetry.input_tokens += response.input_tokens
            telemetry.output_tokens += response.output_tokens
            telemetry.latency_ms += response.latency_ms
            telemetry.prompt_name = prompt.prompt_name

            logger.info(
                "segment de scénario généré",
                extra={
                    "event": "screenplay_segment",
                    "duration_ms": response.latency_ms,
                },
            )

            # L'utilisateur voit avancer une génération qui dure plusieurs
            # minutes, plutôt qu'un écran figé.
            if on_pass is not None:
                on_pass(len(parts), len(segments))

        return assemble(parts), telemetry

    # ------------------------------------------------------------------
    def refine(
        self,
        user: User,
        project: Project,
        document: Document,
        payload: RefineRequest,
        *,
        reserved_credits: int | None = None,
    ) -> GenerationResult:
        self.prepare_refine(document)

        cost = (
            self.credits.check_credits(user, AIOperation.IMPROVE_DOCUMENT)
            if reserved_credits is None
            else reserved_credits
        )
        prompt = build_refine_prompt(
            payload.action,
            document.title,
            document.content,
            self.build_context(project, document.document_type),
            instructions=payload.instructions,
        )

        response = self._run_or_log_failure(
            prompt, user, project, document.document_type, AIOperation.IMPROVE_DOCUMENT
        )

        self._store_version(
            document,
            content=response.text,
            origin=ORIGIN_BY_ACTION.get(payload.action, "AI_IMPROVE"),
            prompt_version=prompt.prompt_version,
            ai_model=response.model,
        )
        consumed = self.credits.record_usage(
            user,
            operation=AIOperation.IMPROVE_DOCUMENT,
            provider=response.provider,
            model=response.model,
            project_id=project.id,
            document_type=str(document.document_type),
            prompt_name=prompt.prompt_name,
            prompt_version=prompt.prompt_version,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=response.latency_ms,
            # Deja debite a la mise en file : on journalise sans reprelever.
            consume=reserved_credits is None,
        )
        self._sync_project_fields(project, document.document_type, response.text)
        self.db.commit()
        self.db.refresh(document)
        self.scoring.compute(project)

        return GenerationResult(
            document=DocumentRead.model_validate(document),
            credits_consumed=consumed or cost,
            credits_remaining=user.ai_credits_remaining,
            provider=response.provider,
            model=response.model,
            prompt_version=prompt.prompt_version,
            latency_ms=response.latency_ms,
            missing_information=AIService.extract_missing_information(response.text),
        )

    # ------------------------------------------------------------------
    def save_manual(
        self, project: Project, document: Document, payload: DocumentUpdate
    ) -> Document:
        """Sauvegarde depuis l'editeur ; ne cree une version que si le texte change."""
        if payload.title:
            document.title = payload.title
        if payload.status:
            document.status = payload.status

        if payload.content.strip() != document.content.strip():
            self._store_version(
                document,
                content=payload.content,
                origin="MANUAL",
                note=payload.note,
            )
        self.db.commit()
        self.db.refresh(document)
        self._sync_project_fields(project, document.document_type, document.content)
        self.db.commit()
        self.scoring.compute(project)
        return document

    # ------------------------------------------------------------------
    def create_empty(
        self, project: Project, document_type: DocumentType, content: str = ""
    ) -> Document:
        template = get_prompt(document_type)
        return self._upsert_document(
            project=project,
            document_type=document_type,
            title=template.document_label,
            content=content,
            origin="MANUAL",
        )

    # ------------------------------------------------------------------
    def restore_version(
        self, project: Project, document: Document, version_number: int
    ) -> Document:
        version = self.versions.get_version(document.id, version_number)
        if version is None:
            raise NotFoundError("Version introuvable.")
        self._store_version(
            document,
            content=version.content,
            origin="RESTORE",
            note=f"Restauration de la version {version_number}",
        )
        self._sync_project_fields(project, document.document_type, document.content)
        self.db.commit()
        self.db.refresh(document)
        self.scoring.compute(project)
        return document

    # ------------------------------------------------------------------
    def delete(self, project: Project, document: Document) -> None:
        self.db.delete(document)
        self.db.commit()
        self.scoring.compute(project)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _upsert_document(
        self,
        *,
        project: Project,
        document_type: DocumentType,
        title: str,
        content: str,
        origin: str,
        prompt_version: str | None = None,
        ai_model: str | None = None,
    ) -> Document:
        document = self.documents.get_by_type(project.id, document_type)
        if document is None:
            document = Document(
                project_id=project.id,
                document_type=document_type,
                title=title,
                content="",
                status=DocumentStatus.DRAFT,
                current_version=0,
            )
            self.documents.add(document)
            self.db.flush()

        self._store_version(
            document,
            content=content,
            origin=origin,
            prompt_version=prompt_version,
            ai_model=ai_model,
        )
        return document

    def _store_version(
        self,
        document: Document,
        *,
        content: str,
        origin: str,
        prompt_version: str | None = None,
        ai_model: str | None = None,
        note: str | None = None,
    ) -> DocumentVersion:
        version_number = self.versions.next_version_number(document.id)
        words = word_count(content)

        version = DocumentVersion(
            document_id=document.id,
            version_number=version_number,
            content=content,
            word_count=words,
            origin=origin,
            prompt_version=prompt_version,
            ai_model=ai_model,
            note=note,
        )
        self.db.add(version)

        document.content = content
        document.word_count = words
        document.current_version = version_number
        document.updated_at = datetime.now(UTC)
        self.db.flush()
        return version

    @staticmethod
    def _sync_project_fields(project: Project, document_type: DocumentType, content: str) -> None:
        """Recopie certains documents courts dans les champs du projet.

        Le tableau de bord, le score de maturité et le contexte transmis aux
        prompts suivants lisent `logline`, `short_synopsis` et `long_synopsis` :
        ces champs doivent refléter la DERNIÈRE version du document, sans quoi
        tous les documents générés ensuite travailleraient sur un texte périmé.
        """
        text = content.strip()
        if not text:
            return

        if document_type == DocumentType.LOGLINE:
            # Le document contient un titre Markdown et des variantes : on ne
            # retient que la première ligne de contenu réel.
            first_line = next(
                (
                    line.strip()
                    for line in text.splitlines()
                    if line.strip() and not line.startswith(("#", ">", "-", "*"))
                ),
                "",
            )
            if first_line:
                project.logline = first_line[:1000]
        elif document_type == DocumentType.SHORT_SYNOPSIS:
            project.short_synopsis = text
        elif document_type == DocumentType.LONG_SYNOPSIS:
            project.long_synopsis = text
