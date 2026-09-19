"""Moteur d'execution : lecture de la sortie, application, orchestration.

Le fournisseur est remplace par un double que l'on pilote : ce qui est teste
ici, c'est la reaction du moteur a ce qu'un modele peut reellement renvoyer —
du JSON propre, du JSON emballe, du JSON faux — et non la qualite d'une
generation.
"""

from __future__ import annotations

import json

import pytest

from app.agents import correction_route, get_agent
from app.agents.contracts import Finding, ProjectState
from app.agents.orchestrator import Orchestrator
from app.agents.runner import AgentInput, AgentRunner, extract_json, parse_agent_response
from app.core.errors import AppError
from app.models.enums import AgentRole, Severity, ValidationVerdict
from app.services.ai.base import AICompletionRequest, AICompletionResponse, AIProvider
from app.services.ai.service import AIService


class ScriptedProvider(AIProvider):
    """Repond ce qu'on lui dit, agent par agent."""

    name = "scripted"

    def __init__(self, by_role: dict[str, str], default: str | None = None) -> None:
        self.by_role = by_role
        self.default = default
        self.calls: list[str] = []

    def complete(self, request: AICompletionRequest) -> AICompletionResponse:
        role = request.metadata.get("agent_role", "?")
        self.calls.append(role)
        text = self.by_role.get(role, self.default)
        assert text is not None, f"aucune réponse prévue pour {role}"
        return AICompletionResponse(text=text, model="scripted", provider=self.name)


def _payload(role: AgentRole = AgentRole.DEVELOPMENT) -> AgentInput:
    return AgentInput(
        project_state=ProjectState(project_id="p-1", project_identity={"title": "Taxi 237"}),
        current_agent_role=role,
    )


def _response(**overrides) -> str:
    body = {
        "analysis": "## PROJECT_DEVELOPMENT_ANALYSIS\nLe concept tient.",
        "rationale": "Rien à retirer.",
        "decisions": [],
        "modifications": {
            "preserved": ["logline"],
            "modified": [],
            "removed": [],
            "added": [],
            "reasoning": [],
        },
        "findings": [],
        "verdict": None,
        "state_patch": None,
        "next_agent_instructions": "",
    }
    body.update(overrides)
    return json.dumps(body, ensure_ascii=False)


def _runner(text: str) -> AgentRunner:
    return AgentRunner(AIService(provider=ScriptedProvider({}, default=text), model="m"))


# ----------------------------------------------------------------------
# Lire la sortie du modele


def test_a_clean_json_object_is_read():
    assert extract_json('{"analysis": "ok"}') == {"analysis": "ok"}


def test_a_fenced_object_is_read():
    """Un modele encadre volontiers sa reponse d'un bloc de code."""
    assert extract_json('```json\n{"analysis": "ok"}\n```') == {"analysis": "ok"}
    assert extract_json('```\n{"analysis": "ok"}\n```') == {"analysis": "ok"}


def test_a_talkative_model_is_tolerated():
    """Refuser une politesse couterait une passe entiere."""
    text = 'Voici le résultat :\n{"analysis": "ok"}\nJ\'espère que cela convient.'
    assert extract_json(text) == {"analysis": "ok"}


@pytest.mark.parametrize("text", ["", "aucun JSON ici", "[1, 2, 3]", "{pas du json}"])
def test_an_unreadable_output_fails_loudly(text):
    """Mieux vaut une etape qui echoue qu'une etape au verdict devine."""
    with pytest.raises(AppError) as refused:
        extract_json(text)
    assert refused.value.code == "agent_output_not_json"


def test_an_unexpected_key_is_refused():
    """`extra=forbid` : une cle inventee signale une consigne mal suivie."""
    with pytest.raises(AppError) as refused:
        parse_agent_response('{"analysis": "ok", "conclusion": "…"}')
    assert refused.value.code == "agent_output_invalid"


def test_an_invalid_severity_is_refused_and_named():
    with pytest.raises(AppError) as refused:
        parse_agent_response(
            _response(findings=[{"severity": "URGENT", "element": "x", "description": "y"}])
        )
    assert refused.value.code == "agent_output_invalid"
    # Le champ fautif est nomme : sans cela, le diagnostic se ferait a l'aveugle.
    assert "severity" in str(refused.value.params["details"])


# ----------------------------------------------------------------------
# Appliquer la sortie


def test_the_runner_never_takes_the_models_word_for_who_it_is():
    """Le role vient de la definition, jamais de la reponse."""
    output = _runner(_response()).run(get_agent(AgentRole.DIRECTOR), _payload())
    assert output.agent is AgentRole.DIRECTOR
    assert output.version == get_agent(AgentRole.DIRECTOR).version


