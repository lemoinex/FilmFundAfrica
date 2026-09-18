"""Tests de la génération asynchrone.

Le défaut corrigé ici : la génération s'exécutait dans la requête HTTP. Un
scénario de 110 pages enchaîne plusieurs appels au fournisseur et tenait la
requête ouverte plusieurs minutes — jusqu'à l'expiration côté proxy ou
navigateur.

Deux propriétés portent le reste et sont testées en priorité : les crédits
sont réservés à la mise en file (sinon on empile des tâches au-delà de son
quota), et aucune tâche n'est perdue (la base est la source de vérité, pas la
file Redis).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.errors import AIProviderError
from app.models.enums import JobStatus
from app.models.jobs import GenerationJob
from app.models.user import User
from app.services.job_service import JobService, run_job
from tests.conftest import job_result


# ---------------------------------------------------------------------------
# Fausse file : un worker est déclaré disponible, rien ne s'exécute tout seul
# ---------------------------------------------------------------------------
class FakeQueue:
    """File qui accepte les tâches sans jamais les exécuter.

    Elle tient le rôle du couple Redis + worker : ce que l'API dépose reste en
    attente jusqu'à ce que le test appelle `run_job` lui-même.
    """

    def __init__(self, *, available: bool = True, accepts: bool = True) -> None:
        self._available = available
        self._accepts = accepts
        self.pushed: list[str] = []

    @property
    def available(self) -> bool:
        return self._available

    def push(self, job_id: str) -> bool:
        if not self._accepts:
            return False
        self.pushed.append(job_id)
        return True


@pytest.fixture
def queued(monkeypatch):
    """Branche une fausse file sur l'API et la renvoie."""
    queue = FakeQueue()
    monkeypatch.setattr("app.services.job_service.job_queue", queue)
    return queue


def _generate(client, headers, project_id, document_type="SHORT_SYNOPSIS", **payload):
    body = {"language": "fr", "overwrite": True}
    body.update(payload)
    return client.post(
        f"/api/v1/projects/{project_id}/documents/{document_type}/generate",
        json=body,
        headers=headers,
    )


def _credits(db_session, email: str) -> int:
    db_session.expire_all()
    user = db_session.query(User).filter(User.email == email).one()
    return user.ai_credits_remaining


# ---------------------------------------------------------------------------
# Contrat de l'API
# ---------------------------------------------------------------------------
def test_generation_returns_an_accepted_job(client, auth_headers, project, queued):
    response = _generate(client, auth_headers, project["id"])

    assert response.status_code == 202, response.text
    job = response.json()
    assert job["status"] == "QUEUED"
    assert job["result"] is None
    assert job["total_passes"] == 1
    assert queued.pushed == [job["id"]]


def test_the_job_carries_its_result_once_executed(client, auth_headers, project, queued):
    job_id = _generate(client, auth_headers, project["id"]).json()["id"]

    assert run_job(job_id) == JobStatus.SUCCEEDED

    job = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers).json()
    assert job["status"] == "SUCCEEDED"
    assert job["completed_passes"] == job["total_passes"]
    assert job["result"]["document"]["current_version"] == 1
    assert job["document_id"] == job["result"]["document"]["id"]
    assert job["finished_at"] is not None


def test_a_job_belongs_to_its_owner_alone(client, make_user, queued):
    alice, _ = make_user("alice.jobs@example.com", plan="PRO_AUTHOR")
    bob, _ = make_user("bob.jobs@example.com", plan="PRO_AUTHOR")
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Projet d'Alice", "project_type": "DOCUMENTARY"},
        headers=alice,
    ).json()["id"]
    job_id = _generate(client, alice, project_id).json()["id"]

    # 404 et non 403 : la réponse ne révèle pas que la tâche existe.
    assert client.get(f"/api/v1/jobs/{job_id}", headers=bob).status_code == 404
    assert client.get(f"/api/v1/jobs/{job_id}", headers=alice).status_code == 200


def test_project_history_lists_recent_jobs(client, auth_headers, project, queued):
    _generate(client, auth_headers, project["id"])
    _generate(client, auth_headers, project["id"], document_type="INTENT_NOTE")

    jobs = client.get(
        f"/api/v1/projects/{project['id']}/jobs", headers=auth_headers
    ).json()
    assert len(jobs) == 2
    assert {job["document_type"] for job in jobs} == {"SHORT_SYNOPSIS", "INTENT_NOTE"}


