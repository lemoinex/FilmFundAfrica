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
from collections import Counter
from dataclasses import dataclass, field

from app.core.config import settings
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

#: Plafond de securite du nombre de passes, surchargeable par
#: `SCREENPLAY_MAX_PASSES`. Ce n'est pas une limite d'usage : le nombre de
#: passes suit la duree demandee. Il existe pour qu'une saisie aberrante ne
#: lance pas cent appels au fournisseur.
DEFAULT_MAX_PASSES = 40
#: Plafond de sortie demandé par passe, avant bornage par `AI_MAX_OUTPUT_TOKENS`.
SCREENPLAY_MAX_TOKENS_PER_CALL = 32000
#: Marge de sécurité : on ne demande jamais à un fournisseur sa limite exacte.
TOKEN_SAFETY_RATIO = 0.9
#: Nombre de caractères de contexte de continuité repris d'une passe à l'autre.
CONTINUITY_TAIL_CHARS = 3500
#: Personnages et lieux retenus dans l'etat de continuite. Bornes pour que le
#: contexte n'enfle pas passe apres passe au detriment du texte a ecrire.
MAX_TRACKED_CHARACTERS = 25
MAX_TRACKED_LOCATIONS = 20
#: Segments recents rappeles nominativement. Les rappeler tous ferait croitre
#: le bloc a chaque passe, sans rien apprendre de plus : la position dans
#: l'arc est deja donnee par le libelle du segment en cours.
MAX_RECENT_SEGMENTS = 3

#: En-tete de sequence : « 12. INT. MAISON DE FATOU - NUIT ».
SCENE_HEADING_RE = re.compile(
    r"^\s*(?:\d{1,3}[.)]\s*)?(?:INT|EXT)[./\s]*(?:INT|EXT)?\.?\s+(.+?)\s+[-–—]\s+.+$",
    flags=re.MULTILINE,
)
#: Nom de personnage au-dessus de sa replique, en majuscules, eventuellement
#: suivi d'une indication entre parentheses : « FATOU (au telephone) ».
CHARACTER_CUE_RE = re.compile(
    r"^[ \t]{0,40}([A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ0-9'’\- ]{1,38}?)[ \t]*(?:\([^)]{0,60}\))?[ \t]*$",
    flags=re.MULTILINE,
)
#: Lignes en majuscules qui ne sont pas des personnages.
NOT_A_CHARACTER = {
    "FIN",
    "FIN DU SEGMENT",
    "INT",
    "EXT",
    "JOUR",
    "NUIT",
    "SCENARIO",
    "SCÉNARIO",
    "TITRE",
    "ACTE I",
    "ACTE II",
    "ACTE III",
}


@dataclass
class ScreenplayState:
    """Ce qui a ete etabli par les passes deja ecrites.

    Sans cet etat, chaque passe ne voyait que la FIN de la precedente : un
    personnage presente au premier acte avait disparu du contexte a la
    quatrieme passe, et l'IA le renommait ou le reintroduisait. Les faits sont
    extraits du texte produit, sans appel supplementaire au fournisseur : la
    continuite ne coute donc aucun credit.

    L'extraction est au mieux : un texte qui ne suit pas le format standard ne
    produit rien, et l'on retombe simplement sur le comportement d'avant.
    """

    characters: Counter = field(default_factory=Counter)
    locations: Counter = field(default_factory=Counter)
    segments_written: list[str] = field(default_factory=list)

    def absorb(self, text: str, label: str) -> None:
        self.characters.update(extract_characters(text))
        self.locations.update(extract_locations(text))
        self.segments_written.append(label)

    def _recent_segments(self) -> str:
        """Les derniers segments, et le compte des precedents."""
        recent = self.segments_written[-MAX_RECENT_SEGMENTS:]
        earlier = len(self.segments_written) - len(recent)
        listed = " · ".join(recent)
        return f"{earlier} segment(s) plus tôt, puis {listed}" if earlier else listed

    def as_prompt_block(self) -> list[str]:
        """Rappel des faits etablis, insere dans le prompt de la passe suivante."""
        if not self.segments_written:
            return []

        lines = [
            "",
            "ÉLÉMENTS DÉJÀ ÉTABLIS DANS LES SEGMENTS PRÉCÉDENTS",
            "--------------------------------------------------",
            "Respecte ces noms et ces lieux à la lettre. Ne réintroduis ni ne "
            "re-présente un personnage déjà apparu, et ne renomme aucun lieu.",
            "Segments déjà écrits : " + self._recent_segments() + ".",
        ]
        if self.characters:
            names = [
                f"{name} ({count})"
                for name, count in self.characters.most_common(MAX_TRACKED_CHARACTERS)
            ]
            lines.append("Personnages déjà présents (nombre de répliques) : " + ", ".join(names) + ".")
        if self.locations:
            places = [
                place for place, _ in self.locations.most_common(MAX_TRACKED_LOCATIONS)
            ]
            lines.append("Lieux déjà utilisés : " + ", ".join(places) + ".")
        return lines