def test_a_builder_enriches_its_own_section():
    output = _runner(_response(state_patch={"ton": "réaliste"})).run(
        get_agent(AgentRole.DIRECTOR), _payload()
    )
    assert output.updated_state.director_vision == {"ton": "réaliste"}


@pytest.mark.parametrize(
    "role", [AgentRole.CONSISTENCY_VALIDATOR, AgentRole.FUNDING_PACKAGE_VALIDATOR]
)
def test_a_validator_cannot_rewrite_what_it_reviews(role):
    """Un controle qui modifie le dossier n'est plus independant de lui."""
    with pytest.raises(AppError) as refused:
        _runner(_response(state_patch={"budget": 1})).run(get_agent(role), _payload())
    assert refused.value.code == "agent_patch_not_allowed"


def test_changes_are_traced_with_their_reason():
    output = _runner(
        _response(
            modifications={
                "preserved": [],
                "modified": ["Acte II"],
                "removed": ["Personnage secondaire"],
                "added": [],
                "reasoning": ["Resserrer l'intrigue"],
            }
        )
    ).run(get_agent(AgentRole.SCREENWRITER), _payload())

    traces = output.updated_state.modifications_history
    assert {trace.element for trace in traces} == {"Acte II", "Personnage secondaire"}
    assert all("Resserrer l'intrigue" in trace.reason for trace in traces)
    assert all(trace.agent is AgentRole.SCREENWRITER for trace in traces)


def test_an_unjustified_change_is_traced_as_such():
    """Une modification sans raison ne doit pas passer pour justifiée."""
    output = _runner(
        _response(
            modifications={
                "preserved": [],
                "modified": ["Acte I"],
                "removed": [],
                "added": [],
                "reasoning": [],
            }
        )
    ).run(get_agent(AgentRole.SCREENWRITER), _payload())
    assert output.updated_state.modifications_history[0].reason == "non justifié"


def test_findings_are_carried_into_the_state():
    output = _runner(
        _response(
            findings=[
                {
                    "severity": "MAJOR",
                    "element": "lieu",
                    "description": "Douala ou Dakar ?",
                    "owner": "PRODUCER",
                }
            ]
        )
    ).run(get_agent(AgentRole.CONSISTENCY_VALIDATOR), _payload())
    assert [issue.owner for issue in output.updated_state.unresolved_issues] == [
        AgentRole.PRODUCER
    ]


def test_an_agent_clears_its_own_previous_findings():
    """Une reprise corrige ses propres remarques, elle ne les empile pas."""
    runner = _runner(_response(findings=[]))
    payload = _payload(AgentRole.PRODUCER)
    payload.project_state.unresolved_issues.append(
        Finding(
            severity=Severity.MAJOR,
            element="budget",
            description="ancien constat",
            owner=AgentRole.PRODUCER,
        )
    )
    output = runner.run(get_agent(AgentRole.PRODUCER), payload)
    assert output.updated_state.unresolved_issues == []


def test_the_input_state_is_left_untouched():
    """Le moteur travaille sur une copie : un echec ne doit rien abimer."""
    payload = _payload(AgentRole.DIRECTOR)
    _runner(_response(state_patch={"ton": "réaliste"})).run(
        get_agent(AgentRole.DIRECTOR), payload
    )
    assert payload.project_state.director_vision == {}


# ----------------------------------------------------------------------
# Orchestration


def _orchestrator(by_role: dict, default: str) -> tuple[Orchestrator, ScriptedProvider]:
    provider = ScriptedProvider(by_role, default=default)
    return Orchestrator(AgentRunner(AIService(provider=provider, model="m"))), provider


def test_a_clean_run_needs_no_correction():
    clean = _response(verdict="PASS")
    orchestrator, provider = _orchestrator({}, clean)
    run = orchestrator.run(ProjectState(project_id="p-1"))

    assert run.verdict is ValidationVerdict.PASS
    assert run.is_exportable
    assert run.rounds == 0
    assert len(provider.calls) == 8


def test_a_blocking_finding_forbids_export():
    blocked = _response(
        verdict="BLOCKED",
        findings=[
            {"severity": "CRITICAL", "element": "budget", "description": "absent"}
        ],
    )
    orchestrator, _ = _orchestrator({}, blocked)
    run = orchestrator.run(ProjectState(project_id="p-1"))
    assert not run.is_exportable
    assert run.blocking_findings()


