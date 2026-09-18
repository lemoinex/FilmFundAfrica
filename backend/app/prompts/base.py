"""Systeme de prompts versionnes.

Regles :
- aucun prompt n'est ecrit en dur dans une route API ;
- chaque prompt porte un numero de version, trace dans `document_versions`
  et `ai_usage`, afin de pouvoir comparer la qualite des generations ;
- chaque prompt recoit le contexte structure du projet, jamais du texte libre
  reconstruit a la volee.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.models.enums import DocumentType, ProjectType

if TYPE_CHECKING:  # pragma: no cover
    from app.models.project import Project

MISSING_VALUE_RULE = (
    "Lorsqu'une information nécessaire est absente du contexte, écris exactement "
    "« Information non fournie. » à l'endroit concerné, puis signale-la dans la section "
    "finale. N'invente jamais de personnage, d'événement, de lieu réel, de financement, "
    "de partenaire ni de condition de candidature."
)

MISSING_SECTION_MARKER = "## Informations à compléter"

BASE_SYSTEM_PROMPT = """Tu es un consultant en développement de projets audiovisuels, \
spécialisé dans l'accompagnement des auteurs, réalisateurs et producteurs africains \
francophones auprès des fonds, chaînes, festivals et laboratoires internationaux.

Tu rédiges des documents de dossier professionnels, sobres et concrets, du niveau \
attendu par un comité de lecture de fonds d'aide.

Règles absolues :
- {missing_rule}
- Pas de superlatifs creux, pas de remplissage, pas de répétition pour atteindre une longueur.
- Tu respectes strictement la structure demandée et la longueur cible.
- Tu écris en {language}.
- Tu ne mentionnes jamais que tu es une IA et tu ne commentes pas ta propre production.
- Tu termines toujours par une section « {missing_marker} » listant, en puces, les \
informations manquantes que l'utilisateur doit renseigner. Si rien ne manque, écris \
« Aucune information manquante. »
"""

#: Nombre de mots par page A4 de dossier (hors scenario).
WORDS_PER_PAGE = 450
#: Un scenario suit la regle : 1 page de scenario ~= 1 minute a l'ecran.
SCREENPLAY_WORDS_PER_PAGE = 190


@dataclass(slots=True)
class PromptContext:
    """Contexte structure d'un projet, transmis tel quel aux prompts."""

    title: str
    project_type: str
    genre: str | None = None
    country: str | None = None
    language: str = "Français"
    duration: int | None = None
    theme: str | None = None
    logline: str | None = None
    short_synopsis: str | None = None
    long_synopsis: str | None = None
    concept: str | None = None
    stakes: str | None = None
    director_vision: str | None = None
    objectives: str | None = None
    target_audience: str | None = None
    status: str | None = None
    characters: list[dict[str, Any]] = field(default_factory=list)
    existing_documents: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_project(
        cls, project: Project, existing_documents: dict[str, str] | None = None
    ) -> PromptContext:
        return cls(
            title=project.title,
            project_type=str(project.project_type),
            genre=project.genre,
            country=project.country,
            language=project.language,
            duration=project.duration,
            theme=project.theme,
            logline=project.logline,
            short_synopsis=project.short_synopsis,
            long_synopsis=project.long_synopsis,
            concept=project.concept,
            stakes=project.stakes,
            director_vision=project.director_vision,
            objectives=project.objectives,
            target_audience=project.target_audience,
            status=str(project.status),
            characters=[
                {
                    "name": character.name,
                    "role": character.role,
                    "age": character.age,
                    "description": character.description,
                    "arc": character.arc,
                }
                for character in project.characters
            ],
            existing_documents=existing_documents or {},
        )

    def to_dict(self) -> dict[str, Any]:
        labels = {
            "title": "Titre",
            "project_type": "Type de projet",
            "genre": "Genre",
            "country": "Pays",
            "language": "Langue",
            "duration": "Durée (minutes)",
            "theme": "Thème",
            "logline": "Logline",
            "short_synopsis": "Synopsis court",
            "long_synopsis": "Synopsis long",
            "concept": "Concept",
            "stakes": "Enjeux",
            "director_vision": "Vision du réalisateur",
            "objectives": "Objectifs",
            "target_audience": "Public cible",
            "status": "Statut",
        }
        payload: dict[str, Any] = {}
        for attribute, label in labels.items():
            value = getattr(self, attribute)
            if value not in (None, ""):
                payload[label] = str(value)
        if self.characters:
            payload["characters"] = self.characters
        return payload

    def render_block(self) -> str:
        """Bloc texte lisible, injecte dans le prompt utilisateur."""
        lines = ["CONTEXTE DU PROJET", "=================="]
        for label, value in self.to_dict().items():
            if label == "characters":
                continue
            lines.append(f"{label} : {value}")

        if self.characters:
            lines.append("")
            lines.append("PERSONNAGES")
            lines.append("-----------")
            for character in self.characters:
                descriptor = ", ".join(
                    f"{key} : {value}"
                    for key, value in character.items()
                    if value not in (None, "")
                )
                lines.append(f"- {descriptor}")
        else:
            lines.append("")
            lines.append("PERSONNAGES : aucun personnage n'a été saisi par l'utilisateur.")

        if self.existing_documents:
            lines.append("")
            lines.append("DOCUMENTS DÉJÀ VALIDÉS PAR L'UTILISATEUR")
            lines.append("----------------------------------------")
            lines.append(
                "Le document à produire doit être cohérent avec ceux-ci "
                "(personnages, intrigue, ton, intentions) :"
            )
            for label, content in self.existing_documents.items():
                excerpt = content.strip()
                if len(excerpt) > 4000:
                    excerpt = excerpt[:4000] + "\n[...extrait tronqué...]"
                lines.append("")
                lines.append(f"### {label}")
                lines.append(excerpt)

        return "\n".join(lines)