def test_predictable_refusals_answer_immediately(client, auth_headers, project, queued):
    """Un refus prévisible ne doit pas devenir une tâche qui échoue plus tard."""
    run_job(_generate(client, auth_headers, project["id"]).json()["id"])
    blocked = _generate(client, auth_headers, project["id"], overwrite=False)

    assert blocked.status_code == 400
    assert blocked.json()["code"] == "document_exists"
    # Rien n'a été mis en file pour cette demande.
    assert len(queued.pushed) == 1


# ---------------------------------------------------------------------------
# Crédits : réservés à la mise en file
# ---------------------------------------------------------------------------
def test_queued_jobs_cannot_exceed_the_credit_quota(client, make_user, queued):
    """Le défaut qu'évite la réserve : empiler des tâches avec un seul crédit.

    Sans débit à la mise en file, aucune des tâches en attente n'aurait encore
    rien consommé au moment où la suivante est demandée.
    """
    headers, _ = make_user("quota.jobs@example.com")  # plan FREE : 1 crédit
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Projet test", "project_type": "DOCUMENTARY"},
        headers=headers,
    ).json()["id"]

    first = _generate(client, headers, project_id)
    assert first.status_code == 202
    assert first.json()["credits_reserved"] == 1

    second = _generate(client, headers, project_id)
    assert second.status_code == 402
    assert second.json()["code"] == "ai_credits_exhausted"
    assert len(queued.pushed) == 1


def test_a_successful_job_debits_once(client, make_user, db_session, queued):
    headers, _ = make_user("debit.once@example.com", plan="PRO_AUTHOR")
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Projet test", "project_type": "DOCUMENTARY"},
        headers=headers,
    ).json()["id"]

    before = _credits(db_session, "debit.once@example.com")
    job_id = _generate(client, headers, project_id).json()["id"]
    assert _credits(db_session, "debit.once@example.com") == before - 1

    run_job(job_id)
    # L'exécution ne débite pas une seconde fois ce qui a été réservé.
    assert _credits(db_session, "debit.once@example.com") == before - 1


def test_a_failed_job_gives_the_credits_back(
    client, make_user, db_session, queued, monkeypatch
):
    headers, _ = make_user("panne@example.com", plan="PRO_AUTHOR")
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Projet test", "project_type": "DOCUMENTARY"},
        headers=headers,
    ).json()["id"]

    before = _credits(db_session, "panne@example.com")
    job_id = _generate(client, headers, project_id).json()["id"]

    def _fails(*_args, **_kwargs):
        raise AIProviderError("Le fournisseur d'IA est injoignable.")

    monkeypatch.setattr("app.services.ai.service.AIService.run", _fails)
    assert run_job(job_id) == JobStatus.FAILED

    job = client.get(f"/api/v1/jobs/{job_id}", headers=headers).json()
    assert job["status"] == "FAILED"
    assert job["error_code"] == "ai_provider_error"
    assert job["error_message"]
    # Une génération qui n'a rien produit ne coûte rien.
    assert _credits(db_session, "panne@example.com") == before


# ---------------------------------------------------------------------------
# Avancement d'un scénario long
# ---------------------------------------------------------------------------
def test_a_long_screenplay_is_queued_with_its_pass_count(client, make_user, queued):
    headers, _ = make_user("scenario@example.com", plan="PRODUCER")
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Long métrage", "project_type": "FEATURE_FILM", "duration": 110},
        headers=headers,
    ).json()["id"]

    job = _generate(
        client, headers, project_id, document_type="SCREENPLAY", target_duration_minutes=110
    ).json()

    assert job["total_passes"] > 1
    assert job["completed_passes"] == 0
    # Le coût annoncé est celui qui a été retenu.
    assert job["credits_reserved"] == job["total_passes"]


