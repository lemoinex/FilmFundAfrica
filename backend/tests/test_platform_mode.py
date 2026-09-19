"""Cycle de vie de la plateforme : bêta interne, puis ouverture commerciale.

Deux risques, opposés, et ces tests existent pour les tenir écartés tous les
deux. Le premier : que la bêta interne devienne une porte dérobée — un mode
où l'on ne vérifie plus rien, où un utilisateur ordinaire passe sans payer,
où quelqu'un se hisse administrateur. Le second : que l'ouverture commerciale
soit un mirage — des règles d'offre qu'on croit éprouvées alors qu'elles
n'ont jamais été opposées à personne.

Seule la **contrainte commerciale** se lève, et seulement pour les
administrateurs, et seulement en mode interne.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.core.platform import commercial_rules_apply, platform_status
from app.models.enums import UserType
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
def internal(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.platform_mode", "internal")


@pytest.fixture
def public(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.platform_mode", "public")


def _promote(email: str) -> None:
    with SessionLocal() as db:
        db.query(User).filter(User.email == email).one().user_type = UserType.ADMIN
        db.commit()


@pytest.fixture
def admin(client: TestClient, make_user):
    """Administrateur sur l'offre gratuite : 1 projet, 1 crédit, pas d'export."""
    headers, data = make_user("admin.mode@example.com")
    _promote("admin.mode@example.com")
    return headers, data


def _drain_credits(email: str) -> None:
    with SessionLocal() as db:
        db.query(User).filter(User.email == email).one().ai_credits_remaining = 0
        db.commit()


def _credits(client: TestClient, headers: dict) -> int:
    return client.get("/api/v1/auth/me", headers=headers).json()["ai_credits_remaining"]


# ----------------------------------------------------------------------
# Mode interne : l'équipe éprouve le produit


def test_an_administrator_is_not_held_to_the_project_quota(client, admin, internal):
    """L'offre gratuite s'arrête à un projet. L'équipe n'achète pas d'abonnement."""
    headers, _ = admin
    for index in range(3):
        response = client.post(
            "/api/v1/projects", json={**PROJECT, "title": f"Projet {index}"}, headers=headers
        )
        assert response.status_code == 201, response.text


def test_an_administrator_with_no_credits_left_can_still_generate(client, admin, internal):
    headers, _ = admin
    project_id = client.post("/api/v1/projects", json=PROJECT, headers=headers).json()["id"]
    _drain_credits("admin.mode@example.com")

    response = client.post(
        f"/api/v1/projects/{project_id}/documents/SHORT_SYNOPSIS/generate",
        json={"language": "fr"},
        headers=headers,
    )
    assert response.status_code in (200, 201, 202), response.text


def test_an_administrator_is_never_billed_and_never_credited(client, admin, internal):
    """Le défaut évité : lever le refus sans lever le débit crée de la monnaie.

    Solde 1, réserve 8 → le débit se borne à 0 ; un échec rembourse alors 8,
    et le compte sort de l'opération plus riche qu'il n'y est entré. En mode
    interne, un administrateur ne réserve rien du tout.
    """
    headers, _ = admin
    before = _credits(client, headers)
    project_id = client.post("/api/v1/projects", json=PROJECT, headers=headers).json()["id"]
    client.post(
        f"/api/v1/projects/{project_id}/documents/SHORT_SYNOPSIS/generate",
        json={"language": "fr"},
        headers=headers,
    )
    assert _credits(client, headers) == before


def test_the_usage_ledger_still_records_every_call(client, admin, internal):
    """Sans registre, personne ne saurait ce que coûte la phase interne."""
    headers, _ = admin
    project_id = client.post("/api/v1/projects", json=PROJECT, headers=headers).json()["id"]
    client.post(
        f"/api/v1/projects/{project_id}/documents/SHORT_SYNOPSIS/generate",
        json={"language": "fr"},
        headers=headers,
    )
    stats = client.get("/api/v1/admin/stats/ai", headers=headers).json()
    assert stats["calls"] >= 1
    # L'appel est journalisé, mais il n'est facturé à personne.
    assert stats["credits_consumed"] == 0


def test_an_administrator_can_export_without_a_paid_plan(client, admin, internal):
    headers, _ = admin
    project_id = client.post("/api/v1/projects", json=PROJECT, headers=headers).json()["id"]
    client.post(
        f"/api/v1/projects/{project_id}/documents/SHORT_SYNOPSIS/generate",
        json={"language": "fr"},
        headers=headers,
    )
    response = client.get(f"/api/v1/projects/{project_id}/export/pdf", headers=headers)
    assert response.status_code == 200, response.text


# ----------------------------------------------------------------------
# Mode interne : ce qui ne change pas


def test_an_ordinary_user_keeps_the_commercial_rules(client, make_user, internal):
    """La bêta interne n'est pas une phase gratuite pour le public."""
    headers, _ = make_user("ordinaire@example.com")
    client.post("/api/v1/projects", json=PROJECT, headers=headers)
    response = client.post(
        "/api/v1/projects", json={**PROJECT, "title": "Deuxième"}, headers=headers
    )
    assert response.status_code == 402
    assert response.json()["code"] == "project_quota_exceeded"


