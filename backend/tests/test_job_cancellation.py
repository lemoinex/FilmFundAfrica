"""Arrêter une génération en cours.

Une chaîne d'agents coûte huit crédits et enchaîne seize appels. Lancée par
erreur, rien ne permettait de l'arrêter : il fallait attendre la fin et tout
payer.

Toute la difficulté tient dans le remboursement, et ces tests existent pour
tenir les deux abus à distance. Rendre tout laisserait n'importe qui dépenser
l'argent du fournisseur sans rien payer, en lançant puis en annulant. Ne rien
rendre ferait payer un arrêt à la première passe au prix de huit. On rend ce
qui n'a pas tourné — et le travail déjà produit est conservé, sans quoi on
ferait payer des passes dont il ne resterait rien.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.agents import AGENT_PIPELINE
from app.agents.orchestrator import Orchestrator, PipelineRun
from app.core.database import SessionLocal
from app.models.enums import JobKind, JobStatus
from app.models.jobs import GenerationJob
from app.models.user import User

PROJECT = {
    "title": "Les Gardiennes du fleuve",
    "project_type": "DOCUMENTARY",
    "genre": "Documentaire de création",
    "country": "Sénégal",
    "duration": 90,
    "theme": "Transmission",
    "concept": "Trois générations face à la salinisation du delta.",
}


@pytest.fixture
def project_id(client, auth_headers) -> str:
    return client.post("/api/v1/projects", json=PROJECT, headers=auth_headers).json()["id"]


def _make_job(user_email: str, project_id: str, **overrides) -> str:
    """Pose une tâche directement en base, dans l'état voulu."""
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == user_email).one()
        job = GenerationJob(
            user_id=user.id,
            project_id=project_id,
            kind=JobKind.RUN_AGENT_CHAIN,
            total_passes=len(AGENT_PIPELINE),
            credits_reserved=8,
            payload={},
            **{"status": JobStatus.QUEUED, **overrides},
        )
        db.add(job)
        db.commit()
        return job.id


def _job(job_id: str) -> GenerationJob:
    with SessionLocal() as db:
        return db.execute(
            select(GenerationJob).where(GenerationJob.id == job_id)
        ).scalar_one()


def _credits(email: str) -> int:
    with SessionLocal() as db:
        return db.query(User).filter(User.email == email).one().ai_credits_remaining


def _set_credits(email: str, value: int) -> None:
    with SessionLocal() as db:
        db.query(User).filter(User.email == email).one().ai_credits_remaining = value
        db.commit()


# ----------------------------------------------------------------------
# En file d'attente : rien n'a tourné


