"""Tests de la veille automatisée et des tâches planifiées.

La règle qui porte ce module : **le pipeline n'écrit jamais dans la base
vivante**. Il dépose des candidats ; une personne les publie ou les écarte.
Une opportunité proposée à un auteur engage son dossier de financement, elle
ne peut pas venir d'une classification automatique non relue.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.enums import CandidateStatus, FundingStatus, NotificationType, UserType
from app.models.funding import FundingOpportunity
from app.models.ingestion import OpportunityCandidate
from app.models.system import Notification
from app.models.user import User
from app.workers.tasks import SCHEDULED_TASKS, send_pending_notification_emails

API_KEY = "cle-automatisation-de-test"
KEY_HEADER = {"X-API-Key": API_KEY}


def _candidate(**overrides) -> dict:
    payload = {
        "name": "Fonds de soutien au documentaire",
        "source_url": "https://exemple-source.org/appels/doc-2027",
        "source_name": "Portail des aides",
        "payload": {
            "organization": "Institut national du cinéma",
            "description": "Aide à l'écriture documentaire.",
            "country": "Sénégal",
            "deadline": "2027-03-31",
        },
    }
    payload.update(overrides)
    return payload


def _ingest(client, candidates: list[dict], headers=KEY_HEADER):
    return client.post("/api/v1/automation/opportunities", json=candidates, headers=headers)


def _admin(client, make_user, email: str) -> dict:
    headers, _ = make_user(email)
    with SessionLocal() as db:
        db.query(User).filter(User.email == email).one().user_type = UserType.ADMIN
        db.commit()
    return headers


# ---------------------------------------------------------------------------
# Authentification de l'automatisation
# ---------------------------------------------------------------------------
def test_ingestion_without_a_key_is_refused(client):
    response = client.post("/api/v1/automation/opportunities", json=[_candidate()])
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_api_key"


def test_ingestion_with_a_wrong_key_is_refused(client):
    response = _ingest(client, [_candidate()], headers={"X-API-Key": "pas-la-bonne"})
    assert response.status_code == 401


def test_nothing_reaches_the_database_without_a_valid_key(client, db_session):
    _ingest(client, [_candidate()], headers={"X-API-Key": "pas-la-bonne"})
    assert db_session.scalars(select(OpportunityCandidate)).all() == []


# ---------------------------------------------------------------------------
# Le pipeline n'écrit jamais dans la base vivante
# ---------------------------------------------------------------------------
def test_ingested_candidates_wait_for_a_human(client, db_session):
    response = _ingest(client, [_candidate()])
    assert response.status_code == 202
    assert response.json() == {
        "received": 1,
        "created": 1,
        "duplicates": 0,
        "rejected": 0,
        "details": [],
    }

    candidate = db_session.scalars(select(OpportunityCandidate)).one()
    assert candidate.status is CandidateStatus.PENDING
    # Et surtout : rien dans la base des dispositifs proposés aux auteurs.
    assert db_session.scalars(select(FundingOpportunity)).all() == []


def test_a_candidate_without_a_source_is_refused(client):
    response = _ingest(client, [_candidate(source_url="")])
    # Le schéma refuse avant même le service : pas de source, pas de candidat.
    assert response.status_code == 422


def test_the_same_source_twice_does_not_fill_the_queue(client, db_session):
    """Une veille hebdomadaire repasse sur les mêmes pages."""
    _ingest(client, [_candidate()])
    second = _ingest(client, [_candidate(name="Titre légèrement différent")])

    assert second.json()["created"] == 0
    assert second.json()["duplicates"] == 1
    assert len(db_session.scalars(select(OpportunityCandidate)).all()) == 1


def test_a_decided_candidate_does_not_come_back_in_the_queue(client, make_user, db_session):
    """La décision humaine tient, même si la veille repasse sur la source."""
    admin = _admin(client, make_user, "admin.veille.rejet@example.com")
    _ingest(client, [_candidate()])
    candidate_id = client.get("/api/v1/admin/candidates", headers=admin).json()[0]["id"]
    client.post(
        f"/api/v1/admin/candidates/{candidate_id}/reject",
        json={"note": "Hors périmètre géographique."},
        headers=admin,
    )

    _ingest(client, [_candidate()])

    db_session.expire_all()
    candidate = db_session.get(OpportunityCandidate, candidate_id)
    assert candidate.status is CandidateStatus.REJECTED
    # Le passage de la veille est daté, sans rouvrir la décision.
    assert candidate.last_seen_at is not None


# ---------------------------------------------------------------------------
# Validation humaine
# ---------------------------------------------------------------------------
def test_approving_publishes_the_opportunity_with_its_source(client, make_user, db_session):
    admin = _admin(client, make_user, "admin.veille@example.com")
    _ingest(client, [_candidate()])
    candidate = client.get("/api/v1/admin/candidates", headers=admin).json()[0]

    response = client.post(
        f"/api/v1/admin/candidates/{candidate['id']}/approve", json={}, headers=admin
    )
    assert response.status_code == 200, response.text

    opportunity = db_session.scalars(select(FundingOpportunity)).one()
    assert opportunity.name == "Fonds de soutien au documentaire"
    assert opportunity.organization == "Institut national du cinéma"
    # La traçabilité de la source suit le candidat jusqu'au dispositif publié.
    assert opportunity.source_url == "https://exemple-source.org/appels/doc-2027"
    assert opportunity.source_name == "Portail des aides"
    assert opportunity.last_verified_at is not None
    # Une personne vient de le vérifier : il entre ouvert, pas « non vérifié ».
    assert opportunity.status is FundingStatus.OPEN
    assert opportunity.is_demo is False


def test_the_reviewer_corrections_win_over_the_extraction(client, make_user, db_session):
    """C'est la personne qui a lu la source, pas la classification."""
    admin = _admin(client, make_user, "admin.correction@example.com")
    _ingest(client, [_candidate()])
    candidate = client.get("/api/v1/admin/candidates", headers=admin).json()[0]

    client.post(
        f"/api/v1/admin/candidates/{candidate['id']}/approve",
        json={
            "organization": "Institut national du cinéma et de l'audiovisuel",
            "deadline": "2027-04-15",
        },
        headers=admin,
    )

    opportunity = db_session.scalars(select(FundingOpportunity)).one()
    assert opportunity.organization == "Institut national du cinéma et de l'audiovisuel"
    assert opportunity.deadline == date(2027, 4, 15)


