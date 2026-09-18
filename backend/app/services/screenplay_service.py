"""Génération de scénario long en plusieurs passes.

Un long métrage de 90 à 120 pages représente 17 000 à 23 000 mots : aucun
fournisseur ne produit cela en un seul appel. Le scénario est donc écrit par
segments successifs (actes, puis blocs de séquences), chaque passe recevant
la fin du segment précédent pour garantir la continuité des personnages, des
lieux et de la numérotation des séquences.

Le découpage suit la structure dramatique, pas un simple quota de mots :
c'est la densité de séquences qui produit la longueur, jamais l'étirement.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from app.prompts.base import (
    SCREENPLAY_WORDS_PER_PAGE,
    PromptContext,
    PromptTemplate,
    RenderedPrompt,
)

#: Proportion de pages par acte dans une structure en trois actes.
ACT_RATIOS: tuple[tuple[str, float], ...] = (
    ("Acte I — exposition, présentation du monde et élément déclencheur", 0.25),
    ("Acte II — confrontation, complications et point de bascule central", 0.50),
    ("Acte III — crise, climax et résolution", 0.25),
)

MAX_PASSES = 10
#: Plafond de sortie demandé par passe, avant bornage par `AI_MAX_OUTPUT_TOKENS`.
SCREENPLAY_MAX_TOKENS_PER_CALL = 32000
#: Marge de sécurité : on ne demande jamais à un fournisseur sa limite exacte.
TOKEN_SAFETY_RATIO = 0.9
#: Nombre de caractères de contexte de continuité repris d'une passe à l'autre.
CONTINUITY_TAIL_CHARS = 3500


@dataclass(slots=True)
class ScreenplaySegment:
    index: int
    total: int
    label: str
    pages: int
    words: int
    max_output_tokens: int


def pages_per_pass(max_tokens_per_call: int) -> int:
    """Nombre de pages qu'une seule passe peut réellement produire."""
    words_per_call = max(int(max_tokens_per_call * TOKEN_SAFETY_RATIO / 2.2), 400)
    return max(int(words_per_call / SCREENPLAY_WORDS_PER_PAGE), 3)


def _split_blocks(total_pages: int, per_pass: int) -> list[tuple[str, int]]:
    """Répartit les pages par acte, en subdivisant tout acte plus long qu'une passe."""
    blocks: list[tuple[str, int]] = []
    for label, ratio in ACT_RATIOS:
        act_pages = max(int(round(total_pages * ratio)), 3)
        parts = math.ceil(act_pages / per_pass)
        if parts <= 1:
            blocks.append((label, act_pages))
            continue
        # Réparti au plus juste : aucun morceau ne dépasse `per_pass`.
        base, remainder = divmod(act_pages, parts)
        for part in range(parts):
            blocks.append((f"{label} — partie {part + 1}/{parts}", base + (1 if part < remainder else 0)))
    return blocks


def max_supported_minutes(max_tokens_per_call: int) -> int:
    """Durée maximale dont le découpage tient en `MAX_PASSES` appels.

    Calculée à partir du découpage réel — la répartition par acte introduit des
    arrondis, si bien qu'une simple multiplication surestimerait la limite.
    """
    per_pass = pages_per_pass(max_tokens_per_call)
    minutes = per_pass
    while len(_split_blocks(minutes + 1, per_pass)) <= MAX_PASSES:
        minutes += 1
    return minutes


