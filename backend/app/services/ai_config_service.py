"""Configuration du fournisseur d'IA depuis l'administration.

Deux choses seulement, mais qui ne doivent jamais se tromper : dire l'etat
reel (quelle cle s'applique, d'ou elle vient, quel modele partira) et
enregistrer une modification sans que le secret n'apparaisse ou que ce soit
— ni dans une reponse, ni dans un journal, ni dans une trace d'audit.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.models.system import AuditLog
from app.schemas.settings import (
    AIConfigRead,
    AIConfigTestResult,
    AIConfigUpdate,
    AIProviderState,
)
from app.services.ai.credentials import effective_provider
from app.services.settings_service import (
    KEY_AI_MODEL,
    KEY_AI_PROVIDER,
    SettingsService,
    ai_key_setting,
)

logger = logging.getLogger("filmfund.ai")

#: Ordre d'affichage. `mock` en dernier : c'est un repli, pas un choix.
PROVIDERS: tuple[str, ...] = ("anthropic", "openai", "mock")

#: Fournisseurs qui appellent un tiers, et exigent donc une cle.
NEEDS_KEY: frozenset[str] = frozenset({"anthropic", "openai"})

#: Question posee lors d'un essai. Courte a dessein : l'essai verifie qu'un
#: appel aboutit, pas la qualite de la reponse, et chaque jeton est facture.
TEST_PROMPT = "Réponds exactement : OK"
TEST_MAX_TOKENS = 512


class AIConfigService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings_service = SettingsService(db)

    # ------------------------------------------------------------------
    def _default_model(self, provider: str) -> str:
        """Defaut declare par la classe du fournisseur, sans la construire.

        La construire exigerait une cle — or on decrit justement l'etat d'un
        fournisseur qui n'en a peut-etre pas encore.
        """
        if provider == "anthropic":
            from app.services.ai.providers.anthropic_provider import AnthropicProvider

            return AnthropicProvider.default_model
        if provider == "openai":
            from app.services.ai.providers.openai_provider import OpenAIProvider

            return OpenAIProvider.default_model
        from app.services.ai.providers.mock_provider import MockProvider

        return MockProvider.default_model

    def _provider_state(self, provider: str, active: str) -> AIProviderState:
        try:
            stored_hint = self.settings_service.key_hint(provider)
        except AppError:
            # Cle de chiffrement du serveur changee. Laisser remonter
            # rendrait cet ecran inutilisable — or c'est le seul endroit ou
            # ressaisir la cle qu'il reclame. On le dit, et on continue.
            logger.warning(
                "clé de fournisseur illisible",
                extra={"event": "ai_key_unreadable", "provider": provider},
            )
            return AIProviderState(
                name=provider,  # type: ignore[arg-type]
                configured=False,
                key_hint=None,
                key_source="unreadable",
                default_model=self._default_model(provider),
                requires_key=provider in NEEDS_KEY,
            )

        if stored_hint:
            source = "database"
        elif provider == active and settings.ai_api_key:
            # `AI_API_KEY` n'appartient qu'au fournisseur actif : elle vient
            # d'un compte precis, et l'attribuer a l'autre serait faux.
            source = "environment"
            stored_hint = f"…{settings.ai_api_key[-4:]}"
        else:
            source = "none"

        return AIProviderState(
            name=provider,  # type: ignore[arg-type]
            configured=source != "none" or provider not in NEEDS_KEY,
            key_hint=stored_hint,
            key_source=source,  # type: ignore[arg-type]
            default_model=self._default_model(provider),
            requires_key=provider in NEEDS_KEY,
        )

    def read(self) -> AIConfigRead:
        # Par la session de la requete, et non par `effective_provider()`, qui
        # en ouvre une a lui. Le defaut corrige : juste apres un
        # enregistrement, cette autre session ne voit pas encore l'ecriture
        # non validee, et l'ecran renvoyait la valeur precedente — on
        # choisissait « anthropic » et « mock » s'affichait en retour.
        active = (
            self.settings_service.get(KEY_AI_PROVIDER) or settings.ai_provider
        ).lower()
        stored_model = self.settings_service.get(KEY_AI_MODEL)

        if stored_model:
            model_source = "database"
        elif settings.ai_model:
            model_source = "environment"
        elif self._default_model(active):
            model_source = "provider_default"
        else:
            model_source = "none"

        effective = stored_model or settings.ai_model or self._default_model(active)

        return AIConfigRead(
            active_provider=active,  # type: ignore[arg-type]
            effective_model=effective,
            configured_model=stored_model or "",
            model_source=model_source,  # type: ignore[arg-type]
            providers=[self._provider_state(name, active) for name in PROVIDERS],
        )

    # ------------------------------------------------------------------
    def update(self, payload: AIConfigUpdate, *, actor_id: str | None) -> AIConfigRead:
        changes: list[str] = []

        if payload.provider is not None:
            self.settings_service.set(
                KEY_AI_PROVIDER,
                payload.provider,
                description="Fournisseur d'IA choisi depuis l'administration.",
            )
            changes.append(f"fournisseur={payload.provider}")

        if payload.model is not None:
            self.settings_service.set(
                KEY_AI_MODEL,
                payload.model,
                description="Modèle visé, choisi depuis l'administration.",
            )
            changes.append(f"modèle={payload.model or '(défaut du fournisseur)'}")

        if payload.api_key is not None:
            target = payload.key_provider or payload.provider
            if target is None:
                raise AppError("ai.keyProviderRequired", code="ai_key_provider_required")
            if target not in NEEDS_KEY:
                raise AppError(
                    "ai.keyNotApplicable",
                    params={"provider": target},
                    code="ai_key_not_applicable",
                )
            self.settings_service.set(
                ai_key_setting(target),
                payload.api_key,
                secret=True,
                description=f"Clé API du fournisseur {target}.",
            )
            # Jamais la cle, ni son empreinte : une trace d'audit se conserve
            # longtemps et se lit largement.
            changes.append(
                f"clé {target} {'remplacée' if payload.api_key else 'supprimée'}"
            )

        if changes:
            self.db.add(
                AuditLog(
                    user_id=actor_id,
                    action="ai.config.updated",
                    entity_type="app_settings",
                    detail=", ".join(changes),
                )
            )
            logger.info(
                "configuration IA modifiée",
                extra={"event": "ai_config_updated", "changes": ", ".join(changes)},
            )

        self.db.flush()
        return self.read()

    # ------------------------------------------------------------------
    def test(self, *, actor_id: str | None) -> AIConfigTestResult:
        """Appel reel, court, declenche par un administrateur.

        Il est facture. C'est le but : rien d'autre ne distingue une cle
        valide d'une cle revoquee, d'un solde epuise ou d'un modele retire du
        catalogue — trois situations qui arrivent toutes en HTTP 400 et que
        l'on decouvrirait sinon au milieu d'une chaine de huit appels.
        """
        from app.prompts.base import RenderedPrompt
        from app.services.ai.service import AIService

        try:
            service = AIService()
        except AppError as exc:
            return AIConfigTestResult(
                ok=False,
                provider=effective_provider(),
                model="",
                detail=exc.detail,
            )

        prompt = RenderedPrompt(
            system_prompt="Tu réponds en un mot.",
            user_prompt=TEST_PROMPT,
            outline=[],
            context_json="{}",
            document_label="Test de configuration",
            prompt_name="admin_ai_test",
            prompt_version="1",
            max_output_tokens=TEST_MAX_TOKENS,
            temperature=0.0,
        )

        try:
            response = service.run(prompt)
        except AppError as exc:
            self._audit_test(actor_id, service.provider.name, service.model, ok=False)
            return AIConfigTestResult(
                ok=False,
                provider=service.provider.name,
                model=service.model,
                detail=exc.detail,
            )

        self._audit_test(actor_id, response.provider, response.model, ok=True)
        return AIConfigTestResult(
            ok=True,
            provider=response.provider,
            model=response.model,
            detail=response.text[:200],
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=response.latency_ms,
        )

    def _audit_test(
        self, actor_id: str | None, provider: str, model: str, *, ok: bool
    ) -> None:
        """Un essai dépense de l'argent : il laisse une trace, comme le reste."""
        self.db.add(
            AuditLog(
                user_id=actor_id,
                action="ai.config.tested",
                entity_type="app_settings",
                detail=f"{provider}/{model} — {'succès' if ok else 'échec'}",
            )
        )