def test_a_correction_round_can_resolve_the_package():
    """Premier passage en echec, reprise réussie : le dossier devient exportable."""
    state = {"calls": 0}

    class Recovering(ScriptedProvider):
        def complete(self, request):
            state["calls"] += 1
            # Le premier validateur de dossier refuse, les suivants acceptent.
            first_pass = state["calls"] <= 8
            text = (
                _response(
                    verdict="REQUIRES_CORRECTION",
                    findings=[
                        {
                            "severity": "MAJOR",
                            "element": "budget",
                            "description": "incohérent",
                            "owner": "PRODUCER",
                        }
                    ],
                )
                if first_pass
                else _response(verdict="PASS")
            )
            return AICompletionResponse(text=text, model="m", provider=self.name)

    orchestrator = Orchestrator(AgentRunner(AIService(provider=Recovering({}), model="m")))
    run = orchestrator.run(ProjectState(project_id="p-1"))

    assert run.rounds == 1
    assert run.verdict is ValidationVerdict.PASS
    assert run.is_exportable


def test_the_loop_stops_when_a_round_changes_nothing():
    """Rejouer huit appels pour le meme resultat coute cher et ne sert a rien."""
    stuck = _response(
        verdict="REQUIRES_CORRECTION",
        findings=[
            {
                "severity": "MAJOR",
                "element": "budget",
                "description": "incohérent",
                "owner": "PRODUCER",
            }
        ],
    )
    orchestrator, provider = _orchestrator({}, stuck)
    run = orchestrator.run(ProjectState(project_id="p-1"))

    assert run.stalled
    assert run.rounds == 1
    assert not run.is_exportable
    # Un passage complet, puis une seule reprise : pas les trois tours permis.
    assert len(provider.calls) == 8 + len(correction_route(AgentRole.PRODUCER))


def test_the_correction_restarts_from_the_most_upstream_owner():
    """L'ordre du pipeline est l'ordre des dependances.

    Corriger le budget avant le scénario laisserait le budget à refaire une
    fois le scénario modifié.
    """
    mixed = _response(
        verdict="REQUIRES_CORRECTION",
        findings=[
            {
                "severity": "MAJOR",
                "element": "budget",
                "description": "x",
                "owner": "PRODUCER",
            },
            {
                "severity": "CRITICAL",
                "element": "acte II",
                "description": "y",
                "owner": "SCREENWRITER",
            },
        ],
    )
    orchestrator, provider = _orchestrator({}, mixed)
    orchestrator.run(ProjectState(project_id="p-1"))

    # Le neuvième appel ouvre la reprise : c'est le scénariste, pas le
    # producteur, bien que le constat du producteur soit listé en premier.
    assert provider.calls[8] == AgentRole.SCREENWRITER


def test_a_verdict_without_a_fixable_owner_does_not_replay():
    """Quand seuls les validateurs ont des constats, rejouer ne corrige rien.

    Aucun agent constructeur n'est en cause : la chaîne rendrait exactement le
    même dossier, et donc le même verdict.
    """
    orphan = _response(
        verdict="REQUIRES_CORRECTION",
        findings=[{"severity": "MAJOR", "element": "dossier", "description": "flou"}],
    )
    orchestrator, provider = _orchestrator(
        {role.value: orphan for role in (AgentRole.CONSISTENCY_VALIDATOR,
                                         AgentRole.FUNDING_PACKAGE_VALIDATOR)},
        _response(),
    )
    run = orchestrator.run(ProjectState(project_id="p-1"))

    assert run.rounds == 0
    assert len(provider.calls) == 8
    assert not run.is_exportable


def test_a_finding_without_an_owner_is_attributed_not_dropped():
    """Le défaut corrigé : un constat sans destinataire disparaissait.

    Il ne correspondait ni au filtre « émis par cet agent » ni au filtre
    « adressé à un autre », et se perdait entre les deux — détecté puis oublié,
    ce qui est pire que non détecté.
    """
    output = _runner(
        _response(
            findings=[{"severity": "MAJOR", "element": "dossier", "description": "flou"}]
        )
    ).run(get_agent(AgentRole.PRODUCER), _payload())

    issues = output.updated_state.unresolved_issues
    assert len(issues) == 1
    assert issues[0].owner is AgentRole.PRODUCER


def test_the_mock_provider_never_yields_an_exportable_package():
    """Sans modele, rien n'a ete controle : le dire est plus utile que passer."""
    run = Orchestrator().run(ProjectState(project_id="p-1"))
    assert not run.is_exportable
    assert run.verdict is ValidationVerdict.REQUIRES_CORRECTION