def test_progress_is_published_pass_after_pass(
    client, make_user, db_session, queued, monkeypatch
):
    """Sans cela, l'utilisateur regarde un écran figé pendant plusieurs minutes."""
    from app.services.ai.service import AIService

    headers, _ = make_user("progression@example.com", plan="PRODUCER")
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Long métrage", "project_type": "FEATURE_FILM", "duration": 110},
        headers=headers,
    ).json()["id"]
    job_id = _generate(
        client, headers, project_id, document_type="SCREENPLAY", target_duration_minutes=110
    ).json()["id"]

    # Avant chaque appel au fournisseur, on relit l'avancement depuis une
    # session indépendante : c'est exactement ce que voit le frontend.
    published: list[int] = []
    real_run = AIService.run

    def _observe(self, prompt):
        db_session.expire_all()
        published.append(db_session.get(GenerationJob, job_id).completed_passes)
        return real_run(self, prompt)

    monkeypatch.setattr(AIService, "run", _observe)
    assert run_job(job_id) == JobStatus.SUCCEEDED

    # Une passe écrite, une progression visible : 0 avant la première, puis 1, 2…
    assert len(published) > 1, "un scénario long s'écrit en plusieurs passes"
    assert published == list(range(len(published)))

    db_session.expire_all()
    job = db_session.get(GenerationJob, job_id)
    assert job.completed_passes == job.total_passes


# ---------------------------------------------------------------------------
# Reprise : aucune tâche perdue
# ---------------------------------------------------------------------------
def test_a_queued_job_whose_signal_was_lost_is_recovered(
    client, auth_headers, project, db_session, queued
):
    """Redis vidé, worker redémarré : la tâche est en base, le balayage la voit."""
    job_id = _generate(client, auth_headers, project["id"]).json()["id"]

    service = JobService(db_session, queue=queued)
    assert job_id not in service.stale_queued_ids()  # trop récente

    job = db_session.get(GenerationJob, job_id)
    job.created_at = datetime.now(UTC) - timedelta(minutes=5)
    db_session.commit()

    assert job_id in service.stale_queued_ids()
    assert run_job(job_id) == JobStatus.SUCCEEDED


def test_an_interrupted_job_fails_and_refunds(
    client, make_user, db_session, queued
):
    """Worker disparu en cours d'exécution : la tâche ne doit pas rester RUNNING."""
    headers, _ = make_user("interrompu@example.com", plan="PRO_AUTHOR")
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Projet test", "project_type": "DOCUMENTARY"},
        headers=headers,
    ).json()["id"]
    job_id = _generate(client, headers, project_id).json()["id"]
    after_reservation = _credits(db_session, "interrompu@example.com")

    job = db_session.get(GenerationJob, job_id)
    job.status = JobStatus.RUNNING
    job.started_at = datetime.now(UTC) - timedelta(hours=2)
    db_session.commit()

    assert JobService(db_session, queue=queued).fail_timed_out() == 1

    db_session.expire_all()
    job = db_session.get(GenerationJob, job_id)
    assert job.status == JobStatus.FAILED
    assert job.error_code == "job_interrupted"
    assert _credits(db_session, "interrompu@example.com") == after_reservation + 1


def test_an_already_running_job_is_not_executed_twice(client, auth_headers, project, queued):
    """Deux workers peuvent recevoir le même identifiant : un seul doit l'exécuter."""
    job_id = _generate(client, auth_headers, project["id"]).json()["id"]

    assert run_job(job_id) == JobStatus.SUCCEEDED
    # Le second passage ne régénère rien et ne redébite rien.
    assert run_job(job_id) == JobStatus.SUCCEEDED

    versions = client.get(
        f"/api/v1/projects/{project['id']}/documents", headers=auth_headers
    ).json()
    assert versions[0]["current_version"] == 1


# ---------------------------------------------------------------------------
# Repli : pas de worker, pas de file
# ---------------------------------------------------------------------------
def test_without_a_worker_the_api_generates_itself(client, auth_headers, project, monkeypatch):
    """Une file que personne ne lit vaudrait une génération qui n'arrive jamais."""
    monkeypatch.setattr(
        "app.services.job_service.job_queue", FakeQueue(available=False)
    )
    response = _generate(client, auth_headers, project["id"])

    assert response.status_code == 202
    assert job_result(response)["document"]["current_version"] == 1


def test_a_queue_that_refuses_the_job_falls_back_to_inline(
    client, auth_headers, project, monkeypatch
):
    """Redis tombe entre le contrôle et le dépôt : la demande aboutit quand même."""
    monkeypatch.setattr(
        "app.services.job_service.job_queue", FakeQueue(available=True, accepts=False)
    )
    response = _generate(client, auth_headers, project["id"])

    assert response.status_code == 202
    assert response.json()["status"] == "SUCCEEDED"
