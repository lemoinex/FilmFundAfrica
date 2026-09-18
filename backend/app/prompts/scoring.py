"""Prompt : analyse qualitative du dossier (module IA d'amelioration).

Le score chiffre est calcule de maniere deterministe par
`app.services.scoring_service` ; ce prompt produit l'analyse qualitative qui
l'accompagne (forces, faiblesses, coherence entre documents).
"""

from __future__ import annotations

import json

from app.prompts.base import (
    BASE_SYSTEM_PROMPT,
    MISSING_SECTION_MARKER,
    MISSING_VALUE_RULE,
    PromptContext,
    RenderedPrompt,
)

PROMPT_NAME = "project_analysis"
PROMPT_VERSION = "1.0.0"

MISSION = """Analyse ce dossier de projet audiovisuel comme le ferait un lecteur de \
comité de fonds d'aide. Tu évalues la solidité du dossier tel qu'il est écrit, \
sans reformuler les documents et sans réécrire le projet."""

OUTLINE = [
    "Cohérence globale du projet",
    "Qualité du synopsis",
    "Forces du dossier",
    "Faiblesses du dossier",
    "Cohérence entre les documents",
    "Adéquation aux attentes des financeurs",
    "Potentiel de financement et principaux risques",
    "Trois actions prioritaires",
]


def build_analysis_prompt(
    context: PromptContext,
    *,
    language: str = "français",
    deterministic_score: int | None = None,
) -> RenderedPrompt:
    system_prompt = BASE_SYSTEM_PROMPT.format(
        missing_rule=MISSING_VALUE_RULE,
        language=language,
        missing_marker=MISSING_SECTION_MARKER.replace("## ", ""),
    )
    sections = "\n".join(f"{index}. {item}" for index, item in enumerate(OUTLINE, 1))
    score_block = (
        f"\nLe score d'avancement calculé par la plateforme est de {deterministic_score}/100. "
        "Commente-le, ne le recalcule pas et ne le contredis pas sans justification factuelle."
        if deterministic_score is not None
        else ""
    )
    blocks = [
        f"MISSION\n=======\n{MISSION}{score_block}",
        "",
        context.render_block(),
        "",
        f"STRUCTURE OBLIGATOIRE\n=====================\n{sections}",
        "",
        "EXIGENCES",
        "=========",
        "- Sois précis et actionnable : chaque faiblesse est suivie de ce qu'il faut écrire.",
        "- Ne promets jamais un financement et ne donne aucune probabilité chiffrée de succès.",
        "- Si un document est absent du contexte, dis-le au lieu d'en supposer le contenu.",
        "",
        "FORMAT DE SORTIE",
        "================",
        "- Markdown, un titre `##` par section.",
        f"- Termine par la section `{MISSION and MISSING_SECTION_MARKER}`.",
    ]
    return RenderedPrompt(
        system_prompt=system_prompt,
        user_prompt="\n".join(blocks),
        outline=list(OUTLINE),
        prompt_name=PROMPT_NAME,
        prompt_version=PROMPT_VERSION,
        document_label="Analyse du dossier",
        max_output_tokens=6000,
        temperature=0.4,
        context_json=json.dumps(context.to_dict(), ensure_ascii=False),
    )
