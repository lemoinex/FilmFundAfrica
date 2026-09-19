"""Persistance du dossier : ce qui doit survivre a la fin d'une session.

L'enjeu n'est pas d'ecrire des lignes, c'est qu'un second passage reparte de ce
que le premier a laisse — sections remplies, constats encore ouverts, historique
intact — au lieu de recommencer a vide.
"""

from __future__ import annotations

import json

import pytest

from app.agents.contracts import Finding, ProjectState, TrackedFact
from app.agents.orchestrator import Orchestrator, PipelineRun
from app.agents.runner import AgentRunner
from app.models.agents import AgentRun, AgentStep, DossierFinding, DossierModification
from app.models.enums import (
    AgentRole,
    ConfidenceStatus,
    JobStatus,
    Severity,
    ValidationVerdict,
)
from app.models.project import Project
from app.services.ai.base import AICompletionResponse, AIProvider
from app.services.ai.service import AIService
from app.services.dossier_service import DossierService

PATCHES = {
    "DEVELOPMENT": {"public_cible": "18-35, urbain"},
    "SCREENWRITER": {"structure": "trois actes"},
    "DIRECTOR": {"lumiere": "naturelle"},
    "PRODUCER": {"jours_tournage": 24},
    "FINANCING": {"gap_eur": 90000},
    "IMPACT": {"impact_reel": "aucun à ce stade"},
}


class Scripted(AIProvider):
    """Chaque agent remplit sa section ; les validateurs rendent un verdict."""

    name = "scripted"

    def __init__(self, verdict: str = "PASS", findings: list | None = None) -> None:
        self.verdict = verdict
        self.findings = findings or []

    def complete(self, request):
        role = request.metadata["agent_role"]
        is_validator = role.endswith("VALIDATOR")
        patch = PATCHES.get(role)
        return AICompletionResponse(
            text=json.dumps(
                {
                    "analysis": f"## Analyse de {role}",
                    "rationale": "…",
                    "decisions": [],
                    "modifications": {
                        "preserved": [],
                        "modified": [],
                        "removed": [],
                        "added": list(patch) if patch else [],
                        "reasoning": ["première passe"] if patch else [],
                    },
                    "findings": self.findings if is_validator else [],
                    "verdict": self.verdict if is_validator else None,
                    "state_patch": patch,
                    "next_agent_instructions": "",
                },
                ensure_ascii=False,
            ),
            model="m",
            provider=self.name,
        )


def _orchestrator(provider: AIProvider) -> Orchestrator:
    return Orchestrator(AgentRunner(AIService(provider=provider, model="m")))


@pytest.fixture
def dossiers(db_session):
    return DossierService(db_session)


@pytest.fixture
def project_record(db_session, project) -> Project:
    """Le projet créé par l'API, vu comme une ligne et non comme du JSON."""
    return db_session.get(Project, project["id"])


# ----------------------------------------------------------------------


def test_a_fresh_project_starts_from_an_empty_state(dossiers, project_record):
    state = dossiers.load_state(project_record.id)
    assert state.project_id == project_record.id
    assert state.concept == {}
    assert state.characters == []
    assert state.unresolved_issues == []
    assert state.modifications_history == []


def test_the_dossier_is_created_once_per_project(dossiers, project_record):
    first = dossiers.get_or_create(project_record.id)
    assert dossiers.get_or_create(project_record.id).id == first.id


def test_a_run_persists_every_section(dossiers, db_session, project_record):
    run = _orchestrator(Scripted()).run(dossiers.load_state(project_record.id))
    dossiers.save_run(project_record.id, run)
    db_session.commit()

    reloaded = dossiers.load_state(project_record.id)
    assert reloaded.concept == {"public_cible": "18-35, urbain"}
    assert reloaded.production_plan == {"jours_tournage": 24}
    assert reloaded.financing_plan == {"gap_eur": 90000}
    assert reloaded.impact_analysis == {"impact_reel": "aucun à ce stade"}


def test_every_step_is_recorded_in_order(dossiers, db_session, project_record):
    run = _orchestrator(Scripted()).run(dossiers.load_state(project_record.id))
    record = dossiers.save_run(project_record.id, run)
    db_session.commit()

    steps = db_session.query(AgentStep).filter_by(run_id=record.id).order_by(AgentStep.sequence)
    agents = [step.agent for step in steps]
    assert agents[0] is AgentRole.DEVELOPMENT
    assert agents[-1] is AgentRole.FUNDING_PACKAGE_VALIDATOR
    assert len(agents) == 8


