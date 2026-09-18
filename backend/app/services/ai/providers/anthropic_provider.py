"""Fournisseur Anthropic (API Messages), appele via httpx.

On evite une dependance SDK supplementaire : l'API REST suffit et reste
stable. La cle provient exclusivement de AI_API_KEY.
"""

from __future__ import annotations

import time

import httpx

from app.core.config import settings
from app.core.errors import AIProviderError
from app.services.ai.base import AICompletionRequest, AICompletionResponse, AIProvider

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None, timeout: int | None = None) -> None:
        self.api_key = api_key or settings.ai_api_key
        self.timeout = timeout or settings.ai_timeout_seconds
        if not self.api_key:
            raise AIProviderError(
                "AI_API_KEY est requis lorsque AI_PROVIDER=anthropic.",
                code="ai_provider_not_configured",
            )

    def complete(self, request: AICompletionRequest) -> AICompletionResponse:
        payload = {
            "model": request.model,
            "max_tokens": request.max_output_tokens,
            "temperature": request.temperature,
            "system": request.system_prompt,
            "messages": [{"role": "user", "content": request.user_prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        started = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise AIProviderError(f"Fournisseur IA injoignable : {exc}") from exc
        latency_ms = int((time.perf_counter() - started) * 1000)

        if response.status_code >= 400:
            raise AIProviderError(
                f"Erreur du fournisseur IA ({response.status_code}). "
                "Vérifiez la clé API et le modèle configuré."
            )

        data = response.json()
        blocks = data.get("content") or []
        text = "".join(block.get("text", "") for block in blocks if block.get("type") == "text")
        if not text.strip():
            raise AIProviderError("Le fournisseur IA a renvoyé une réponse vide.")

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