def plan_segments(target_minutes: int, max_tokens_per_call: int) -> list[ScreenplaySegment]:
    """Découpe le scénario en passes compatibles avec la limite du fournisseur.

    Chaque segment produit reste sous le plafond de sortie d'un appel : aucun
    segment n'est jamais plus long que ce qu'une passe peut réellement écrire,
    faute de quoi l'utilisateur paierait des crédits pour un scénario tronqué.

    Lève `AppError` si la durée demandée dépasse ce que `MAX_PASSES` appels
    permettent de couvrir, plutôt que de renvoyer un plan irréalisable.
    """
    total_pages = max(target_minutes, 1)
    per_pass = pages_per_pass(max_tokens_per_call)

    if total_pages <= per_pass:
        return [
            ScreenplaySegment(
                index=1,
                total=1,
                label="Scénario complet (trois actes)",
                pages=total_pages,
                words=total_pages * SCREENPLAY_WORDS_PER_PAGE,
                max_output_tokens=max_tokens_per_call,
            )
        ]

    raw_blocks = _split_blocks(total_pages, per_pass)

    if len(raw_blocks) > MAX_PASSES:
        from app.core.errors import AppError

        raise AppError(
            f"Durée trop longue pour une génération en une fois : {target_minutes} minutes "
            f"demanderaient {len(raw_blocks)} passes, au-delà de la limite de {MAX_PASSES}. "
            f"Maximum réalisable avec la configuration actuelle : "
            f"{max_supported_minutes(max_tokens_per_call)} minutes.",
            code="screenplay_too_long",
        )

    total = len(raw_blocks)
    return [
        ScreenplaySegment(
            index=index,
            total=total,
            label=label,
            pages=pages,
            words=pages * SCREENPLAY_WORDS_PER_PAGE,
            max_output_tokens=max_tokens_per_call,
        )
        for index, (label, pages) in enumerate(raw_blocks, 1)
    ]


def last_scene_number(text: str) -> int:
    """Dernier numéro de séquence rencontré, pour poursuivre la numérotation."""
    numbers = re.findall(r"^\s*(\d{1,3})[.)\s]+(?:INT|EXT)", text, flags=re.MULTILINE)
    return int(numbers[-1]) if numbers else 0


def build_segment_prompt(
    template: PromptTemplate,
    context: PromptContext,
    segment: ScreenplaySegment,
    *,
    language: str,
    target_minutes: int,
    previous_text: str,
    user_instructions: str | None,
) -> RenderedPrompt:
    """Construit le prompt d'une passe, avec son contexte de continuité."""
    instructions: list[str] = [
        f"Tu écris UNIQUEMENT le segment {segment.index}/{segment.total} du scénario : "
        f"{segment.label}.",
        f"Ce segment fait environ {segment.pages} pages, soit environ {segment.words} mots.",
        f"Le scénario complet vise {target_minutes} pages pour {target_minutes} minutes : "
        "dimensionne l'action de ce segment en conséquence.",
    ]

    if segment.index == 1:
        instructions.append(
            "Commence par la page de titre, puis la première séquence numérotée 1."
        )
    else:
        next_scene = last_scene_number(previous_text) + 1
        instructions.extend(
            [
                "N'écris NI page de titre, NI rappel de ce qui précède, NI résumé : "
                "enchaîne directement sur la séquence suivante.",
                f"La numérotation des séquences reprend à {next_scene}.",
                "Respecte scrupuleusement les noms, lieux, relations et registres de "
                "langage déjà établis dans les pages précédentes.",
            ]
        )

    if segment.index == segment.total:
        instructions.append(
            "Ce segment referme le récit : il contient le climax et la résolution, "
            "et se termine par la mention FIN."
        )
    else:
        instructions.append(
            "Ce segment ne conclut pas le récit : il se termine sur une tension ouverte."
        )

    if user_instructions:
        instructions.append(user_instructions.strip())

    if previous_text:
        tail = previous_text.strip()[-CONTINUITY_TAIL_CHARS:]
        instructions.extend(
            [
                "",
                "FIN DU SEGMENT PRÉCÉDENT (pour la continuité, à ne pas réécrire)",
                "---------------------------------------------------------------",
                tail,
            ]
        )

    prompt = template.render(
        context,
        language=language,
        target_duration=target_minutes,
        additional_instructions="\n".join(instructions),
    )
    prompt.max_output_tokens = segment.max_output_tokens
    return prompt


def assemble(parts: list[str]) -> str:
    """Concatène les segments en retirant les en-têtes Markdown redondants."""
    cleaned: list[str] = []
    for index, part in enumerate(parts):
        text = part.strip()
        if index > 0:
            # Supprime une éventuelle page de titre répétée en tête de segment.
            text = re.sub(r"^#\s+[^\n]+\n+", "", text)
        cleaned.append(text)
    return "\n\n".join(cleaned).strip()