def test_an_ordinary_user_is_still_refused_the_export(client, make_user, internal):
    headers, _ = make_user("sans.export@example.com")
    project_id = client.post("/api/v1/projects", json=PROJECT, headers=headers).json()["id"]
    client.post(
        f"/api/v1/projects/{project_id}/documents/SHORT_SYNOPSIS/generate",
        json={"language": "fr"},
        headers=headers,
    )
    response = client.get(f"/api/v1/projects/{project_id}/export/pdf", headers=headers)
    assert response.status_code == 402
    assert response.json()["code"] == "export_not_included"


def test_authentication_is_still_required(client, internal):
    """« Interne » ne veut pas dire « ouvert »."""
    assert client.get("/api/v1/projects").status_code == 401
    assert client.post("/api/v1/projects", json=PROJECT).status_code == 401
    assert client.get("/api/v1/admin/platform").status_code == 401


def test_an_ordinary_user_cannot_reach_the_admin_routes(client, auth_headers, internal):
    assert client.get("/api/v1/admin/platform", headers=auth_headers).status_code == 403
    assert client.get("/api/v1/admin/users", headers=auth_headers).status_code == 403


def test_an_ordinary_user_cannot_make_themselves_an_administrator(
    client, make_user, internal
):
    headers, data = make_user("ambitieux@example.com")
    user_id = data["user"]["id"]
    for payload in ({"user_type": "ADMIN"}, {"is_active": True, "user_type": "ADMIN"}):
        assert client.put(
            f"/api/v1/admin/users/{user_id}", json=payload, headers=headers
        ).status_code == 403
    assert client.get("/api/v1/auth/me", headers=headers).json()["user_type"] != "ADMIN"


def test_ownership_is_still_enforced_between_two_administrators(client, make_user, internal):
    """Le mode interne lève la facturation, pas la cloison entre comptes."""
    owner_headers, _ = make_user("proprietaire@example.com")
    _promote("proprietaire@example.com")
    project_id = client.post(
        "/api/v1/projects", json=PROJECT, headers=owner_headers
    ).json()["id"]

    other_headers, _ = make_user("autre.admin@example.com")
    _promote("autre.admin@example.com")
    assert client.get(
        f"/api/v1/projects/{project_id}", headers=other_headers
    ).status_code == 404


# ----------------------------------------------------------------------
# Mode public : les règles d'offre s'appliquent


def test_in_public_mode_an_administrator_is_held_to_the_quota(client, admin, public):
    """Sinon les règles commerciales seraient réputées éprouvées sans l'être."""
    headers, _ = admin
    client.post("/api/v1/projects", json=PROJECT, headers=headers)
    response = client.post(
        "/api/v1/projects", json={**PROJECT, "title": "Deuxième"}, headers=headers
    )
    assert response.status_code == 402
    assert response.json()["code"] == "project_quota_exceeded"


def test_in_public_mode_an_exhausted_balance_blocks_an_administrator(client, admin, public):
    headers, _ = admin
    project_id = client.post("/api/v1/projects", json=PROJECT, headers=headers).json()["id"]
    _drain_credits("admin.mode@example.com")
    response = client.post(
        f"/api/v1/projects/{project_id}/documents/SHORT_SYNOPSIS/generate",
        json={"language": "fr"},
        headers=headers,
    )
    assert response.status_code == 402
    assert response.json()["code"] == "ai_credits_exhausted"


def test_in_public_mode_a_paid_plan_still_works(client, make_user, public):
    headers, _ = make_user("pro.mode@example.com", plan="PRO_AUTHOR")
    project_id = client.post("/api/v1/projects", json=PROJECT, headers=headers).json()["id"]
    client.post(
        f"/api/v1/projects/{project_id}/documents/SHORT_SYNOPSIS/generate",
        json={"language": "fr"},
        headers=headers,
    )
    assert client.get(
        f"/api/v1/projects/{project_id}/export/pdf", headers=headers
    ).status_code == 200


def test_switching_back_to_internal_restores_the_exemption(client, admin, monkeypatch):
    """Le retour arrière doit être immédiat et sans migration."""
    headers, _ = admin
    monkeypatch.setattr("app.core.config.settings.platform_mode", "public")
    client.post("/api/v1/projects", json=PROJECT, headers=headers)
    assert client.post(
        "/api/v1/projects", json={**PROJECT, "title": "Deuxième"}, headers=headers
    ).status_code == 402

    monkeypatch.setattr("app.core.config.settings.platform_mode", "internal")
    assert client.post(
        "/api/v1/projects", json={**PROJECT, "title": "Troisième"}, headers=headers
    ).status_code == 201


