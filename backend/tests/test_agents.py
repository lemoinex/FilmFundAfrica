"""Chaine d'agents : perimetres, contrats, boucle de correction.

Ces tests portent sur ce qui doit rester vrai quelle que soit la redaction des
consignes : que chaque role soit tenu, que les regles communes atteignent
reellement chaque agent, et qu'un constat trouve toujours un responsable.
"""

from __future__ import annotations

import pytest

from app.agents import (
    AGENT_PIPELINE,
    AGENT_REGISTRY,
    BUILDER_AGENTS,
    VALIDATOR_AGENTS,
    AgentInput,
    AgentOutput,
    ChangeSet,
    Finding,
    ProjectState,
    TrackedFact,
    correction_route,
    get_agent,
    is_exportable,
    next_agent,
    verdict_for,
)
from app.core.errors import AppError
from app.models.enums import AgentRole, ConfidenceStatus, Severity, ValidationVerdict

# ----------------------------------------------------------------------
# Chaque agent a sa place


def test_every_role_has_a_definition():
    """Un role sans definition casserait la chaine a l'execution, pas au demarrage."""
    assert set(AGENT_REGISTRY) == set(AgentRole)


def test_the_pipeline_covers_every_agent_once():
    assert len(AGENT_PIPELINE) == len(set(AGENT_PIPELINE)) == len(AgentRole)
    assert BUILDER_AGENTS + VALIDATOR_AGENTS == AGENT_PIPELINE


def test_the_validators_close_the_chain():
    """Le controle vient apres la construction, sinon il ne controle rien."""
    assert AGENT_PIPELINE[-2:] == VALIDATOR_AGENTS
    assert AGENT_PIPELINE[-1] is AgentRole.FUNDING_PACKAGE_VALIDATOR


def test_next_agent_walks_the_chain_and_stops():
    assert next_agent(AgentRole.DEVELOPMENT) is AgentRole.SCREENWRITER
    assert next_agent(AgentRole.IMPACT) is AgentRole.CONSISTENCY_VALIDATOR
    assert next_agent(AgentRole.FUNDING_PACKAGE_VALIDATOR) is None


def test_an_unknown_role_is_refused_with_a_translatable_message():
    with pytest.raises(AppError) as refused:
        get_agent("INEXISTANT")  # type: ignore[arg-type]
    assert refused.value.code == "agent_not_found"


# ----------------------------------------------------------------------
# Fonction et roles


@pytest.mark.parametrize("role", list(AgentRole))
def test_every_agent_declares_its_function_and_roles(role):
    agent = get_agent(role)
    assert agent.profile and agent.mission
    assert agent.competencies, "un agent sans domaine n'a pas de périmètre"
    assert agent.contemporary_adaptation, "l'expertise doit être ancrée dans le présent"
    assert agent.expected_output, "l'orchestrateur doit savoir quoi attendre"


@pytest.mark.parametrize("role", list(AgentRole))
def test_the_common_rules_reach_every_agent(role):
    """Les regles de §19 ne valent que si elles atteignent chaque consigne."""
    system = get_agent(role).system_prompt()
    assert "trente années d'expérience" in system
    # Non-invention, incertitude, non-destruction, collaboration, protocole.
    assert "Information non fournie." in system
    assert "TO_BE_VERIFIED" in system
    assert "Ne remplace jamais intégralement" in system
    assert "OBSERVATION → ANALYSIS → RISK → DECISION" in system
    # L'ancrage africain est une exigence de justesse, pas un decor.
    assert "stéréotype" in system


@pytest.mark.parametrize("role", list(AgentRole))
def test_no_agent_claims_a_domain_it_does_not_own(role):
    """Chaque agent dit ce qu'il laisse a un autre : c'est ce qui evite le silo."""
    assert get_agent(role).out_of_scope


def test_the_validators_do_not_correct_what_they_find():
    """Un validateur qui corrige n'est plus une instance independante."""
    for role in VALIDATOR_AGENTS:
        scope = " ".join(get_agent(role).out_of_scope)
        assert "correction" in scope.lower()


def test_the_financing_agent_is_forbidden_from_inventing_criteria():
    """C'est la regle produit la plus couteuse a enfreindre : un dossier rejete."""
    rule = get_agent(AgentRole.FINANCING).particular_rule or ""
    assert "n'inventes jamais un critère de financement" in rule


def test_the_impact_agent_refuses_manufactured_impact():
    rule = get_agent(AgentRole.IMPACT).particular_rule or ""
    assert "Ne fabrique jamais un argument d'impact" in rule


def test_the_package_validator_does_not_trust_the_agents_before_it():
    rule = get_agent(AgentRole.FUNDING_PACKAGE_VALIDATOR).particular_rule or ""
    assert "jamais qu'un dossier est valide parce que les agents" in rule


def test_the_development_agent_never_restarts_from_scratch():
    rule = get_agent(AgentRole.DEVELOPMENT).particular_rule or ""
    assert "jamais de zéro" in rule


@pytest.mark.parametrize("role", VALIDATOR_AGENTS)
def test_validators_are_the_least_creative(role):
    """Un controle doit etre reproductible, pas inspire."""
    assert get_agent(role).temperature <= 0.2