def extract_characters(text: str) -> list[str]:
    """Noms de personnages ayant une replique dans ce texte."""
    found: list[str] = []
    for match in CHARACTER_CUE_RE.finditer(text):
        name = match.group(1).strip().rstrip(":").strip()
        if len(name) < 2 or name in NOT_A_CHARACTER:
            continue
        if any(name.startswith(prefix) for prefix in ("INT", "EXT", "ACTE", "FIN")):
            continue
        if not any(char.isalpha() for char in name):
            continue
        found.append(name)
    return found


def extract_locations(text: str) -> list[str]:
    """Lieux tires des en-tetes de sequence."""
    return [match.group(1).strip() for match in SCENE_HEADING_RE.finditer(text) if match.group(1).strip()]


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


def effective_max_passes(max_passes: int | None = None) -> int:
    return max(max_passes if max_passes is not None else settings.screenplay_max_passes, 1)


def max_supported_minutes(max_tokens_per_call: int, max_passes: int | None = None) -> int:
    """Durée maximale que le plafond de passes permet de couvrir.

    Calculée à partir du découpage réel — la répartition par acte introduit des
    arrondis, si bien qu'une simple multiplication surestimerait la limite.
    """
    ceiling = effective_max_passes(max_passes)
    per_pass = pages_per_pass(max_tokens_per_call)
    minutes = per_pass
    while len(_split_blocks(minutes + 1, per_pass)) <= ceiling:
        minutes += 1
    return minutes


def plan_segments(
    target_minutes: int, max_tokens_per_call: int, max_passes: int | None = None
) -> list[ScreenplaySegment]:
    """Découpe le scénario en passes compatibles avec la limite du fournisseur.

    Le nombre de passes suit la durée demandée : une durée plus longue coûte
    plus de passes, elle ne devient pas irréalisable. `AI_MAX_OUTPUT_TOKENS`
    fixe ce qu'une passe produit, pas la longueur totale du scénario.

    Chaque segment produit reste sous le plafond de sortie d'un appel : aucun
    segment n'est jamais plus long que ce qu'une passe peut réellement écrire,
    faute de quoi l'utilisateur paierait des crédits pour un scénario tronqué.

    Lève `AppError` au-delà du plafond de sécurité (`SCREENPLAY_MAX_PASSES`),
    plutôt que de renvoyer un plan irréalisable.
    """
    total_pages = max(target_minutes, 1)
    per_pass = pages_per_pass(max_tokens_per_call)
    ceiling = effective_max_passes(max_passes)

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

    if len(raw_blocks) > ceiling:
        from app.core.errors import AppError

        raise AppError(
            f"Durée trop longue pour une génération en une fois : {target_minutes} minutes "
            f"demanderaient {len(raw_blocks)} passes, au-delà de la limite de {ceiling}. "
            f"Maximum réalisable avec la configuration actuelle : "
            f"{max_supported_minutes(max_tokens_per_call, ceiling)} minutes.",
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
    state: ScreenplayState | None = None,
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

    if state is not None:
        instructions.extend(state.as_prompt_block())

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
