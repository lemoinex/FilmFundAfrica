"""Contrat commun a tous les fournisseurs IA.

Aucune partie du code metier n'appelle un SDK de fournisseur directement :
tout passe par `AIProvider`, ce qui permet de changer de fournisseur via la
seule variable d'environnement AI_PROVIDER.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(slots=True)
class AICompletionRequest:
    system_prompt: str
    user_prompt: str
    model: str
    max_output_tokens: int = 4000
    temperature: float = 0.7
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class AICompletionResponse:
    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    stop_reason: str | None = None


class AIProvider(ABC):
    """Interface minimale d'un fournisseur de generation de texte."""

    name: str = "abstract"

    @abstractmethod
    def complete(self, request: AICompletionRequest) -> AICompletionResponse:
        """Retourne une completion ou leve `AIProviderError`."""

    def healthcheck(self) -> bool:
        return True