def test_the_profile_says_whether_the_rules_apply(client, admin, make_user, internal):
    """L'interface en a besoin pour ne pas annoncer « 0 crédit » à tort.

    Avant la bêta interne, un solde à zéro voulait dire « bloqué ». Pour un
    administrateur exempté, ce n'est plus vrai — et afficher le chiffre
    laisserait croire l'inverse de ce qui se passe.
    """
    admin_headers, _ = admin
    assert client.get(
        "/api/v1/auth/me", headers=admin_headers
    ).json()["commercial_rules_apply"] is False

    user_headers, _ = make_user("facture@example.com")
    assert client.get(
        "/api/v1/auth/me", headers=user_headers
    ).json()["commercial_rules_apply"] is True


def test_in_public_mode_the_profile_says_the_rules_apply(client, admin, public):
    admin_headers, _ = admin
    assert client.get(
        "/api/v1/auth/me", headers=admin_headers
    ).json()["commercial_rules_apply"] is True


# ----------------------------------------------------------------------
# L'inscription


def test_creating_an_account_is_closed_during_the_private_beta(client, internal):
    """La bêta se mène avec des comptes connus."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "visiteur@example.com",
            "password": "MotDePasse123",
            "first_name": "Visiteur",
            "last_name": "Anonyme",
            "user_type": "AUTHOR",
        },
    )
    assert response.status_code == 403
    assert response.json()["code"] == "registration_closed"

    with SessionLocal() as db:
        assert db.query(User).filter(User.email == "visiteur@example.com").count() == 0


def test_the_form_can_ask_whether_registration_is_open(client, internal):
    """Sans cette réponse, l'écran proposerait une porte qui ne s'ouvre pas."""
    assert client.get("/api/v1/auth/registration").json() == {"open": False}


def test_registration_reopens_at_the_commercial_launch(client, public):
    """Rien n'est supprimé : `PLATFORM_MODE=public` rouvre, sans migration."""
    assert client.get("/api/v1/auth/registration").json() == {"open": True}
    assert client.post(
        "/api/v1/auth/register",
        json={
            "email": "nouvelle@example.com",
            "password": "MotDePasse123",
            "first_name": "Nouvelle",
            "last_name": "Venue",
            "user_type": "AUTHOR",
        },
    ).status_code == 202


def test_an_account_awaiting_confirmation_is_not_stranded(client, monkeypatch):
    """Le trou laissé exprès dans la fermeture.

    Fermer aussi la confirmation d'adresse emprisonnerait dans un état
    inactif tout compte créé avant la bascule : plus d'activation, et pas
    de recours non plus, puisque se réinscrire est justement fermé.
    """
    from tests.conftest import pending_verification_token, register_payload

    # Compte créé avant la fermeture, et resté non confirmé.
    monkeypatch.setattr("app.core.config.settings.platform_mode", "public")
    assert client.post(
        "/api/v1/auth/register", json=register_payload("attente@example.com")
    ).status_code == 202

    monkeypatch.setattr("app.core.config.settings.platform_mode", "internal")

    # Redemander le lien le renouvelle : c'est le lien final qui doit ouvrir.
    assert client.post(
        "/api/v1/auth/resend-verification", json={"email": "attente@example.com"}
    ).status_code == 200
    assert client.post(
        "/api/v1/auth/verify-email",
        json={"token": pending_verification_token("attente@example.com")},
    ).status_code == 200
    with SessionLocal() as db:
        assert db.query(User).filter(User.email == "attente@example.com").one().is_verified


# ----------------------------------------------------------------------
# Le prédicat lui-même


def test_an_unknown_user_is_subject_to_the_rules(internal):
    """Un défaut d'identification ne doit jamais valoir exemption."""
    assert commercial_rules_apply(None) is True


def test_a_passed_target_date_changes_nothing(monkeypatch, internal, client, admin):
    """Le défaut évité : une bascule au calendrier.

    Dépasser la date cible ne fait pas passer la plateforme en mode public —
    la transition est une décision, pas une échéance. Un basculement
    automatique opposerait soudain des quotas à une équipe en plein travail,
    un matin, sans que personne ne l'ait demandé.
    """
    headers, _ = admin
    monkeypatch.setattr("app.core.config.settings.internal_start_date", "2000-01-01")
    monkeypatch.setattr("app.core.config.settings.internal_target_end_date", "2000-01-02")

    assert platform_status()["mode"] == "internal"
    for index in range(2):
        assert client.post(
            "/api/v1/projects", json={**PROJECT, "title": f"P{index}"}, headers=headers
        ).status_code == 201


def test_the_status_is_reported_without_interpreting_the_dates(internal):
    status = platform_status()
    assert status["mode"] == "internal"
    assert status["internal"] is True
    assert status["start_date"] and status["target_end_date"]


def test_the_probe_publishes_the_mode(client, internal):
    """Un déploiement qui se croit commercial sans l'être doit se voir."""
    assert client.get("/health").json()["platform_mode"] == "internal"


def test_the_administration_reports_the_mode(client, admin, internal):
    headers, _ = admin
    body = client.get("/api/v1/admin/platform", headers=headers).json()
    assert body["mode"] == "internal"
    assert body["internal"] is True