def test_a_queued_job_stops_at_once_and_gives_everything_back(
    client, auth_headers, make_user, project_id
):
    _set_credits("user@example.com", 0)
    job_id = _make_job("user@example.com", project_id)

    response = client.post(f"/api/v1/jobs/{job_id}/cancel", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "CANCELLED"

    # Les huit crédits reviennent : aucun appel n'est parti.
    assert _credits("user@example.com") == 8
    assert _job(job_id).credits_reserved == 0
    assert make_user is not None


def test_cancelling_twice_changes_nothing_the_second_time(client, auth_headers, project_id):
    """La demande est une date, pas un compteur — sinon on rembourserait deux fois."""
    _set_credits("user@example.com", 0)
    job_id = _make_job("user@example.com", project_id)

    client.post(f"/api/v1/jobs/{job_id}/cancel", headers=auth_headers)
    assert _credits("user@example.com") == 8

    second = client.post(f"/api/v1/jobs/{job_id}/cancel", headers=auth_headers)
    assert second.status_code == 400
    assert second.json()["code"] == "job_already_finished"
    assert _credits("user@example.com") == 8


def test_a_finished_job_cannot_be_cancelled(client, auth_headers, project_id):
    job_id = _make_job("user@example.com", project_id, status=JobStatus.SUCCEEDED)
    response = client.post(f"/api/v1/jobs/{job_id}/cancel", headers=auth_headers)
    assert response.status_code == 400
    assert response.json()["code"] == "job_already_finished"


def test_a_running_job_records_the_request_without_stopping_itself(
    client, auth_headers, project_id
):
    """Elle ne s'arrête qu'entre deux passes : la route ne ment pas là-dessus."""
    job_id = _make_job("user@example.com", project_id, status=JobStatus.RUNNING)
    body = client.post(f"/api/v1/jobs/{job_id}/cancel", headers=auth_headers).json()
    assert body["status"] == "RUNNING"
    assert body["cancel_requested_at"] is not None
    # Rien n'est rendu tant qu'on ne sait pas ce qui aura tourné.
    assert _job(job_id).credits_reserved == 8


def test_another_account_cannot_cancel_a_job(client, auth_headers, make_user, project_id):
    """404 et non 403 : la réponse ne révèle pas l'existence de la tâche."""
    job_id = _make_job("user@example.com", project_id)
    other_headers, _ = make_user("intrus@example.com")
    assert client.post(
        f"/api/v1/jobs/{job_id}/cancel", headers=other_headers
    ).status_code == 404
    assert _job(job_id).status == JobStatus.QUEUED


def test_cancelling_requires_authentication(client, auth_headers, project_id):
    job_id = _make_job("user@example.com", project_id)
    assert client.post(f"/api/v1/jobs/{job_id}/cancel").status_code == 401


# ----------------------------------------------------------------------
# En cours : on rend ce qui n'a pas tourné


@pytest.mark.parametrize(
    ("done", "expected_refund"),
    [(0, 8), (1, 7), (3, 5), (8, 0)],
)
def test_only_the_untouched_units_come_back(client, auth_headers, project_id, done, expected_refund):
    from app.services.job_service import JobService

    _set_credits("user@example.com", 0)
    job_id = _make_job("user@example.com", project_id, status=JobStatus.RUNNING)

    with SessionLocal() as db:
        job = db.get(GenerationJob, job_id)
        JobService(db)._cancel(job, consumed_units=done)
        db.commit()

    assert _credits("user@example.com") == expected_refund
    assert _job(job_id).credits_reserved == 8 - expected_refund
    assert _job(job_id).status == JobStatus.CANCELLED


def test_more_steps_than_reserved_never_costs_more(client, auth_headers, project_id):
    """Une reprise dépasse les huit agents ; elle ne dépasse pas la réserve.

    Sans cette borne, une chaîne partie en boucle de correction ferait payer
    plus que ce qui a été retenu à la mise en file — c'est-à-dire plus que ce
    que l'utilisateur a accepté.
    """
    from app.services.job_service import JobService

    _set_credits("user@example.com", 0)
    job_id = _make_job("user@example.com", project_id, status=JobStatus.RUNNING)
    with SessionLocal() as db:
        JobService(db)._cancel(db.get(GenerationJob, job_id), consumed_units=16)
        db.commit()

    assert _credits("user@example.com") == 0
    assert _job(job_id).credits_reserved == 8


# ----------------------------------------------------------------------
# L'orchestrateur s'arrête entre deux agents


def test_the_chain_stops_between_two_agents_and_keeps_its_work():
    """Jamais pendant un appel : il est déjà parti, donc déjà facturé.

    Entre deux agents, l'état est celui qu'un agent vient de rendre —
    cohérent, conservable, simplement incomplet.
    """
    from app.agents.contracts import ProjectState

    seen: list[int] = []

    def stop_after_three() -> bool:
        return len(seen) >= 3

    def count(done: int, _total: int) -> None:
        seen.append(done)

    run = Orchestrator().run(
        ProjectState(project_id="p1"), on_step=count, should_stop=stop_after_three
    )
    assert run.cancelled is True
    assert len(run.outputs) == 3
    # Le travail des trois agents est là, pas jeté.
    assert all(output.analysis for output in run.outputs)


def test_an_interrupted_chain_is_never_exportable():
    """Le défaut évité : présenter comme vérifié un dossier non vérifié.

    Même si les validateurs avaient rendu un verdict favorable à un tour
    précédent, les agents suivants n'ont pas tourné sur l'état final.
    """
    from app.agents.contracts import ProjectState
    from app.models.enums import ValidationVerdict

    run = PipelineRun(state=ProjectState(project_id="p1"))
    run.verdict = ValidationVerdict.PASS
    assert run.is_exportable is True

    run.cancelled = True
    assert run.is_exportable is False


def test_an_interrupted_chain_is_neither_stalled_nor_exhausted():
    """Trois causes d'arrêt distinctes ; les confondre égarerait le diagnostic."""
    from app.agents.contracts import ProjectState

    run = Orchestrator().run(
        ProjectState(project_id="p1"), should_stop=lambda: True
    )
    assert run.cancelled is True
    assert run.stalled is False
    assert run.exhausted is False
    assert run.outputs == []


def test_without_a_stop_signal_nothing_changes():
    """La chaîne complète reste le cas courant."""
    from app.agents.contracts import ProjectState

    run = Orchestrator().run(ProjectState(project_id="p1"))
    assert run.cancelled is False
    assert len(run.outputs) >= len(AGENT_PIPELINE)


# ----------------------------------------------------------------------
# Bout en bout : le worker voit la demande et s'arrête


class _Scripted:
    """Fournisseur déterministe, qui compte ses appels."""

    name = "scripted"

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, request):
        import json

        from app.services.ai.base import AICompletionResponse

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
                    "verdict": "PASS" if role.endswith("VALIDATOR") else None,
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
    provider = _Scripted()
    monkeypatch.setattr("app.services.ai.service.build_provider", lambda *a, **k: provider)
    return provider


