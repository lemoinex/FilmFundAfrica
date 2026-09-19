"""Fournisseur Anthropic (API Messages), appele via httpx.

On evite une dependance SDK supplementaire : l'API REST suffit et reste
stable. La cle provient exclusivement de AI_API_KEY.

**Les parametres envoyes dependent du modele.** L'API a change : les modeles
actuels refusent `temperature` avec une 400, et acceptent en echange une
profondeur de reflexion (`thinking`) et un niveau d'effort. Envoyer les
mauvais parametres ne degrade pas la reponse, il n'y en a pas : la requete est
rejetee. D'ou la table de capacites ci-dessous, et un principe simple pour ce
qu'elle ne couvre pas — **ne rien envoyer d'optionnel**. Un parametre omis
prend sa valeur par defaut cote serveur ; un parametre de trop fait echouer
l'appel.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.errors import AIProviderError
from app.services.ai.base import AICompletionRequest, AICompletionResponse, AIProvider

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    """Ce qu'un modele accepte, et donc ce qu'on a le droit de lui envoyer."""

    #: `thinking: {"type": "adaptive"}` — le modele decide de sa profondeur.
    adaptive_thinking: bool = False
    #: `output_config: {"effort": ...}`.
    effort: bool = False
    #: `temperature` et consorts. Retires des modeles actuels.
    sampling: bool = False


#: Prefixes de modeles dont on connait les capacites.
#:
#: L'ordre compte : le premier prefixe qui correspond gagne, donc les entrees
#: les plus specifiques d'abord.
MODEL_CAPABILITIES: tuple[tuple[str, ModelCapabilities], ...] = (
    # Generation actuelle : reflexion adaptative et effort, pas d'echantillonnage.
    ("claude-opus-5", ModelCapabilities(adaptive_thinking=True, effort=True)),
    ("claude-sonnet-5", ModelCapabilities(adaptive_thinking=True, effort=True)),
    ("claude-opus-4-8", ModelCapabilities(adaptive_thinking=True, effort=True)),
    ("claude-opus-4-7", ModelCapabilities(adaptive_thinking=True, effort=True)),
    # 4.6 : periode de transition, les deux sont acceptes.
    (
        "claude-opus-4-6",
        ModelCapabilities(adaptive_thinking=True, effort=True, sampling=True),
    ),
    (
        "claude-sonnet-4-6",
        ModelCapabilities(adaptive_thinking=True, effort=True, sampling=True),
    ),
    # Generations anterieures : echantillonnage uniquement.
    ("claude-haiku-4-5", ModelCapabilities(sampling=True)),
    ("claude-sonnet-4-5", ModelCapabilities(sampling=True)),
    ("claude-opus-4-5", ModelCapabilities(sampling=True)),
    ("claude-3", ModelCapabilities(sampling=True)),
)

#: Modele inconnu : on n'envoie rien d'optionnel.
#:
#: Un parametre omis vaut son defaut serveur et fonctionne partout ; un
#: parametre de trop fait echouer l'appel. Devant l'incertitude, se taire est
#: la seule option qui ne casse rien.
UNKNOWN_MODEL = ModelCapabilities()


def capabilities_for(model: str) -> ModelCapabilities:
    for prefix, capabilities in MODEL_CAPABILITIES:
        if model.startswith(prefix):
            return capabilities
    return UNKNOWN_MODEL


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None, timeout: int | None = None) -> None:
        self.api_key = api_key or settings.ai_api_key
        self.timeout = timeout or settings.ai_timeout_seconds
        if not self.api_key:
            raise AIProviderError(
                "ai.keyRequired",
                params={"provider": "anthropic"},
                code="ai_provider_not_configured",
            )

    # ------------------------------------------------------------------
    def build_payload(self, request: AICompletionRequest) -> dict:
        """Corps de la requete, ajuste aux capacites du modele vise."""
        capabilities = capabilities_for(request.model)
        payload: dict = {
            "model": request.model,
            "max_tokens": request.max_output_tokens,
            "system": request.system_prompt,
            "messages": [{"role": "user", "content": request.user_prompt}],
        }

        if capabilities.adaptive_thinking:
            payload["thinking"] = {"type": "adaptive"}
        if capabilities.effort and settings.ai_effort:
            payload["output_config"] = {"effort": settings.ai_effort}
        if capabilities.sampling:
            payload["temperature"] = request.temperature

        return payload

    # ------------------------------------------------------------------
    def complete(self, request: AICompletionRequest) -> AICompletionResponse:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        started = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    ANTHROPIC_API_URL, json=self.build_payload(request), headers=headers
                )
        except httpx.HTTPError as exc:
            raise AIProviderError("ai.unreachable", params={"reason": str(exc)}) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)

        if response.status_code >= 400:
            raise AIProviderError(
                "ai.providerError", params={"status": response.status_code}
            )

        data = response.json()

        # Un refus n'est pas une erreur HTTP : la reponse arrive en 200, sans
        # contenu exploitable. Le laisser passer produirait une etape vide que
        # l'on prendrait pour une reponse du modele.
        if data.get("stop_reason") == "refusal":
            details = data.get("stop_details") or {}
            raise AIProviderError(
                "ai.refused",
                params={"reason": details.get("category") or "non précisée"},
                code="ai_refused",
            )

        blocks = data.get("content") or []
        text = "".join(block.get("text", "") for block in blocks if block.get("type") == "text")
        if not text.strip():
            raise AIProviderError("ai.emptyResponse")

        usage = data.get("usage") or {}
        return AICompletionResponse(
            text=text.strip(),
            model=data.get("model", request.model),
            provider=self.name,
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            latency_ms=latency_ms,
            stop_reason=data.get("stop_reason"),
        )
