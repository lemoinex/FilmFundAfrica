"""Tests du tableau de bord, des acces admin et de la sonde de sante."""

from __future__ import annotations

from tests.conftest import PROJECT_PAYLOAD


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


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