class _Silent:
    """File d'attente qui accepte tout sans rien exécuter.

    Sans elle, `enqueue` retombe sur l'exécution dans la requête — la tâche
    serait déjà terminée avant qu'on puisse l'annuler. Cette bascule est un
    comportement réel du produit, pas un artefact de test : **sans worker, une
    génération ne peut pas être annulée**, puisqu'elle s'achève dans l'appel
    HTTP qui l'a lancée.
    """

    available = True

    def push(self, job_id: str) -> bool:  # noqa: ARG002
        return True


def test_the_worker_honours_a_request_made_before_it_starts(
    client, auth_headers, db_session, project_id, scripted
):
    """Le chemin réel : la demande vient d'une autre session que celle du worker.

    Se fier à l'objet chargé au démarrage de la tâche reviendrait à ne jamais
    la voir arriver — c'est pour cela que le contrôle relit la base.
    """
    from app.models.project import Project
    from app.services.job_service import JobService, run_job

    user = db_session.query(User).filter(User.email == "user@example.com").one()
    job = JobService(db_session, queue=_Silent()).enqueue_agent_chain(
        user, db_session.get(Project, project_id)
    )
    job_id = job.id
    db_session.commit()

    # L'utilisateur annule pendant que la tâche attend, depuis sa requête HTTP.
    client.post(f"/api/v1/jobs/{job_id}/cancel", headers=auth_headers)

    # Le worker a sa propre session : il lit l'état écrit par l'autre.
    db_session.expire_all()
    # Une tâche annulée en file ne doit plus rien exécuter du tout.
    assert run_job(job_id, db=db_session) is JobStatus.CANCELLED
    assert scripted.calls == 0
    assert _job(job_id).credits_reserved == 0


