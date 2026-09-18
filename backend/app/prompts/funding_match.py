"""Prompt : explication d'un rapprochement projet / financement (Phase 3).

Le prompt est defini des maintenant pour que le module Funding Intelligence
s'y branche sans reecriture. Le score de compatibilite est calcule par des
regles deterministes ; l'IA n'est utilisee que pour expliquer le rapprochement
a partir des donnees fournies.
"""

from __future__ import annotations

import json
from typing import Any

from app.prompts.base import (
    BASE_SYSTEM_PROMPT,
    MISSING_SECTION_MARKER,
    MISSING_VALUE_RULE,
    PromptContext,
    RenderedPrompt,
)

PROMPT_NAME = "funding_match_explanation"
PROMPT_VERSION = "1.0.0"

MISSION = """Explique à l'auteur pourquoi ce dispositif de financement correspond — ou \
non — à son projet, en te fondant EXCLUSIVEMENT sur les données de l'opportunité \
fournies ci-dessous."""

OUTLINE = [
    "Pourquoi ce dispositif correspond",
    "Conditions remplies",
    "Conditions manquantes ou à vérifier",
    "Documents à préparer",
    "Ce qu'il reste à faire avant de candidater",
]

DISCLAIMER = (
    "Le score de compatibilité est un indicateur d'aide à la décision : il ne garantit "
    "en aucun cas l'obtention d'un financement. Les conditions officielles font foi et "
    "doivent être vérifiées sur le site de l'organisme."
)


def build_funding_match_prompt(
    context: PromptContext,
    opportunity: dict[str, Any],
    computed_score: int,
    *,
    language: str = "français",
) -> RenderedPrompt:
    system_prompt = BASE_SYSTEM_PROMPT.format(
        missing_rule=MISSING_VALUE_RULE,
        language=language,
        missing_marker=MISSING_SECTION_MARKER.replace("## ", ""),
    )
    sections = "\n".join(f"{index}. {item}" for index, item in enumerate(OUTLINE, 1))
    opportunity_block = "\n".join(
        f"{key} : {value}" for key, value in opportunity.items() if value not in (None, "")
    )
    blocks = [
        f"MISSION\n=======\n{MISSION}",
        "",
        context.render_block(),
        "",
        "OPPORTUNITÉ DE FINANCEMENT (données vérifiées en base)",
        "=====================================================",
        opportunity_block,
        "",
        f"Score de compatibilité calculé par la plateforme : {computed_score}/100.",
        "",
        f"STRUCTURE OBLIGATOIRE\n=====================\n{sections}",
        "",
        "INTERDICTIONS ABSOLUES",
        "======================",
        "- N'invente aucune condition d'éligibilité, date limite, montant ni pièce à fournir.",
        "- N'affirme jamais que le projet sera financé ni qu'il a « de bonnes chances ».",
        "- Si une donnée manque dans la fiche, écris « Information non fournie. » et "
        "renvoie l'utilisateur vers le site officiel du dispositif.",
        "",
        "FORMAT DE SORTIE",
        "================",
        "- Markdown, un titre `##` par section, puces courtes.",
        f"- Reprends en dernière ligne, en italique : {DISCLAIMER}",
    ]
    return RenderedPrompt(
        system_prompt=system_prompt,
        user_prompt="\n".join(blocks),
        outline=list(OUTLINE),
        prompt_name=PROMPT_NAME,
        prompt_version=PROMPT_VERSION,
        document_label="Analyse de compatibilité",
        max_output_tokens=3000,
        temperature=0.3,
        context_json=json.dumps(context.to_dict(), ensure_ascii=False),
    )
