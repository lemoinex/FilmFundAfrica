"""Tests du module Projets, y compris l'isolation des donnees."""

from __future__ import annotations

from tests.conftest import PROJECT_PAYLOAD


def test_create_and_read_project(client, auth_headers):
    created = client.post("/api/v1/projects", json=PROJECT_PAYLOAD, headers=auth_headers)
    assert created.status_code == 201
    data = created.json()
    assert data["title"] == PROJECT_PAYLOAD["title"]
    assert len(data["characters"]) == 1

    read = client.get(f"/api/v1/projects/{data['id']}", headers=auth_headers)
    assert read.status_code == 200
    assert read.json()["id"] == data["id"]


def test_list_projects_only_returns_own(client, make_user):
    alice, _ = make_user("alice@example.com", plan="PRO_AUTHOR")
    bob, _ = make_user("bob@example.com", plan="PRO_AUTHOR")

    client.post("/api/v1/projects", json=PROJECT_PAYLOAD, headers=alice)

    assert len(client.get("/api/v1/projects", headers=alice).json()) == 1
    assert client.get("/api/v1/projects", headers=bob).json() == []


def test_user_cannot_access_another_users_project(client, make_user):
    alice, _ = make_user("alice@example.com", plan="PRO_AUTHOR")
    bob, _ = make_user("bob@example.com", plan="PRO_AUTHOR")

    project_id = client.post(
        "/api/v1/projects", json=PROJECT_PAYLOAD, headers=alice
    ).json()["id"]

    # 404 et non 403 : l'existence du projet n'est pas divulguee.
    assert client.get(f"/api/v1/projects/{project_id}", headers=bob).status_code == 404
    assert (
        client.put(
            f"/api/v1/projects/{project_id}", json={"title": "Piraté"}, headers=bob
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/projects/{project_id}", headers=bob).status_code == 404


def test_update_and_delete_project(client, auth_headers, project):
    updated = client.put(
        f"/api/v1/projects/{project['id']}",
        json={"title": "Nouveau titre", "status": "WRITING"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Nouveau titre"
    assert updated.json()["status"] == "WRITING"

    assert (
        client.delete(f"/api/v1/projects/{project['id']}", headers=auth_headers).status_code == 200
    )
    assert client.get(f"/api/v1/projects/{project['id']}", headers=auth_headers).status_code == 404


def test_free_plan_is_limited_to_one_project(client, make_user):
    headers, _ = make_user("free@example.com")  # plan FREE par defaut
    assert (
        client.post("/api/v1/projects", json=PROJECT_PAYLOAD, headers=headers).status_code == 201
    )
    second = client.post("/api/v1/projects", json=PROJECT_PAYLOAD, headers=headers)
    assert second.status_code == 402
    assert second.json()["code"] == "project_quota_exceeded"


def test_character_crud(client, auth_headers, project):
    created = client.post(
        f"/api/v1/projects/{project['id']}/characters",
        json={"name": "Khady Sow", "role": "Protagoniste", "description": "Hydrologue."},
        headers=auth_headers,
    )
    assert created.status_code == 201
    character_id = created.json()["id"]

    updated = client.put(
        f"/api/v1/projects/{project['id']}/characters/{character_id}",
        json={"arc": "Découvre les limites de ses données."},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["arc"].startswith("Découvre")

    assert (
        client.delete(
            f"/api/v1/projects/{project['id']}/characters/{character_id}", headers=auth_headers
        ).status_code
        == 200
    )
    assert len(client.get(f"/api/v1/projects/{project['id']}/characters", headers=auth_headers).json()) == 1


def test_readiness_score_is_bounded_and_explains_gaps(client, auth_headers, project):
    response = client.get(f"/api/v1/projects/{project['id']}/score", headers=auth_headers)
    assert response.status_code == 200
    score = response.json()

    assert 0 <= score["total"] <= 100
    assert sum(item["weight"] for item in score["criteria"]) == 100
    assert all(item["earned"] <= item["weight"] for item in score["criteria"])
    # Un projet neuf a forcement des axes d'amelioration.
    assert score["improvements"]


def test_score_increases_when_project_is_completed(client, auth_headers, project):
    before = client.get(f"/api/v1/projects/{project['id']}/score", headers=auth_headers).json()
    client.put(
        f"/api/v1/projects/{project['id']}",
        json={
            "logline": "Trois femmes défendent un savoir que le sel menace d'effacer." * 2,
            "target_audience": "Public de documentaires de création et chaînes francophones.",
            "stakes": "La salinisation rend les terres incultivables : rester ou partir.",
            "objectives": "Festivals documentaires puis diffusion télévisée francophone.",
            "director_vision": "Plans longs, son direct, aucune voix off, à hauteur d'épaule.",
        },
        headers=auth_headers,
    )
    after = client.get(f"/api/v1/projects/{project['id']}/score", headers=auth_headers).json()
    assert after["total"] > before["total"]