@dataclass(slots=True)
class RenderedPrompt:
    system_prompt: str
    user_prompt: str
    outline: list[str]
    prompt_name: str
    prompt_version: str
    document_label: str
    max_output_tokens: int
    temperature: float
    context_json: str
    #: Longueur cible en mots, utile pour le suivi qualite et le decoupage.
    target_words_hint: int = 0


@dataclass(slots=True)
class PromptTemplate:
    """Definition versionnee d'un prompt de generation."""

    name: str
    version: str
    document_type: DocumentType
    document_label: str
    mission: str
    outline: list[str]
    #: Longueur cible en pages A4, ou None si pilotee par la duree du projet.
    target_pages: tuple[float, float] | None = None
    style_notes: list[str] = field(default_factory=list)
    temperature: float = 0.7
    #: Documents dont le contenu doit etre injecte pour garantir la coherence.
    depends_on: tuple[DocumentType, ...] = ()
    #: Restreint le prompt a certains types de projet (vide = tous).
    applies_to: tuple[ProjectType, ...] = ()

    # ------------------------------------------------------------------
    def target_words(self, context: PromptContext, target_duration: int | None = None) -> int:
        if self.document_type == DocumentType.SCREENPLAY:
            minutes = target_duration or context.duration or 90
            return int(minutes * SCREENPLAY_WORDS_PER_PAGE)
        if self.target_pages is None:
            return 900
        low, high = self.target_pages
        return int((low + high) / 2 * WORDS_PER_PAGE)

    def length_instruction(
        self, context: PromptContext, target_duration: int | None = None
    ) -> str:
        if self.document_type == DocumentType.SCREENPLAY:
            minutes = target_duration or context.duration or 90
            pages = minutes
            return (
                f"LONGUEUR CIBLE : {pages} pages de scénario, soit environ {minutes} minutes "
                f"à l'écran (règle : 1 page ≈ 1 minute), soit environ "
                f"{self.target_words(context, target_duration)} mots. "
                "La longueur doit venir du nombre de séquences et de la densité dramatique, "
                "jamais d'un étirement artificiel des dialogues ou des descriptions."
            )
        if self.target_pages is None:
            return "LONGUEUR CIBLE : adaptée au type et à l'ampleur du projet."
        low, high = self.target_pages
        low_label = f"{low:g}"
        high_label = f"{high:g}"
        pages_label = low_label if low == high else f"{low_label} à {high_label}"
        return (
            f"LONGUEUR CIBLE : {pages_label} page(s) A4, soit environ "
            f"{self.target_words(context)} mots. Respecte d'abord la structure imposée ; "
            "n'ajoute jamais de remplissage pour atteindre la longueur."
        )

    # ------------------------------------------------------------------
    def render(
        self,
        context: PromptContext,
        *,
        language: str = "français",
        target_duration: int | None = None,
        additional_instructions: str | None = None,
    ) -> RenderedPrompt:
        system_prompt = BASE_SYSTEM_PROMPT.format(
            missing_rule=MISSING_VALUE_RULE,
            language=language,
            missing_marker=MISSING_SECTION_MARKER.replace("## ", ""),
        )

        sections = "\n".join(f"{index}. {item}" for index, item in enumerate(self.outline, 1))
        blocks = [
            f"MISSION\n=======\n{self.mission}",
            "",
            context.render_block(),
            "",
            f"STRUCTURE OBLIGATOIRE\n=====================\n{sections}",
            "",
            self.length_instruction(context, target_duration),
        ]

        if self.style_notes:
            notes = "\n".join(f"- {note}" for note in self.style_notes)
            blocks.extend(["", f"EXIGENCES DE FORME\n==================\n{notes}"])

        if additional_instructions:
            blocks.extend(
                [
                    "",
                    "CONSIGNES COMPLÉMENTAIRES DE L'UTILISATEUR",
                    "==========================================",
                    additional_instructions.strip(),
                ]
            )

        blocks.extend(
            [
                "",
                "FORMAT DE SORTIE",
                "================",
                "- Markdown ; un titre de niveau 2 (`##`) par section de la structure.",
                "- Pas de préambule, pas de conclusion méta, pas de commentaire sur la consigne.",
                f"- Termine par la section `{MISSING_SECTION_MARKER}`.",
            ]
        )

        return RenderedPrompt(
            system_prompt=system_prompt,
            user_prompt="\n".join(blocks),
            outline=list(self.outline),
            prompt_name=self.name,
            prompt_version=self.version,
            document_label=self.document_label,
            max_output_tokens=self._max_tokens(context, target_duration),
            temperature=self.temperature,
            context_json=json.dumps(context.to_dict(), ensure_ascii=False),
            target_words_hint=self.target_words(context, target_duration),
        )

    def _max_tokens(self, context: PromptContext, target_duration: int | None) -> int:
        # ~1,6 token par mot en francais, avec une marge de securite.
        return max(1500, min(int(self.target_words(context, target_duration) * 2.2), 32000))


