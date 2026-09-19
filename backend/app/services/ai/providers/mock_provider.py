"""Fournisseur de secours deterministe, sans appel reseau.

Objectif : permettre de lancer, tester et demontrer l'application sans cle API.
Il ne remplace pas une vraie generation. Le document produit reprend
strictement les donnees saisies par l'utilisateur, affiche la structure
professionnelle attendue et marque explicitement chaque information absente
par « Information non fournie. » — conformement a la regle qui interdit a
l'IA d'inventer personnages, evenements ou financements.
"""

from __future__ import annotations

import json
import time

from app.services.ai.base import AICompletionRequest, AICompletionResponse, AIProvider

BANNER = (
    "> **CONTENU NON GÉNÉRÉ PAR UNE IA — MODE `mock`.**\n"
    "> Aucun fournisseur d'IA n'est configuré (`AI_PROVIDER=mock`). Ce document reprend "
    "uniquement les informations que vous avez saisies et la structure attendue. "
    "Renseignez `AI_PROVIDER` et `AI_API_KEY` pour obtenir une rédaction complète.\n"
)

MISSING = "Information non fournie."


class MockProvider(AIProvider):
    name = "mock"
    default_model = "mock-deterministic"

    def complete(self, request: AICompletionRequest) -> AICompletionResponse:
        started = time.perf_counter()

        if request.metadata.get("response_format") == "agent_json":
            return self._agent_output(request, started)

        outline = [
            line for line in request.metadata.get("outline", "").split("\n") if line.strip()
        ]
        try:
            context = json.loads(request.metadata.get("context_json", "{}"))
        except json.JSONDecodeError:
            context = {}

        # `PromptContext.to_dict()` indexe par libelle affichable (« Titre »),
        # pas par nom d'attribut : chercher "title" renvoyait toujours le repli,
        # et tout document produit en mode `mock` s'intitulait « sans titre ».
        title = context.get("Titre") or context.get("title") or "Projet sans titre"
        document_label = request.metadata.get("document_label", "Document")

        parts: list[str] = [f"# {document_label} — {title}", "", BANNER, ""]

        known = {
            key: value
            for key, value in context.items()
            if isinstance(value, str) and value.strip()
        }
        if known:
            parts.append("## Données du projet")
            parts.append("")
            for key, value in known.items():
                parts.append(f"- **{key}** : {value}")
            parts.append("")

        characters = context.get("characters") or []
        if characters:
            parts.append("## Personnages saisis")
            parts.append("")
            for character in characters:
                name = character.get("name", MISSING)
                role = character.get("role") or MISSING
                description = character.get("description") or MISSING
                parts.append(f"- **{name}** ({role}) — {description}")
            parts.append("")

        if outline:
            parts.append("## Structure attendue")
            parts.append("")
            for heading in outline:
                parts.append(f"### {heading.strip().lstrip('-').strip()}")
                parts.append("")
                parts.append(MISSING)
                parts.append("")

        text = "\n".join(parts).strip()
        latency_ms = int((time.perf_counter() - started) * 1000)

        return AICompletionResponse(
            text=text,
            model="mock-deterministic",
            provider=self.name,
            input_tokens=len(request.user_prompt) // 4,
            output_tokens=len(text) // 4,
            latency_ms=latency_ms,
            stop_reason="end_turn",
        )

    # ------------------------------------------------------------------
    def _agent_output(
        self, request: AICompletionRequest, started: float
    ) -> AICompletionResponse:
        """Sortie d'agent en mode `mock` : structurellement valide, jamais probante.

        Le mode `mock` doit permettre de traverser la chaine sans cle API. Il ne
        doit pas permettre d'en sortir un dossier presente comme controle : sans
        modele, rien n'a ete analyse. Le constat rendu est donc `MAJOR`, ce qui
        interdit l'export tout en laissant l'orchestrateur derouler et la boucle
        de correction s'exercer.
        """
        role = request.metadata.get("agent_role", "UNKNOWN")
        outline = [
            line.strip() for line in request.metadata.get("outline", "").split("\n") if line.strip()
        ]
        sections: list[str] = []
        for heading in outline:
            sections.append(f"## {heading}")
            sections.append(MISSING)
        analysis = "\n\n".join(sections) if sections else MISSING

        payload = {
            "analysis": analysis,
            "rationale": (
                "Aucun fournisseur d'IA n'est configuré (`AI_PROVIDER=mock`) : "
                "aucune analyse n'a été produite."
            ),
            "decisions": [],
            "modifications": {
                "preserved": [],
                "modified": [],
                "removed": [],
                "added": [],
                "reasoning": [],
            },
            "findings": [
                {
                    "severity": "MAJOR",
                    "element": "fournisseur d'IA",
                    "description": (
                        "Sortie produite en mode `mock` : le dossier n'a été ni rédigé "
                        "ni contrôlé. Renseignez `AI_PROVIDER` et `AI_API_KEY`."
                    ),
                    "owner": role,
                    "suggested_correction": "Configurer un fournisseur d'IA réel.",
                }
            ],
            "verdict": "REQUIRES_CORRECTION",
            "state_patch": None,
            "next_agent_instructions": (
                "Sortie `mock` : ne t'appuie sur aucun de ses contenus."
            ),
        }

        text = json.dumps(payload, ensure_ascii=False)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return AICompletionResponse(
            text=text,
            model="mock-deterministic",
            provider=self.name,
            input_tokens=len(request.user_prompt) // 4,
            output_tokens=len(text) // 4,
            latency_ms=latency_ms,
            stop_reason="end_turn",
        )
