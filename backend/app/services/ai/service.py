"""Service IA : point d'entree unique pour toute generation de texte.

    AIService
       |
    AIProvider
       |-- AnthropicProvider
       |-- OpenAIProvider
       `-- MockProvider

Le fournisseur est choisi par la variable d'environnement AI_PROVIDER.
Le reste du code ne connait que `AIService`.
"""

from __future__ import annotations

import logging
import re

from app.core.config import settings
from app.core.errors import AIProviderError
from app.prompts.base import MISSING_SECTION_MARKER, RenderedPrompt
from app.services.ai.base import AICompletionRequest, AICompletionResponse, AIProvider
from app.services.ai.providers.mock_provider import MockProvider

logger = logging.getLogger("filmfund.ai")


def build_provider(provider_name: str | None = None) -> AIProvider:
    name = (provider_name or settings.ai_provider).lower()
    if name == "anthropic":
        from app.services.ai.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider()
    if name == "openai":
        from app.services.ai.providers.openai_provider import OpenAIProvider

        return OpenAIProvider()
    if name == "mock":
        return MockProvider()
    raise AIProviderError(
        "ai.providerUnknown", params={"name": name}, code="ai_provider_unknown"
    )


class AIService:
    """Orchestre prompt -> fournisseur -> texte nettoye."""

    def __init__(self, provider: AIProvider | None = None, model: str | None = None) -> None:
        self.provider = provider or build_provider()
        self.model = model or settings.ai_model

    # ------------------------------------------------------------------
    @staticmethod
    def effective_max_output_tokens(requested: int) -> int:
        """Plafond réellement applicable à un appel, bornes de configuration comprises."""
        if settings.ai_max_output_tokens:
            return min(requested, settings.ai_max_output_tokens)
        return requested

    # ------------------------------------------------------------------
    def run(self, prompt: RenderedPrompt) -> AICompletionResponse:
        request = AICompletionRequest(
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.user_prompt,
            model=self.model,
            max_output_tokens=self.effective_max_output_tokens(prompt.max_output_tokens),
            temperature=prompt.temperature,
            metadata={
                "outline": "\n".join(prompt.outline),
                "context_json": prompt.context_json,
                "document_label": prompt.document_label,
                "prompt_name": prompt.prompt_name,
                "prompt_version": prompt.prompt_version,
                **prompt.metadata_extra,
            },
        )
        logger.info(
            "génération IA",
            extra={
                "event": "ai_generate",
                "prompt_name": prompt.prompt_name,
                "prompt_version": prompt.prompt_version,
            },
        )
        response = self.provider.complete(request)
        response.text = self._clean(response.text)
        return response

    # ------------------------------------------------------------------
    @staticmethod
    def _clean(text: str) -> str:
        """Retire les bavardages de preambule et les blocs de code parasites."""
        cleaned = text.strip()
        fence = re.match(r"^```(?:markdown|md)?\n(.*)\n```$", cleaned, flags=re.DOTALL)
        if fence:
            cleaned = fence.group(1).strip()
        cleaned = re.sub(
            r"^(bien sûr|voici|avec plaisir)[^\n]*\n+",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        return cleaned.strip()

    @staticmethod
    def extract_missing_information(text: str) -> list[str]:
        """Recupere les puces de la section « Informations à compléter »."""
        marker = MISSING_SECTION_MARKER.replace("## ", "")
        pattern = re.compile(
            rf"^#{{1,4}}\s*{re.escape(marker)}\s*$(.*?)(?=^#{{1,4}}\s|\Z)",
            flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
        )
        match = pattern.search(text)
        if not match:
            return []
        items: list[str] = []
        for line in match.group(1).splitlines():
            stripped = line.strip()
            if stripped.startswith(("-", "*", "•")):
                item = stripped.lstrip("-*• ").strip()
                if item and "aucune information manquante" not in item.lower():
                    items.append(item)
        return items


def word_count(text: str) -> int:
    return len([token for token in re.split(r"\s+", text.strip()) if token])