#: Registre global des prompts, indexe par type de document.
PROMPT_REGISTRY: dict[DocumentType, PromptTemplate] = {}


def register(template: PromptTemplate) -> PromptTemplate:
    PROMPT_REGISTRY[template.document_type] = template
    return template


def get_prompt(document_type: DocumentType) -> PromptTemplate:
    from app.core.errors import AppError

    try:
        return PROMPT_REGISTRY[document_type]
    except KeyError as exc:  # pragma: no cover - garde-fou
        raise AppError(
            "prompt.notFound",
            params={"document": document_type},
            code="prompt_not_found",
        ) from exc


REFINE_INSTRUCTIONS: dict[str, str] = {
    "IMPROVE": (
        "Améliore ce document : précision du vocabulaire, clarté des enjeux, force des "
        "formulations, rythme des paragraphes. Conserve strictement la structure, les faits, "
        "les noms de personnages et la longueur approximative. N'ajoute aucun élément "
        "narratif ou factuel absent du texte d'origine."
    ),
    "SHORTEN": (
        "Raccourcis ce document d'environ 30 % en conservant l'intégralité de la structure "
        "et toutes les informations essentielles. Supprime les redites et les formulations "
        "creuses, jamais un élément d'information."
    ),
    "EXPAND": (
        "Développe ce document d'environ 40 % en approfondissant ce qui est déjà présent : "
        "conséquences, nuances, précisions de mise en scène. N'invente aucun personnage, "
        "événement, lieu réel ni financement qui ne figure pas déjà dans le texte ou le "
        "contexte du projet ; écris « Information non fournie. » si un développement exigerait "
        "une information absente."
    ),
    "CORRECT": (
        "Corrige ce document : orthographe, grammaire, conjugaison, typographie française "
        "(espaces insécables, guillemets « »), cohérence des noms propres et des temps. "
        "Ne modifie ni le fond, ni la structure, ni le style."
    ),
}


def build_refine_prompt(
    action: str,
    document_label: str,
    content: str,
    context: PromptContext,
    *,
    language: str = "français",
    instructions: str | None = None,
) -> RenderedPrompt:
    """Prompt de retravail d'un document existant (boutons de l'éditeur)."""
    action_instruction = REFINE_INSTRUCTIONS.get(action, REFINE_INSTRUCTIONS["IMPROVE"])
    system_prompt = BASE_SYSTEM_PROMPT.format(
        missing_rule=MISSING_VALUE_RULE,
        language=language,
        missing_marker=MISSING_SECTION_MARKER.replace("## ", ""),
    )
    blocks = [
        f"MISSION\n=======\n{action_instruction}",
        "",
        context.render_block(),
        "",
        f"DOCUMENT À RETRAVAILLER — {document_label}",
        "=" * 40,
        content.strip(),
    ]
    if instructions:
        blocks.extend(
            ["", "CONSIGNES COMPLÉMENTAIRES", "=========================", instructions.strip()]
        )
    blocks.extend(
        [
            "",
            "FORMAT DE SORTIE",
            "================",
            "- Renvoie uniquement le document retravaillé, en Markdown.",
            "- Aucun commentaire sur les modifications effectuées.",
            f"- Termine par la section `{MISSING_SECTION_MARKER}`.",
        ]
    )
    return RenderedPrompt(
        system_prompt=system_prompt,
        user_prompt="\n".join(blocks),
        outline=[],
        prompt_name=f"refine_{action.lower()}",
        prompt_version="1.0.0",
        document_label=document_label,
        max_output_tokens=max(2000, min(int(len(content.split()) * 3.2), 32000)),
        temperature=0.4,
        context_json=json.dumps(context.to_dict(), ensure_ascii=False),
    )
