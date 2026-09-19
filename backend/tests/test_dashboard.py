"""Tests du tableau de bord, des acces admin et de la sonde de sante."""

from __future__ import annotations

from tests.conftest import PROJECT_PAYLOAD


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_the_probe_names_the_variables_it_received(client, monkeypatch):
    """Distinguer « mal renseignée » de « jamais transmise ».

    Sans ce repérage, une variable qui n'atteint pas le processus ne se lit
    que par ses effets — environnement `development`, base injoignable — et
    l'on ne sait pas s'il faut corriger la valeur ou l'endroit où elle est
    posée.
    """
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("SECRETS_KEY", "une-cle-de-test")
    monkeypatch.delenv("REDIS_URL", raising=False)

    config = client.get("/health").json()["config"]
    assert config["host"] == "production"
    assert "SECRETS_KEY" in config["provided"]
    assert "REDIS_URL" not in config["provided"]


def test_an_empty_variable_does_not_count_as_provided(client, monkeypatch):
    """Une variable vide n'est pas une variable renseignée — ici aussi.

    C'est précisément le cas que la sonde doit rendre visible : coller les
    noms sans les valeurs produit des variables vides, indiscernables de
    variables absentes par leurs seuls effets.
    """
    monkeypatch.setenv("SECRETS_KEY", "   ")
    assert "SECRETS_KEY" not in client.get("/health").json()["config"]["provided"]


def test_the_probe_never_publishes_a_value(client, monkeypatch):
    """Les noms sont déjà publics ; les valeurs sont des secrets."""
    monkeypatch.setenv("JWT_SECRET", "valeur-qui-ne-doit-jamais-sortir")
    assert "valeur-qui-ne-doit-jamais-sortir" not in client.get("/health").text


def test_dashboard_reflects_projects_and_documents(client, auth_headers):
    empty = client.get("/api/v1/dashboard", headers=auth_headers).json()
    assert empty["stats"]["projects"] == 0
    assert empty["welcome_name"] == "Aïcha"

    project_id = client.post(
        "/api/v1/projects", json=PROJECT_PAYLOAD, headers=auth_headers
    ).json()["id"]
    client.post(
        f"/api/v1/projects/{project_id}/documents/SHORT_SYNOPSIS/generate",
        json={"language": "fr"},
        headers=auth_headers,
    )

    filled = client.get("/api/v1/dashboard", headers=auth_headers).json()
    assert filled["stats"]["projects"] == 1
    assert filled["stats"]["documents_generated"] == 1
    assert filled["projects"][0]["document_count"] == 1
    assert filled["projects"][0]["readiness_score"] is not None


def test_dashboard_is_per_user(client, make_user):
    alice, _ = make_user("alice@example.com", plan="PRO_AUTHOR")
    bob, _ = make_user("bob@example.com", plan="PRO_AUTHOR")
    client.post("/api/v1/projects", json=PROJECT_PAYLOAD, headers=alice)

    assert client.get("/api/v1/dashboard", headers=bob).json()["stats"]["projects"] == 0


def test_admin_routes_are_forbidden_to_regular_users(client, auth_headers):
    assert client.get("/api/v1/admin/users", headers=auth_headers).status_code == 403
    assert client.get("/api/v1/admin/stats/ai", headers=auth_headers).status_code == 403


def test_admin_can_list_users_and_plans(client, make_user, db_session):
    headers, registered = make_user("admin@example.com")

    from app.models.enums import UserType
    from app.models.user import User

    user = db_session.get(User, registered["user"]["id"])
    user.user_type = UserType.ADMIN
    db_session.commit()

    assert client.get("/api/v1/admin/users", headers=headers).status_code == 200
    plans = client.get("/api/v1/admin/plans", headers=headers).json()
    assert {plan["code"] for plan in plans} == {"FREE", "PRO_AUTHOR", "PRODUCER"}
    # Les prix sont configurables depuis l'administration.
    assert any(plan["price_amount"] == 20000 for plan in plans)


def test_profile_update(client, auth_headers):
    response = client.put(
        "/api/v1/users/me/profile",
        json={"city": "Saint-Louis", "profession": "Réalisatrice"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["profile"]["city"] == "Saint-Louis"