def test_the_run_keeps_its_verdict_and_its_guard_rails(dossiers, db_session, project_record):
    run = _orchestrator(Scripted()).run(dossiers.load_state(project_record.id))
    record = dossiers.save_run(project_record.id, run)
    db_session.commit()

    stored = db_session.get(AgentRun, record.id)
    assert stored.verdict is ValidationVerdict.PASS
    assert stored.status is JobStatus.SUCCEEDED
    assert stored.rounds == 0
    assert not stored.exhausted and not stored.stalled
    assert stored.finished_at is not None


def test_modifications_are_traced_with_their_author(dossiers, db_session, project_record):
    run = _orchestrator(Scripted()).run(dossiers.load_state(project_record.id))
    dossiers.save_run(project_record.id, run)
    db_session.commit()

    traces = db_session.query(DossierModification).all()
    assert {trace.agent for trace in traces} == {
        AgentRole.DEVELOPMENT,
        AgentRole.SCREENWRITER,
        AgentRole.DIRECTOR,
        AgentRole.PRODUCER,
        AgentRole.FINANCING,
        AgentRole.IMPACT,
    }
    assert all(trace.reason for trace in traces)


# ----------------------------------------------------------------------
# Ce qui compte vraiment : reprendre ou l'on s'etait arrete


def test_a_second_run_resumes_instead_of_restarting(dossiers, db_session, project_record):
    """Le but de la persistance : le dossier n'est pas reconstruit a vide."""
    first = _orchestrator(Scripted()).run(dossiers.load_state(project_record.id))
    dossiers.save_run(project_record.id, first)
    db_session.commit()

    resumed = dossiers.load_state(project_record.id)
    assert resumed.concept == {"public_cible": "18-35, urbain"}
    assert len(resumed.modifications_history) == 6

    second = _orchestrator(Scripted()).run(resumed)
    dossiers.save_run(project_record.id, second)
    db_session.commit()

    # L'historique s'allonge, il ne se réécrit pas.
    assert len(dossiers.load_state(project_record.id).modifications_history) == 12


def test_history_is_not_duplicated_on_save(dossiers, db_session, project_record):
    """`load_state` remplit l'historique : le réécrire en entier le dupliquerait."""
    run = _orchestrator(Scripted()).run(dossiers.load_state(project_record.id))
    dossiers.save_run(project_record.id, run)
    db_session.commit()
    before = db_session.query(DossierModification).count()

    # Un second enregistrement du même état ne doit rien ajouter.
    dossiers.save_run(project_record.id, _rerun_of(dossiers, project_record.id))
    db_session.commit()
    assert db_session.query(DossierModification).count() == before


def _rerun_of(dossiers, project_id):
    """Passage qui ne modifie rien : l'état rechargé, sans nouvelle trace."""
    return PipelineRun(state=dossiers.load_state(project_id), verdict=ValidationVerdict.PASS)


# ----------------------------------------------------------------------
# Constats


def _blocking() -> list[dict]:
    return [
        {
            "severity": "CRITICAL",
            "element": "budget",
            "description": "Aucun budget fourni.",
            "owner": "PRODUCER",
        }
    ]


def test_open_findings_survive_the_session(dossiers, db_session, project_record):
    run = _orchestrator(Scripted(verdict="BLOCKED", findings=_blocking())).run(
        dossiers.load_state(project_record.id)
    )
    dossiers.save_run(project_record.id, run)
    db_session.commit()

    reloaded = dossiers.load_state(project_record.id)
    assert len(reloaded.blocking_issues()) == 1
    assert reloaded.blocking_issues()[0].owner is AgentRole.PRODUCER


def test_a_resolved_finding_is_dated_not_erased(dossiers, db_session, project_record):
    """Un constat qui disparaît sans trace empêche de savoir s'il a été corrigé."""
    blocked = _orchestrator(Scripted(verdict="BLOCKED", findings=_blocking())).run(
        dossiers.load_state(project_record.id)
    )
    dossiers.save_run(project_record.id, blocked)
    db_session.commit()

    clean = _orchestrator(Scripted()).run(dossiers.load_state(project_record.id))
    dossiers.save_run(project_record.id, clean)
    db_session.commit()

    rows = db_session.query(DossierFinding).all()
    assert len(rows) == 1, "le constat est daté, pas supprimé"
    assert rows[0].resolved_at is not None
    assert dossiers.load_state(project_record.id).unresolved_issues == []


