"""Fournisseur OpenAI (Chat Completions), appele via httpx."""

from __future__ import annotations

import time

import httpx

from app.core.config import settings
from app.core.errors import AIProviderError
from app.services.ai.base import (
    AICompletionRequest,
    AICompletionResponse,
    AIProvider,
    upstream_reason,
)

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(AIProvider):
    name = "openai"
    #: Volontairement vide : choisir un modele OpenAI a la place de
    #: l'exploitant reviendrait a deviner. `AI_MODEL` est donc requis.
    default_model = ""

    def __init__(self, api_key: str | None = None, timeout: int | None = None) -> None:
        from app.services.ai.credentials import api_key_for

        self.api_key = api_key or api_key_for(self.name)
        self.timeout = timeout or settings.ai_timeout_seconds
        if not self.api_key:
            raise AIProviderError(
                "ai.keyRequired",
                params={"provider": "openai"},
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
            raise AIProviderError("ai.unreachable", params={"reason": str(exc)}) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)

        if response.status_code >= 400:
            raise AIProviderError(
                "ai.providerError",
                params={
                    "status": response.status_code,
                    "reason": upstream_reason(response, self.name),
                },
            )

        data = response.json()
        choices = data.get("choices") or []
        text = choices[0].get("message", {}).get("content", "") if choices else ""
        if not text.strip():
            raise AIProviderError("ai.emptyResponse")

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