def test_a_chain_stopped_midway_keeps_its_dossier_but_cannot_export_it(
    client, auth_headers, db_session, project_id, scripted, monkeypatch
):
    """Le travail des agents qui ont tourné est réel : on le garde.

    Mais le dossier n'a pas traversé ses validateurs sur son état final : le
    présenter comme exportable reviendrait à le dire vérifié.
    """
    from app.models.project import Project
    from app.services.dossier_service import DossierService
    from app.services.job_service import JobService, run_job

    user = db_session.query(User).filter(User.email == "user@example.com").one()
    job = JobService(db_session, queue=_Silent()).enqueue_agent_chain(
        user, db_session.get(Project, project_id)
    )
    job_id = job.id
    db_session.commit()
    before = _credits("user@example.com")

    # La demande tombe pendant l'exécution, après le troisième agent.
    original = Orchestrator._run_sequence
    state = {"steps": 0}

    def counting(self, run, sequence, *args, **kwargs):
        def stop() -> bool:
            state["steps"] = len(run.outputs)
            return len(run.outputs) >= 3

        run._should_stop = stop
        return original(self, run, sequence, *args, **kwargs)

    monkeypatch.setattr(Orchestrator, "_run_sequence", counting)

    assert run_job(job_id, db=db_session) is JobStatus.CANCELLED

    finished = _job(job_id)
    assert finished.status == JobStatus.CANCELLED
    assert finished.result["cancelled"] is True
    assert finished.result["exportable"] is False

    # Trois agents ont tourné : trois crédits retenus, cinq rendus.
    assert finished.credits_reserved == 3
    assert _credits("user@example.com") == before + 5

    # Et le dossier partiel est bien en base.
    run = DossierService(db_session).load_state(project_id)
    assert run is not None


# ----------------------------------------------------------------------
# Le worker reste visible pendant qu'il travaille


def test_the_worker_keeps_beating_while_a_job_runs(monkeypatch):
    """Le défaut corrigé : un worker occupé passait pour un worker mort.

    Le battement n'était publié qu'entre deux tâches, avec un TTL de 30 s.
    Une chaîne de seize appels dure bien plus : l'API cessait de voir le
    worker et se remettait à générer dans la requête HTTP — ce que la file
    existe pour éviter, et exactement quand elle est sollicitée.
    """
    import time

    from app.workers import runner as runner_module

    beats: list[float] = []

    class Counting:
        client = object()

        def heartbeat(self, ttl: int) -> None:  # noqa: ARG002
            beats.append(time.monotonic())

    monkeypatch.setattr(runner_module, "HEARTBEAT_INTERVAL_SECONDS", 0.05)
    # Une tâche qui dure nettement plus qu'un intervalle de battement.
    monkeypatch.setattr(runner_module, "run_job", lambda job_id: time.sleep(0.4))

    worker = runner_module.Worker(queue=Counting())
    worker._execute("une-tache")

    # Plusieurs battements pendant l'exécution, et non un seul avant.
    assert len(beats) >= 3, beats


def test_the_heartbeat_thread_stops_with_the_job(monkeypatch):
    """Un fil qui survivrait à sa tâche maintiendrait un worker mort en vie."""
    import time

    from app.workers import runner as runner_module

    beats: list[int] = []

    class Counting:
        client = object()

        def heartbeat(self, ttl: int) -> None:  # noqa: ARG002
            beats.append(1)

    monkeypatch.setattr(runner_module, "HEARTBEAT_INTERVAL_SECONDS", 0.05)
    monkeypatch.setattr(runner_module, "run_job", lambda job_id: None)

    runner_module.Worker(queue=Counting())._execute("une-tache")
    after = len(beats)
    time.sleep(0.3)
    assert len(beats) == after


def test_a_crashing_job_still_stops_the_heartbeat(monkeypatch):
    """Sinon une tâche en échec laisserait un fil derrière elle, à chaque fois."""
    import time

    from app.workers import runner as runner_module

    beats: list[int] = []

    class Counting:
        client = object()

        def heartbeat(self, ttl: int) -> None:  # noqa: ARG002
            beats.append(1)

    def boom(job_id: str) -> None:  # noqa: ARG001
        raise RuntimeError("échec inattendu")

    monkeypatch.setattr(runner_module, "HEARTBEAT_INTERVAL_SECONDS", 0.05)
    monkeypatch.setattr(runner_module, "run_job", boom)

    runner_module.Worker(queue=Counting())._execute("une-tache")
    after = len(beats)
    time.sleep(0.3)
    assert len(beats) == after