def test_an_unchanged_finding_is_not_duplicated(dossiers, db_session, project_record):
    orchestrator = _orchestrator(Scripted(verdict="BLOCKED", findings=_blocking()))
    for _ in range(2):
        dossiers.save_run(
            project_record.id, orchestrator.run(dossiers.load_state(project_record.id))
        )
        db_session.commit()

    assert db_session.query(DossierFinding).count() == 1


# ----------------------------------------------------------------------
# Historique des verdicts


def test_the_verdict_history_is_derived_not_stored(dossiers, db_session, project_record):
    """Deux sources de vérité finiraient par diverger : il n'y en a qu'une."""
    dossiers.save_run(
        project_record.id, _orchestrator(Scripted()).run(dossiers.load_state(project_record.id))
    )
    db_session.commit()

    history = dossiers.load_state(project_record.id).validation_history
    # Les deux validateurs du passage, et eux seuls.
    assert history == [ValidationVerdict.PASS, ValidationVerdict.PASS]


def test_deleting_a_dossier_takes_its_whole_history_with_it(
    dossiers, db_session, project_record
):
    """Supprimer un dossier ne doit pas laisser d'étapes ni de traces orphelines.

    C'est la cascade ORM qui est vérifiée ici. La cascade côté base
    (`projects` → `project_dossiers`) est réelle sur PostgreSQL, mais SQLite
    n'applique pas les clés étrangères dans cette suite : l'affirmer ici
    donnerait une garantie que le test ne prouve pas.
    """
    dossiers.save_run(
        project_record.id, _orchestrator(Scripted()).run(dossiers.load_state(project_record.id))
    )
    db_session.commit()
    assert db_session.query(AgentStep).count() == 8

    db_session.delete(dossiers.get_or_create(project_record.id))
    db_session.commit()

    assert db_session.query(AgentRun).count() == 0
    assert db_session.query(AgentStep).count() == 0
    assert db_session.query(DossierModification).count() == 0
    assert db_session.query(DossierFinding).count() == 0


def test_a_finding_without_an_owner_is_still_persisted(dossiers, db_session, project_record):
    """Un constat orphelin doit rester visible, pas disparaître à l'écriture."""
    orphan = [{"severity": "MAJOR", "element": "dossier", "description": "flou"}]
    run = _orchestrator(Scripted(verdict="REQUIRES_CORRECTION", findings=orphan)).run(
        dossiers.load_state(project_record.id)
    )
    dossiers.save_run(project_record.id, run)
    db_session.commit()

    stored = db_session.query(DossierFinding).all()
    assert len(stored) == 1
    assert stored[0].severity is Severity.MAJOR
    # Le moteur l'a attribué à son émetteur plutôt que de le perdre.
    assert stored[0].owner is not None


def test_findings_keep_their_suggested_correction(dossiers, db_session, project_record):
    with_fix = [
        {
            "severity": "MAJOR",
            "element": "budget",
            "description": "incohérent",
            "owner": "PRODUCER",
            "suggested_correction": "Aligner le budget sur 24 jours.",
        }
    ]
    run = _orchestrator(Scripted(verdict="REQUIRES_CORRECTION", findings=with_fix)).run(
        dossiers.load_state(project_record.id)
    )
    dossiers.save_run(project_record.id, run)
    db_session.commit()

    stored = db_session.query(DossierFinding).first()
    assert stored.suggested_correction == "Aligner le budget sur 24 jours."


def test_a_tracked_logline_keeps_its_provenance(dossiers, db_session, project_record):
    """Le statut d'une information doit survivre, sinon la règle §18 ne tient plus."""
    state = dossiers.load_state(project_record.id)
    state.logline = TrackedFact(
        value="Un chauffeur de taxi…", status=ConfidenceStatus.PROVIDED_BY_USER
    )
    dossiers.save_run(project_record.id, PipelineRun(state=state))
    db_session.commit()

    reloaded = dossiers.load_state(project_record.id)
    assert reloaded.logline.status is ConfidenceStatus.PROVIDED_BY_USER
    assert reloaded.logline.is_usable_for_funding()


def test_an_empty_state_carries_no_finding(dossiers, project_record):
    assert ProjectState(project_id=project_record.id).blocking_issues() == []
    assert Finding(severity=Severity.MINOR, element="x", description="y").is_blocking() is False
