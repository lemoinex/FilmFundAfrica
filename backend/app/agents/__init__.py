"""Chaine d'agents du dossier de financement.

L'import de ce module suffit a peupler `AGENT_REGISTRY` : chaque module d'agent
s'enregistre lui-meme via `register()`, comme les prompts de document.

La chaine n'est pas strictement lineaire. Les six premiers agents construisent
le dossier ; les deux derniers le controlent et peuvent le renvoyer. C'est
`correction_route()` qui dit ou repartir, et il ne repart jamais du seul agent
fautif : une correction de budget qui ne re-traverserait pas le financement
laisserait un plan de financement assis sur des chiffres qui n'existent plus.
"""

from app.agents import (  # noqa: F401  (imports a effet de bord : enregistrement)
    consistency_validator,
    development,
    director,
    financing,
    funding_package_validator,
    impact,
    producer,
    screenwriter,
)
from app.agents.base import AGENT_REGISTRY, AgentDefinition, get_agent, register
from app.agents.contracts import (
    AgentInput,
    AgentOutput,
    ChangeSet,
    DecisionRecord,
    Finding,
    ModificationTrace,
    ProjectState,
    TrackedFact,
)
from app.models.enums import AgentRole, Severity, ValidationVerdict

#: Ordre d'intervention, tel qu'il est declare dans `AgentRole`.
AGENT_PIPELINE: tuple[AgentRole, ...] = tuple(AgentRole)

#: Les agents qui construisent le dossier.
BUILDER_AGENTS: tuple[AgentRole, ...] = (
    AgentRole.DEVELOPMENT,
    AgentRole.SCREENWRITER,
    AgentRole.DIRECTOR,
    AgentRole.PRODUCER,
    AgentRole.FINANCING,
    AgentRole.IMPACT,
)

#: Les instances de controle. Elles ne modifient pas le dossier, elles statuent.
VALIDATOR_AGENTS: tuple[AgentRole, ...] = (
    AgentRole.CONSISTENCY_VALIDATOR,
    AgentRole.FUNDING_PACKAGE_VALIDATOR,
)


def next_agent(role: AgentRole) -> AgentRole | None:
    """Agent suivant dans la chaine, ou `None` au bout."""
    index = AGENT_PIPELINE.index(role)
    following = AGENT_PIPELINE[index + 1 :]
    return following[0] if following else None


def correction_route(owner: AgentRole) -> tuple[AgentRole, ...]:
    """Agents a rejouer pour corriger un constat confie a `owner`.

    On repart de l'agent responsable et l'on redescend jusqu'au bout de la
    chaine, validateurs compris. Reprendre l'agent seul suffirait a corriger le
    symptome, jamais ses consequences : un budget revu change le plan de
    financement, qui change ce que le validateur doit relire.
    """
    index = AGENT_PIPELINE.index(owner)
    return AGENT_PIPELINE[index:]


def is_exportable(verdict: ValidationVerdict) -> bool:
    """Un dossier `BLOCKED` ne part pas, meme sur demande expresse.

    `REQUIRES_CORRECTION` ne part pas non plus : il a vocation a repasser par la
    boucle. Seuls `PASS` et `PASS_WITH_WARNINGS` autorisent l'export final.
    """
    return verdict in (ValidationVerdict.PASS, ValidationVerdict.PASS_WITH_WARNINGS)


def verdict_for(findings: list[Finding]) -> ValidationVerdict:
    """Verdict deduit des constats, sans indulgence.

    Un seul constat critique bloque. C'est volontairement brutal : un fonds ne
    se represente souvent qu'une fois par an, et une piece obligatoire manquante
    n'est pas rattrapable apres depot.
    """
    severities = {finding.severity for finding in findings}
    if Severity.CRITICAL in severities:
        return ValidationVerdict.BLOCKED
    if Severity.MAJOR in severities:
        return ValidationVerdict.REQUIRES_CORRECTION
    if Severity.MINOR in severities:
        return ValidationVerdict.PASS_WITH_WARNINGS
    return ValidationVerdict.PASS


__all__ = [
    "AGENT_PIPELINE",
    "AGENT_REGISTRY",
    "BUILDER_AGENTS",
    "VALIDATOR_AGENTS",
    "AgentDefinition",
    "AgentInput",
    "AgentOutput",
    "ChangeSet",
    "DecisionRecord",
    "Finding",
    "ModificationTrace",
    "ProjectState",
    "TrackedFact",
    "correction_route",
    "get_agent",
    "is_exportable",
    "next_agent",
    "register",
    "verdict_for",
]
