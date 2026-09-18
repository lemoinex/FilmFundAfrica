"""Fournisseur OpenAI (Chat Completions), appele via httpx."""

from __future__ import annotations

import time

import httpx

from app.core.config import settings
from app.core.errors import AIProviderError
from app.services.ai.base import AICompletionRequest, AICompletionResponse, AIProvider

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, timeout: int | None = None) -> None:
        self.api_key = api_key or settings.ai_api_key
        self.timeout = timeout or settings.ai_timeout_seconds
        if not self.api_key:
            raise AIProviderError(
                "AI_API_KEY est requis lorsque AI_PROVIDER=openai.",
                code="ai_provider_not_configured",
            )

    def complete(self, request: AICompletionRequest) -> AICompletionResponse:
        payload = {
            "model": request.model,
            "max_completion_tokens": request.max_output_tokens,
            "temperature": request.temperature,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }

        started = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(OPENAI_API_URL, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise AIProviderError(f"Fournisseur IA injoignable : {exc}") from exc
        latency_ms = int((time.perf_counter() - started) * 1000)

        if response.status_code >= 400:
            raise AIProviderError(
                f"Erreur du fournisseur IA ({response.status_code}). "
                "Vérifiez la clé API et le modèle configuré."
            )

        data = response.json()
        choices = data.get("choices") or []
        text = choices[0].get("message", {}).get("content", "") if choices else ""
        if not text.strip():
            raise AIProviderError("Le fournisseur IA a renvoyé une réponse vide.")

        usage = data.get("usage") or {}
        return AICompletionResponse(
            text=text.strip(),
            model=data.get("model", request.model),
            provider=self.name,
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            latency_ms=latency_ms,
            stop_reason=choices[0].get("finish_reason") if choices else None,
        )
