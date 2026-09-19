"""Contrat commun a tous les fournisseurs IA.

Aucune partie du code metier n'appelle un SDK de fournisseur directement :
tout passe par `AIProvider`, ce qui permet de changer de fournisseur via la
seule variable d'environnement AI_PROVIDER.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger("filmfund.ai")

#: Au-dela, on tronque : un message d'erreur n'est pas un journal.
MAX_UPSTREAM_REASON = 300


def upstream_reason(response: httpx.Response, provider: str) -> str:
    """Motif exact renvoye par le fournisseur, pour un statut >= 400.

    Anthropic et OpenAI partagent la meme forme (`{"error": {"message": ...}}`)
    et y mettent la seule information utile. La taire coute cher : un solde
    epuise, un modele retire du catalogue et un payload invalide arrivent tous
    en 400, et un message generique du type « verifiez la cle » envoie
    l'exploitant regenerer une cle parfaitement valide.

    L'identifiant de requete part au journal : c'est ce que le support du
    fournisseur demande, et il n'a rien a faire sous les yeux d'un utilisateur.
    """
    message = ""
    try:
        error = (response.json() or {}).get("error")
        if isinstance(error, dict):
            message = str(error.get("message") or "")
        elif isinstance(error, str):
            message = error
    except ValueError:
        # Corps non-JSON (passerelle, page d'erreur) : le texte brut vaut
        # mieux que rien, mais il peut etre volumineux.
        message = response.text.strip()

    request_id = response.headers.get("request-id") or response.headers.get("x-request-id")
    logger.error(
        "appel IA refusé",
        extra={
            "event": "ai_provider_error",
            "provider": provider,
            "status": response.status_code,
            "request_id": request_id or "",
            "upstream_message": message[:MAX_UPSTREAM_REASON],
        },
    )

    if not message:
        return "aucun motif renvoyé par le fournisseur"
    if len(message) > MAX_UPSTREAM_REASON:
        return message[:MAX_UPSTREAM_REASON].rstrip() + "…"
    return message


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

    #: Modele utilise quand `AI_MODEL` n'est pas renseigne.
    #:
    #: Il appartient au fournisseur, pas a la configuration : un seul reglage
    #: partage enverrait le modele de l'un a l'autre. Vide signifie qu'aucun
    #: defaut n'est raisonnable et que `AI_MODEL` devient obligatoire — mieux
    #: vaut refuser de demarrer que deviner un nom de modele.
    default_model: str = ""

    @abstractmethod
    def complete(self, request: AICompletionRequest) -> AICompletionResponse:
        """Retourne une completion ou leve `AIProviderError`."""

    def healthcheck(self) -> bool:
        return True
