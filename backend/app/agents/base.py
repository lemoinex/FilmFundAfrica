"""Definition d'un agent : sa fonction, ses roles, ce qu'il doit rendre.

Un agent est declare, versionne et enregistre, comme un prompt de document
(`app/prompts/`). Meme raison : pouvoir comparer la qualite d'une etape d'une
version a l'autre, et n'avoir aucune consigne ecrite en dur dans une route.

Ce que la definition porte, et que le prompt seul ne porterait pas :

* le **perimetre** de l'agent — ce qu'il decide, et ce qu'il laisse a un autre ;
* ses **competences**, qui bornent son jugement plutot que de le flatter ;
* son **ancrage contemporain**, parce qu'une expertise ancienne appliquee
  mecaniquement produit un dossier daté ;
* la **structure de sortie** que l'orchestrateur attend de lui.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.agents.contracts import AgentInput
from app.models.enums import AgentRole
from app.prompts.base import MISSING_VALUE_RULE

#: Seniorite simulee, commune a tous les agents.
#:
#: Formulee comme un niveau de jugement, pas comme une biographie : un agent
#: qui « a trente ans de metier » est tente de s'inventer des references, ce que
#: la regle de non-invention interdit precisement.
SENIORITY = (
    "Tu simules le niveau de compétence, de jugement professionnel et de recul "
    "correspondant à plus de trente années d'expérience dans ton domaine. Cette "
    "séniorité se traduit par ta capacité à repérer un problème non évident, à "
    "arbitrer entre plusieurs options défendables, à travailler sous contrainte et "
    "à améliorer un travail existant — jamais par l'invention d'un parcours ou de "
    "références que tu n'as pas."
)

#: Ce que la seniorite ne doit pas devenir.
CONTEMPORARY_RULE = (
    "N'applique jamais mécaniquement une méthode ancienne. L'expérience sert à "
    "juger, pas à répéter : le paysage a changé (plateformes, formats, "
    "coproduction internationale, nouveaux modèles de financement, évolution des "
    "publics, transformation des industries créatives africaines)."
)

#: Ancrage africain commun, formule comme une exigence de justesse.
AFRICAN_CONTEXT_RULE = (
    "Le projet s'inscrit dans un contexte africain, le plus souvent francophone, "
    "et vise aussi des dispositifs internationaux. Traite ce contexte avec la "
    "précision qu'on accorderait à n'importe quel autre : villes, institutions, "
    "réalités économiques et sociales réelles. Aucun exotisme, aucun stéréotype, "
    "aucune Afrique générique — et pas davantage de misérabilisme ni de "
    "célébration de façade."
)

#: Regle de collaboration (§3) : un agent n'est jamais seul devant le projet.
COLLABORATION_RULE = (
    "Tu reçois l'état du projet et les productions des agents qui t'ont précédé. "
    "Lis-les avant de décider : ton rôle est d'apporter une amélioration "
    "professionnelle mesurable, pas de produire le texte le plus long possible."
)

#: Regle de non-destruction (§4).
NON_DESTRUCTION_RULE = (
    "Ne remplace jamais intégralement une production précédente sans justification. "
    "Avant toute modification importante, déclare ce que tu conserves, ce que tu "
    "modifies, ce que tu retires et ce que tu ajoutes, avec la raison "
    "professionnelle de chaque changement. Retirer un élément validé par l'auteur "
    "sans le dire est la faute la plus grave de cette chaîne."
)

#: Regle d'incertitude (§18), jumelle de la regle de non-invention des prompts.
UNCERTAINTY_RULE = (
    "Ne présente jamais une hypothèse comme un fait. Qualifie chaque information "
    "que tu avances : VERIFIED, PROVIDED_BY_USER, INFERRED, ASSUMPTION, "
    "TO_BE_VERIFIED ou UNKNOWN. Une information critique pour l'éligibilité ou le "
    "financement doit être vérifiée avant validation finale."
)

#: Protocole de decision (§5).
DECISION_PROTOCOL = (
    "OBSERVATION → ANALYSIS → RISK → DECISION → MODIFICATION → VALIDATION. "
    "Une modification sans observation ni risque identifié est une préférence, "
    "pas une décision : ne la propose pas."
)


@dataclass(slots=True)
class AgentDefinition:
    """Fonction et roles d'un agent de la chaine."""

    role: AgentRole
    version: str
    #: Intitule metier, tel qu'il apparait dans un dossier.
    profile: str
    mission: str
    #: Ce que l'agent maitrise. Borne son perimetre autant qu'elle l'annonce.
    competencies: list[str]
    #: Ce qu'il doit integrer du paysage actuel.
    contemporary_adaptation: list[str]
    #: Blocs attendus dans sa sortie, dans l'ordre.
    expected_output: list[str]
    #: Regle propre a l'agent, quand son metier en impose une.
    particular_rule: str | None = None
    #: Ce que l'agent ne decide pas : dit a qui revient la main.
    out_of_scope: list[str] = field(default_factory=list)
    temperature: float = 0.4

    # ------------------------------------------------------------------
    def system_prompt(self) -> str:
        blocks = [
            f"Tu es {self.profile}.",
            "",
            SENIORITY,
            "",
            CONTEMPORARY_RULE,
            "",
            AFRICAN_CONTEXT_RULE,
            "",
            "MISSION",
            "=======",
            self.mission,
            "",
            "TON DOMAINE",
            "===========",
            *(f"- {item}" for item in self.competencies),
            "",
            "CE QUE TU DOIS INTÉGRER DU PAYSAGE ACTUEL",
            "=========================================",
            *(f"- {item}" for item in self.contemporary_adaptation),
        ]

        if self.out_of_scope:
            blocks.extend(
                [
                    "",
                    "CE QUI N'EST PAS À TOI",
                    "======================",
                    "Signale-le, ne le tranche pas :",
                    *(f"- {item}" for item in self.out_of_scope),
                ]
            )

        blocks.extend(
            [
                "",
                "RÈGLES ABSOLUES",
                "===============",
                f"- {MISSING_VALUE_RULE}",
                f"- {UNCERTAINTY_RULE}",
                f"- {NON_DESTRUCTION_RULE}",
                f"- {COLLABORATION_RULE}",
                f"- Protocole de décision : {DECISION_PROTOCOL}",
                "- Tu ne mentionnes jamais que tu es une IA et tu ne commentes pas ta "
                "propre production.",
            ]
        )

        if self.particular_rule:
            blocks.extend(["", "RÈGLE PROPRE À TON RÔLE", "=======================", self.particular_rule])

        return "\n".join(blocks)

    # ------------------------------------------------------------------
    def user_prompt(self, payload: AgentInput) -> str:
        """Etat du projet, travail des agents precedents, et sortie attendue."""
        blocks = [
            "ÉTAT DU PROJET",
            "==============",
            payload.project_state.model_dump_json(indent=2, exclude_none=True),
        ]

        if payload.previous_agent_outputs:
            blocks.extend(["", "TRAVAIL DES AGENTS PRÉCÉDENTS", "============================="])
            for output in payload.previous_agent_outputs:
                blocks.extend(
                    [
                        "",
                        f"### {output.agent} (v{output.version})",
                        output.analysis.strip(),
                    ]
                )
                if output.next_agent_instructions.strip():
                    blocks.append(f"Consigne transmise : {output.next_agent_instructions.strip()}")
        else:
            blocks.extend(
                [
                    "",
                    "TRAVAIL DES AGENTS PRÉCÉDENTS : aucun, tu ouvres la chaîne.",
                ]
            )

        if payload.funding_requirements:
            blocks.extend(
                [
                    "",
                    "EXIGENCES DU DISPOSITIF VISÉ",
                    "============================",
                    "Ne complète jamais ces exigences de mémoire : ce qui n'y figure pas "
                    "est à vérifier, pas à supposer.",
                    json.dumps(payload.funding_requirements, ensure_ascii=False, indent=2),
                ]
            )

        if payload.project_context:
            blocks.extend(
                [
                    "",
                    "CONTEXTE COMPLÉMENTAIRE",
                    "=======================",
                    json.dumps(payload.project_context, ensure_ascii=False, indent=2),
                ]
            )

        sections = "\n".join(f"{i}. {name}" for i, name in enumerate(self.expected_output, 1))
        blocks.extend(
            [
                "",
                "STRUCTURE OBLIGATOIRE DE TA RÉPONSE",
                "===================================",
                sections,
                "",
                "FORMAT DE SORTIE",
                "================",
                "- Markdown ; un titre de niveau 2 (`##`) par bloc ci-dessus, dans l'ordre.",
                "- Le bloc de modifications distingue explicitement ce qui est conservé, "
                "modifié, retiré et ajouté, avec la raison de chaque changement.",
                "- Pas de préambule, pas de conclusion méta.",
            ]
        )
        return "\n".join(blocks)


#: Registre des agents, rempli a l'import de `app.agents`.
AGENT_REGISTRY: dict[AgentRole, AgentDefinition] = {}


def register(definition: AgentDefinition) -> AgentDefinition:
    AGENT_REGISTRY[definition.role] = definition
    return definition


def get_agent(role: AgentRole) -> AgentDefinition:
    from app.core.errors import AppError

    try:
        return AGENT_REGISTRY[role]
    except KeyError as exc:  # pragma: no cover - garde-fou
        raise AppError(
            "agent.notFound", params={"agent": role}, code="agent_not_found"
        ) from exc
