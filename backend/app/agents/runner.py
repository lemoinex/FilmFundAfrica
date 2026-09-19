"""Execution d'un agent : consigne -> modele -> sortie validee.

La reponse du modele est du JSON, pas du Markdown a relire. Ce choix se paie en
robustesse a l'entree — un modele encadre volontiers son objet d'un bloc de code
ou d'une phrase — et se rembourse partout ailleurs : une gravite, un verdict ou
le destinataire d'un constat sont des valeurs typees, pas le resultat d'une
expression reguliere appliquee a de la prose.

L'extraction est donc tolerante et la validation stricte. Une sortie qu'on ne
peut pas valider est une erreur franche : mieux vaut une etape qui echoue qu'une
etape dont on croit connaitre le verdict.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.agents.base import AgentDefinition
from app.agents.contracts import (
    AgentInput,
    AgentOutput,
    CallTelemetry,
    ChangeSet,
    DecisionRecord,
    Finding,
    ModificationTrace,
    ProjectState,
)
from app.core.errors import AppError
from app.models.enums import AgentRole, ValidationVerdict
from app.services.ai.service import AIService

logger = logging.getLogger("filmfund.agents")

#: Bloc de code eventuel autour de l'objet JSON.
_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


class AgentResponse(BaseModel):
    """Ce que le modele a le droit de renvoyer.

    `agent` et `version` n'y figurent pas : ils viennent de la definition. Un
    modele qui declarerait lui-meme son role pourrait signer la production d'un
    autre agent, et toute la tracabilite reposerait sur sa bonne foi.
    """

    model_config = ConfigDict(extra="forbid")

    analysis: str = ""
    rationale: str = ""
    decisions: list[DecisionRecord] = Field(default_factory=list)
    modifications: ChangeSet = Field(default_factory=ChangeSet)
    findings: list[Finding] = Field(default_factory=list)
    verdict: ValidationVerdict | None = None
    state_patch: dict[str, Any] | None = None
    next_agent_instructions: str = ""


def extract_json(text: str) -> dict[str, Any]:
    """Objet JSON contenu dans la reponse, quel que soit son emballage."""
    candidate = text.strip()

    fenced = _FENCE.match(candidate)
    if fenced:
        candidate = fenced.group(1).strip()

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        # Dernier recours : le premier objet complet du texte. Un modele
        # bavard place parfois une phrase avant son JSON ; la refuser
        # couterait une passe entiere pour une politesse.
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end <= start:
            raise AppError(
                "agent.outputNotJson", code="agent_output_not_json"
            ) from None
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as exc:
            raise AppError("agent.outputNotJson", code="agent_output_not_json") from exc

    if not isinstance(parsed, dict):
        raise AppError("agent.outputNotJson", code="agent_output_not_json")
    return parsed


def parse_agent_response(text: str) -> AgentResponse:
    """Valide la sortie du modele contre le contrat annonce dans la consigne."""
    try:
        return AgentResponse.model_validate(extract_json(text))
    except ValidationError as exc:
        # `errors()` nomme le champ fautif : sans lui, le diagnostic se ferait
        # en relisant des milliers de caracteres de JSON.
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])} : {error['msg']}"
            for error in exc.errors()[:5]
        )
        raise AppError(
            "agent.outputInvalid", params={"details": details}, code="agent_output_invalid"
        ) from exc


class AgentRunner:
    """Fait tourner un agent et applique sa production a l'etat du projet."""

    def __init__(self, ai_service: AIService | None = None) -> None:
        self.ai = ai_service or AIService()

    # ------------------------------------------------------------------
    def run(self, definition: AgentDefinition, payload: AgentInput) -> AgentOutput:
        prompt = definition.render(payload)
        response = self.ai.run(prompt)
        parsed = parse_agent_response(response.text)

        state = payload.project_state.model_copy(deep=True)
        self._apply_patch(definition, parsed, state)
        self._record(definition, parsed, state)

        logger.info(
            "agent exécuté",
            extra={
                "event": "agent_run",
                "agent": definition.role,
                "agent_version": definition.version,
                "findings": len(parsed.findings),
                "verdict": parsed.verdict,
            },
        )

        return AgentOutput(
            agent=definition.role,
            version=definition.version,
            analysis=parsed.analysis,
            decisions=parsed.decisions,
            modifications=parsed.modifications,
            rationale=parsed.rationale,
            updated_state=state,
            next_agent_instructions=parsed.next_agent_instructions,
            findings=parsed.findings,
            verdict=parsed.verdict,
            telemetry=CallTelemetry(
                provider=response.provider,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
            ),
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _apply_patch(
        definition: AgentDefinition, parsed: AgentResponse, state: ProjectState
    ) -> None:
        """Enrichit la section du dossier qui appartient a l'agent.

        Un validateur qui renverrait un patch se verrait refuser : il statue sur
        le dossier, il ne le reecrit pas. Le refus est franc plutot que
        silencieux — un controle qui modifie ce qu'il controle est un defaut de
        conception, pas une donnee a ignorer.
        """
        if parsed.state_patch is None:
            return
        if definition.state_field is None:
            raise AppError(
                "agent.patchNotAllowed",
                params={"agent": definition.role},
                code="agent_patch_not_allowed",
            )
        section = getattr(state, definition.state_field)
        if isinstance(section, dict):
            section.update(parsed.state_patch)
        else:  # pragma: no cover - garde-fou, aucun champ non-dict n'est patchable
            setattr(state, definition.state_field, parsed.state_patch)

    # ------------------------------------------------------------------
    @staticmethod
    def _record(
        definition: AgentDefinition, parsed: AgentResponse, state: ProjectState
    ) -> None:
        """Journalise ce que l'agent a change et ce qu'il a trouve.

        Les constats remplacent ceux que le meme agent avait laisses : une
        execution corrige ses propres remarques, elle ne les empile pas. Ceux
        des autres agents restent, tant qu'eux seuls peuvent les lever.
        """
        changes = parsed.modifications
        reasons = changes.reasoning or ["non justifié"]
        for element in changes.modified + changes.removed + changes.added:
            state.record(
                ModificationTrace(
                    agent=definition.role,
                    element=element,
                    previous_value=None,
                    new_value=None,
                    reason="; ".join(reasons),
                    impact="déclaré par l'agent",
                    validation_status=parsed.verdict,
                )
            )

        # Un constat sans destinataire revient a son emetteur. Le laisser tel
        # quel le ferait disparaitre des deux filtres ci-dessous : detecte, puis
        # perdu, ce qui est pire que non detecte.
        incoming = [
            finding.model_copy(update={"owner": owner_or_default(finding, definition.role)})
            for finding in parsed.findings
        ]

        kept = [
            issue for issue in state.unresolved_issues if issue.owner is not definition.role
        ]
        # Deux validateurs qui relevent le meme defaut relevent un defaut, pas
        # deux. Sans dedoublonnage ici, l'etat en memoire porterait des doublons
        # que la persistance, elle, fusionne : deux comportements pour une meme
        # donnee.
        state.unresolved_issues = _deduplicate(kept + incoming)

        if parsed.verdict is not None:
            state.validation_history.append(parsed.verdict)


def owner_or_default(finding: Finding, fallback: AgentRole) -> AgentRole:
    """Destinataire d'un constat, avec un repli explicite.

    Un constat sans destinataire ne doit pas disparaitre : faute de mieux il
    revient a l'agent qui l'a emis, ce qui le rend visible plutot que perdu.
    """
    return finding.owner or fallback


def _deduplicate(findings: list[Finding]) -> list[Finding]:
    """Constats distincts, dans l'ordre ou ils sont apparus.

    L'identite d'un constat est ce qu'il decrit, pas qui l'a signale : le meme
    defaut releve par deux validateurs reste un seul defaut a corriger.
    """
    seen: set[tuple[str, str, str]] = set()
    unique: list[Finding] = []
    for finding in findings:
        key = (finding.severity.value, finding.element, finding.description)
        if key not in seen:
            seen.add(key)
            unique.append(finding)
    return unique