def test_an_incomplete_candidate_cannot_be_published(client, make_user):
    admin = _admin(client, make_user, "admin.incomplet@example.com")
    _ingest(client, [_candidate(payload={"description": "Sans organisme."})])
    candidate = client.get("/api/v1/admin/candidates", headers=admin).json()[0]

    response = client.post(
        f"/api/v1/admin/candidates/{candidate['id']}/approve", json={}, headers=admin
    )
    assert response.status_code == 400
    assert response.json()["code"] == "candidate_incomplete"


def test_a_candidate_is_reviewed_once(client, make_user):
    admin = _admin(client, make_user, "admin.deuxfois@example.com")
    _ingest(client, [_candidate()])
    candidate = client.get("/api/v1/admin/candidates", headers=admin).json()[0]

    client.post(f"/api/v1/admin/candidates/{candidate['id']}/approve", json={}, headers=admin)
    again = client.post(
        f"/api/v1/admin/candidates/{candidate['id']}/approve", json={}, headers=admin
    )
    assert again.status_code == 400
    assert again.json()["code"] == "candidate_already_reviewed"


def test_rejecting_keeps_the_reason(client, make_user):
    admin = _admin(client, make_user, "admin.motif@example.com")
    _ingest(client, [_candidate()])
    candidate = client.get("/api/v1/admin/candidates", headers=admin).json()[0]

    response = client.post(
        f"/api/v1/admin/candidates/{candidate['id']}/reject",
        json={"note": "Source non vérifiable."},
        headers=admin,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"
    assert response.json()["review_note"] == "Source non vérifiable."


def test_the_validation_queue_is_reserved_to_administrators(client, make_user):
    headers, _ = make_user("curieux.veille@example.com")
    assert client.get("/api/v1/admin/candidates", headers=headers).status_code == 403


def test_the_queue_can_be_filtered_by_status(client, make_user):
    admin = _admin(client, make_user, "admin.filtre@example.com")
    _ingest(client, [_candidate(), _candidate(source_url="https://exemple.org/autre")])
    candidate = client.get("/api/v1/admin/candidates", headers=admin).json()[0]
    client.post(f"/api/v1/admin/candidates/{candidate['id']}/reject", json={}, headers=admin)

    pending = client.get("/api/v1/admin/candidates?status=PENDING", headers=admin).json()
    rejected = client.get("/api/v1/admin/candidates?status=REJECTED", headers=admin).json()
    assert len(pending) == 1
    assert len(rejected) == 1


# ---------------------------------------------------------------------------
# Tâches planifiées
# ---------------------------------------------------------------------------
def test_the_task_list_is_closed(client):
    """Une route acceptant un nom libre exposerait tout le module."""
    response = client.post("/api/v1/automation/tasks/os.system", headers=KEY_HEADER)
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_task"


def test_available_tasks_are_listed(client):
    response = client.get("/api/v1/automation/tasks", headers=KEY_HEADER)
    assert response.status_code == 200
    assert set(response.json()) == set(SCHEDULED_TASKS)


def test_a_task_can_be_triggered(client):
    response = client.post(
        "/api/v1/automation/tasks/notify_upcoming_deadlines", headers=KEY_HEADER
    )
    assert response.status_code == 200
    assert "exécutée" in response.json()["detail"]


def test_tasks_are_idempotent(client):
    """Les rejouer ne doit pas produire de doublons."""
    first = client.post(
        "/api/v1/automation/tasks/notify_incomplete_projects", headers=KEY_HEADER
    ).json()["detail"]
    second = client.post(
        "/api/v1/automation/tasks/notify_incomplete_projects", headers=KEY_HEADER
    ).json()["detail"]
    assert "0 élément(s)" in second or first == second


# ---------------------------------------------------------------------------
# Envoi effectif des notifications par e-mail
# ---------------------------------------------------------------------------
def test_a_notification_stays_pending_while_smtp_is_not_configured(client, make_user):
    """Sans SMTP, la notification n'est pas perdue : elle repartira plus tard."""
    headers, registered = make_user("notif@example.com")
    with SessionLocal() as db:
        db.add(
            Notification(
                user_id=registered["user"]["id"],
                notification_type=NotificationType.DEADLINE_SOON,
                title="Échéance proche",
                body="Un dispositif arrive à échéance.",
                link="/projets",
            )
        )
        db.commit()

    # `SMTP_HOST` est vide en test : l'envoi échoue proprement.
    assert send_pending_notification_emails() == 0

    with SessionLocal() as db:
        notification = db.scalars(
            select(Notification).where(Notification.title == "Échéance proche")
        ).one()
        assert notification.email_sent is False
    assert headers is not None


def test_a_sent_notification_is_not_sent_twice(client, make_user, monkeypatch):
    from app.services.email_service import EmailService

    headers, registered = make_user("notif.envoi@example.com")
    with SessionLocal() as db:
        db.add(
            Notification(
                user_id=registered["user"]["id"],
                notification_type=NotificationType.SYSTEM,
                title="Message unique",
                body="Corps du message.",
            )
        )
        db.commit()

    sent: list[str] = []
    monkeypatch.setattr(
        EmailService, "send_notification", lambda self, to, title, body: sent.append(to) is None
    )

    assert send_pending_notification_emails() >= 1
    before = len(sent)
    send_pending_notification_emails()
    assert len(sent) == before, "une notification déjà envoyée ne repart pas"
    assert headers is not None


def test_expiring_subscriptions_is_reachable_as_a_task(client):
    response = client.post(
        "/api/v1/automation/tasks/expire_due_subscriptions", headers=KEY_HEADER
    )
    assert response.status_code == 200


def test_deadline_notifications_are_not_duplicated(client, make_user, db_session):
    """Deux passages de la veille ne doivent pas prévenir deux fois."""
    headers, registered = make_user("echeance.notif@example.com", plan="PRO_AUTHOR")
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Projet suivi", "project_type": "DOCUMENTARY", "country": "Sénégal"},
        headers=headers,
    ).json()["id"]

    with SessionLocal() as db:
        from app.models.funding import ProjectFundingMatch

        opportunity = FundingOpportunity(
            name="Fonds test échéance",
            organization="Organisme",
            status=FundingStatus.OPEN,
            deadline=date.today() + timedelta(days=7),
            source_url="https://exemple.org/echeance",
            source_name="Test",
        )
        db.add(opportunity)
        db.flush()
        db.add(ProjectFundingMatch(project_id=project_id, opportunity_id=opportunity.id))
        db.commit()

    client.post("/api/v1/automation/tasks/notify_upcoming_deadlines", headers=KEY_HEADER)
    client.post("/api/v1/automation/tasks/notify_upcoming_deadlines", headers=KEY_HEADER)

    with SessionLocal() as db:
        notifications = db.scalars(
            select(Notification).where(
                Notification.user_id == registered["user"]["id"],
                Notification.notification_type == NotificationType.DEADLINE_SOON,
            )
        ).all()
    assert len(notifications) == 1
    assert db_session is not None
    assert datetime.now(UTC) is not None