# ----------------------------------------------------------------------
# Contrats


def _state() -> ProjectState:
    return ProjectState(
        project_id="p-1",
        project_identity={"title": "Taxi 237", "country": "Cameroun"},
        logline=TrackedFact(value="Un chauffeur de taxi…", status=ConfidenceStatus.PROVIDED_BY_USER),
    )


def test_an_agent_receives_the_state_and_what_came_before():
    payload = AgentInput(
        project_state=_state(),
        current_agent_role=AgentRole.SCREENWRITER,
        previous_agent_outputs=[
            AgentOutput(
                agent=AgentRole.DEVELOPMENT,
                version="1.0.0",
                analysis="Le concept tient, le public cible reste flou.",
                next_agent_instructions="Préciser l'arc de la protagoniste.",
            )
        ],
    )
    prompt = get_agent(AgentRole.SCREENWRITER).user_prompt(payload)
    assert "Taxi 237" in prompt
    assert "DEVELOPMENT" in prompt
    assert "Préciser l'arc de la protagoniste." in prompt


def test_the_first_agent_is_told_it_opens_the_chain():
    payload = AgentInput(project_state=_state(), current_agent_role=AgentRole.DEVELOPMENT)
    assert "tu ouvres la chaîne" in get_agent(AgentRole.DEVELOPMENT).user_prompt(payload)


def test_funding_requirements_are_never_to_be_completed_from_memory():
    payload = AgentInput(
        project_state=_state(),
        current_agent_role=AgentRole.FINANCING,
        funding_requirements={"organisme": "Fonds X", "montant_max": 50000},
    )
    prompt = get_agent(AgentRole.FINANCING).user_prompt(payload)
    assert "Fonds X" in prompt
    assert "jamais ces exigences de mémoire" in prompt


def test_an_assumption_cannot_support_a_funding_claim():
    """§18 : le statut n'est pas decoratif, il autorise ou non un usage."""
    assert TrackedFact(value="x", status=ConfidenceStatus.VERIFIED).is_usable_for_funding()
    assert TrackedFact(value="x", status=ConfidenceStatus.PROVIDED_BY_USER).is_usable_for_funding()
    for status in (
        ConfidenceStatus.INFERRED,
        ConfidenceStatus.ASSUMPTION,
        ConfidenceStatus.TO_BE_VERIFIED,
        ConfidenceStatus.UNKNOWN,
    ):
        assert not TrackedFact(value="x", status=status).is_usable_for_funding()


def test_a_fact_without_a_declared_status_is_not_usable():
    """Le defaut doit etre le plus prudent : l'oubli ne doit pas valoir preuve."""
    assert not TrackedFact(value="x").is_usable_for_funding()


def test_a_changeset_says_what_was_destroyed():
    assert ChangeSet(removed=["Personnage secondaire"]).is_destructive()
    assert not ChangeSet(preserved=["Acte I"], modified=["Acte II"]).is_destructive()


# ----------------------------------------------------------------------
# Verdicts et boucle de correction


@pytest.mark.parametrize(
    ("severities", "expected"),
    [
        ([], ValidationVerdict.PASS),
        ([Severity.MINOR], ValidationVerdict.PASS_WITH_WARNINGS),
        ([Severity.MAJOR], ValidationVerdict.REQUIRES_CORRECTION),
        ([Severity.CRITICAL], ValidationVerdict.BLOCKED),
        # La gravite la plus forte l'emporte, quel que soit le nombre de constats.
        ([Severity.MINOR, Severity.CRITICAL, Severity.MAJOR], ValidationVerdict.BLOCKED),
    ],
)
def test_the_verdict_follows_the_worst_finding(severities, expected):
    findings = [
        Finding(severity=severity, element="budget", description="…") for severity in severities
    ]
    assert verdict_for(findings) is expected


def test_a_blocked_package_is_never_exported():
    assert is_exportable(ValidationVerdict.PASS)
    assert is_exportable(ValidationVerdict.PASS_WITH_WARNINGS)
    assert not is_exportable(ValidationVerdict.REQUIRES_CORRECTION)
    assert not is_exportable(ValidationVerdict.BLOCKED)


def test_a_correction_replays_the_consequences_not_only_the_cause():
    """L'exemple de §15 : un budget corrige doit re-traverser le financement."""
    route = correction_route(AgentRole.PRODUCER)
    assert route[0] is AgentRole.PRODUCER
    assert AgentRole.FINANCING in route
    # Et il repasse toujours par les deux controles.
    assert route[-2:] == VALIDATOR_AGENTS


def test_correcting_the_last_builder_still_revalidates():
    assert correction_route(AgentRole.IMPACT) == (AgentRole.IMPACT,) + VALIDATOR_AGENTS


def test_a_finding_carries_the_agent_able_to_fix_it():
    """Sans destinataire, un constat ne serait jamais traite."""
    finding = Finding(
        severity=Severity.MAJOR,
        element="lieu de tournage",
        description="Le scénario dit Douala, le plan de production dit Dakar.",
        owner=AgentRole.PRODUCER,
    )
    assert not finding.is_blocking()
    assert correction_route(finding.owner)[0] is AgentRole.PRODUCER
