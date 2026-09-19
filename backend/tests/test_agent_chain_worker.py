"""La chaine face a la machinerie de file.

Cette machinerie — reservation, battement de coeur, reprise, remboursement —
etait eprouvee avec des generations de document. La chaine est un genre de
tache nouveau qui la reutilise : ce qui est verifie ici, c'est qu'elle s'y
comporte comme il faut, en particulier la ou de l'argent est en jeu.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from app.models.enums import AIOperation, JobKind, JobStatus
from app.models.jobs import GenerationJob
from app.services.ai.base import AICompletionResponse, AIProvider
from app.services.job_service import JobService, run_job
from tests.conftest import job_result

CHAIN_STEPS = 8


class Scripted(AIProvider):
    name = "scripted"

    def __init__(self, verdict: str = "PASS") -> None:
        self.verdict = verdict
        self.calls = 0

    def complete(self, request):
        self.calls += 1
        role = request.metadata["agent_role"]
        return AICompletionResponse(
            text=json.dumps(
                {
                    "analysis": f"## {role}",
                    "rationale": "…",
                    "decisions": [],
                    "modifications": {
                        "preserved": [],
                        "modified": [],
                        "removed": [],
                        "added": [],
                        "reasoning": [],
                    },
                    "findings": [],
                    "verdict": self.verdict if role.endswith("VALIDATOR") else None,
                    "state_patch": {"note": role} if not role.endswith("VALIDATOR") else None,
                    "next_agent_instructions": "",
                },
                ensure_ascii=False,
            ),
            model="modele-test",
            provider=self.name,
            input_tokens=100,
            output_tokens=50,
            latency_ms=12,
        )


@pytest.fixture
def scripted(monkeypatch):
    provider = Scripted()
    monkeypatch.setattr("app.services.ai.service.build_provider", lambda *a, **k: provider)
    return provider


@pytest.fixture
def worker_user(client, make_user):
    headers, data = make_user("worker@example.com", plan="PRO_AUTHOR")
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Projet chaîne", "project_type": "DOCUMENTARY"},
        headers=headers,
    ).json()["id"]
    return headers, data["user"]["id"], project_id


def _launch(client, headers, project_id):
    return client.post(f"/api/v1/projects/{project_id}/dossier/run", headers=headers)


# ----------------------------------------------------------------------
# Ce que la chaîne consomme


def test_a_chain_leaves_a_trace_in_the_usage_ledger(
    client, db_session, worker_user, scripted
):
    """Le défaut corrigé : huit crédits partaient sans aucune ligne de registre.

    L'opération la plus coûteuse du produit était la seule absente du journal
    de consommation — impossible de savoir ce qu'une chaîne coûte en jetons.
    """
    from app.models.billing import AIUsage

    headers, _, project_id = worker_user
    job_result(_launch(client, headers, project_id))

    rows = db_session.query(AIUsage).filter_by(operation=AIOperation.RUN_AGENT_CHAIN).all()
    assert len(rows) == 1
    usage = rows[0]
    assert usage.project_id == project_id
    assert usage.provider == "scripted"
    assert usage.model == "modele-test"
    # Les jetons de toutes les étapes, pas ceux d'une seule.
    assert usage.input_tokens == 100 * CHAIN_STEPS
    assert usage.output_tokens == 50 * CHAIN_STEPS


def test_the_ledger_does_not_debit_a_second_time(client, db_session, worker_user, scripted):
    """Les crédits sont pris à la mise en file : les reprendre les doublerait."""
    from app.models.user import User

    headers, user_id, project_id = worker_user
    before = db_session.get(User, user_id).ai_credits_remaining
    job_result(_launch(client, headers, project_id))
    db_session.expire_all()
    after = db_session.get(User, user_id).ai_credits_remaining

    assert before - after == CHAIN_STEPS


def test_each_step_keeps_its_own_telemetry(client, db_session, worker_user, scripted):
    """Sans elle, comparer le coût d'une version de consigne à l'autre est perdu."""
    from app.models.agents import AgentStep

    headers, _, project_id = worker_user
    job_result(_launch(client, headers, project_id))

    steps = db_session.query(AgentStep).all()
    assert len(steps) == CHAIN_STEPS
    assert all(step.provider == "scripted" for step in steps)
    assert all(step.model == "modele-test" for step in steps)
    assert all(step.input_tokens == 100 for step in steps)
    assert all(step.latency_ms == 12 for step in steps)


# ----------------------------------------------------------------------
# La chaîne dans la file


def test_a_chain_job_is_queued_not_run_inline(client, db_session, worker_user, scripted):
    """Avec un worker, la requête dépose la tâche et rend la main tout de suite."""
    headers, _, project_id = worker_user

    class Listening:
        available = True

        def push(self, job_id):
            self.pushed = job_id
            return True

    from app.models.project import Project
    from app.models.user import User

    queue = Listening()
    service = JobService(db_session, queue=queue)
    user = db_session.query(User).filter_by(email="worker@example.com").one()
    project = db_session.get(Project, project_id)

    job = service.enqueue_agent_chain(user, project)
    assert job.status is JobStatus.QUEUED
    assert queue.pushed == job.id
    assert job.credits_reserved == CHAIN_STEPS
    assert scripted.calls == 0, "aucun agent ne doit tourner dans la requête"


def test_the_worker_picks_up_a_queued_chain(client, db_session, worker_user, scripted):
    """`run_job` est le point d'entrée du worker : la chaîne doit y passer."""
    from app.models.project import Project
    from app.models.user import User

    headers, _, project_id = worker_user

    class Silent:
        available = True

        def push(self, job_id):
            return True

    service = JobService(db_session, queue=Silent())
    user = db_session.query(User).filter_by(email="worker@example.com").one()
    job = service.enqueue_agent_chain(user, db_session.get(Project, project_id))
    assert job.status is JobStatus.QUEUED

    # Ce que fait le worker quand il dépile.
    assert run_job(job.id, db=db_session) is JobStatus.SUCCEEDED
    db_session.expire_all()
    assert db_session.get(GenerationJob, job.id).status is JobStatus.SUCCEEDED
    assert scripted.calls == CHAIN_STEPS


def test_a_chain_job_is_never_executed_twice(client, db_session, worker_user, scripted):
    """Deux workers qui dépilent la même tâche ne doivent pas la payer deux fois."""
    headers, _, project_id = worker_user
    job_result(_launch(client, headers, project_id))
    job_id = db_session.query(GenerationJob).one().id

    calls_after_first = scripted.calls
    assert run_job(job_id, db=db_session) is JobStatus.SUCCEEDED
    assert scripted.calls == calls_after_first, "la tâche a été rejouée"


def test_a_lost_chain_signal_is_recovered(client, db_session, worker_user, scripted):
    """Redis peut perdre le signal : la base reste la source de vérité."""
    from app.models.project import Project
    from app.models.user import User

    headers, _, project_id = worker_user

    class Silent:
        available = True

        def push(self, job_id):
            return True

    service = JobService(db_session, queue=Silent())
    user = db_session.query(User).filter_by(email="worker@example.com").one()
    job = service.enqueue_agent_chain(user, db_session.get(Project, project_id))

    # Vieillie artificiellement pour tomber sous le seuil de reprise.
    job.created_at = datetime.now(UTC) - timedelta(seconds=600)
    db_session.commit()

    assert job.id in service.stale_queued_ids()


def test_an_interrupted_chain_gives_back_all_eight_credits(
    client, db_session, worker_user, scripted
):
    """Rembourser un crédit au lieu de huit ferait perdre sept crédits payés."""
    from app.models.project import Project
    from app.models.user import User

    headers, user_id, project_id = worker_user

    class Silent:
        available = True

        def push(self, job_id):
            return True

    service = JobService(db_session, queue=Silent())
    user = db_session.query(User).filter_by(email="worker@example.com").one()
    job = service.enqueue_agent_chain(user, db_session.get(Project, project_id))
    after_reservation = user.ai_credits_remaining

    # Le worker a disparu en plein passage.
    job.status = JobStatus.RUNNING
    job.started_at = datetime.now(UTC) - timedelta(hours=2)
    job.heartbeat_at = job.started_at
    db_session.commit()

    assert service.fail_timed_out() == 1
    db_session.expire_all()
    assert db_session.get(GenerationJob, job.id).status is JobStatus.FAILED
    assert db_session.get(User, user_id).ai_credits_remaining == after_reservation + CHAIN_STEPS


def test_the_heartbeat_is_refreshed_at_every_agent(
    client, db_session, worker_user, scripted
):
    """Huit appels dépassent le délai d'interruption : sans signe de vie
    régulier, le surveillant tuerait une chaîne qui travaille."""
    headers, _, project_id = worker_user
    job_result(_launch(client, headers, project_id))

    job = db_session.query(GenerationJob).one()
    assert job.heartbeat_at is not None
    assert job.heartbeat_at >= job.started_at
    assert job.completed_passes == CHAIN_STEPS


def test_a_chain_job_carries_no_document_type(client, db_session, worker_user, scripted):
    """Un passage produit un dossier, pas un document : le champ reste vide."""
    headers, _, project_id = worker_user
    job_result(_launch(client, headers, project_id))

    job = db_session.query(GenerationJob).one()
    assert job.kind is JobKind.RUN_AGENT_CHAIN
    assert job.document_type is None
    assert job.document_id is None
