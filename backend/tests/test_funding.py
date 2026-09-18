"""Tests du module Funding Intelligence : recherche, matching, explication."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from tests.conftest import PROJECT_PAYLOAD


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def admin_headers(client, make_user, db_session):
    headers, registered = make_user("admin@example.com", plan="PRODUCER")

    from app.models.enums import UserType
    from app.models.user import User

    user = db_session.get(User, registered["user"]["id"])
    user.user_type = UserType.ADMIN
    db_session.commit()
    return headers


def opportunity_payload(**overrides) -> dict:
    payload = {
        "name": "Fonds Écritures du Sud",
        "organization": "Organisme de test",
        "description": "Aide à l'écriture pour documentaires d'Afrique francophone.",
        "country": "France",
        "eligible_countries": ["Sénégal", "Cameroun", "Mali"],
        "project_types": ["DOCUMENTARY", "FEATURE_FILM"],
        "genres": ["Documentaire de création"],
        "languages": ["Français"],
        "category": "FUND",
        "minimum_budget": 5000,
        "maximum_budget": 15000,
        "currency": "EUR",
        "deadline": str(date.today() + timedelta(days=30)),
        "requirements": "Synopsis, note d'intention",
        "source_name": "Site officiel de l'organisme",
        "source_url": "https://exemple-organisme.test/appel",
        "status": "OPEN",
        "requirement_items": [
            {
                "label": "Synopsis",
                "is_mandatory": True,
                "required_document_type": "SHORT_SYNOPSIS",
            },
            {
                "label": "Note d'intention",
                "is_mandatory": True,
                "required_document_type": "INTENT_NOTE",
            },
        ],
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def opportunity(client, admin_headers):
    response = client.post(
        "/api/v1/admin/funding", json=opportunity_payload(), headers=admin_headers
    )
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Administration
# ---------------------------------------------------------------------------
def test_admin_can_create_an_opportunity(client, admin_headers):
    response = client.post(
        "/api/v1/admin/funding", json=opportunity_payload(), headers=admin_headers
    )
    assert response.status_code == 201
    data = response.json()

    assert data["name"] == "Fonds Écritures du Sud"
    assert data["eligible_countries"] == ["Sénégal", "Cameroun", "Mali"]
    assert data["project_types"] == ["DOCUMENTARY", "FEATURE_FILM"]
    assert len(data["requirement_items"]) == 2
    # La traçabilité est renseignée dès la création.
    assert data["source_url"].startswith("https://")
    assert data["last_verified_at"] is not None


def test_source_url_is_mandatory_and_must_be_a_url(client, admin_headers):
    payload = opportunity_payload()
    del payload["source_url"]
    assert (
        client.post("/api/v1/admin/funding", json=payload, headers=admin_headers).status_code
        == 422
    )

    invalid = client.post(
        "/api/v1/admin/funding",
        json=opportunity_payload(source_url="pas-une-url"),
        headers=admin_headers,
    )
    assert invalid.status_code == 422


def test_budget_range_is_validated(client, admin_headers):
    response = client.post(
        "/api/v1/admin/funding",
        json=opportunity_payload(minimum_budget=20000, maximum_budget=5000),
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_regular_users_cannot_administer_opportunities(client, auth_headers, opportunity):
    assert client.get("/api/v1/admin/funding", headers=auth_headers).status_code == 403
    assert (
        client.post(
            "/api/v1/admin/funding", json=opportunity_payload(), headers=auth_headers
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/v1/admin/funding/{opportunity['id']}", headers=auth_headers
        ).status_code
        == 403
    )


def test_verify_updates_status_and_timestamp(client, admin_headers, opportunity):
    client.put(
        f"/api/v1/admin/funding/{opportunity['id']}",
        json={"status": "UNVERIFIED"},
        headers=admin_headers,
    )
    response = client.post(
        f"/api/v1/admin/funding/{opportunity['id']}/verify?new_status=OPEN",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "OPEN"
    assert response.json()["last_verified_at"] is not None


def test_requirements_can_be_added_and_removed(client, admin_headers, opportunity):
    added = client.post(
        f"/api/v1/admin/funding/{opportunity['id']}/requirements",
        json={"label": "Budget prévisionnel", "is_mandatory": True},
        headers=admin_headers,
    )
    assert added.status_code == 201
    assert len(added.json()["requirement_items"]) == 3

    requirement_id = added.json()["requirement_items"][-1]["id"]
    removed = client.delete(
        f"/api/v1/admin/funding/{opportunity['id']}/requirements/{requirement_id}",
        headers=admin_headers,
    )
    assert removed.status_code == 200
    assert len(removed.json()["requirement_items"]) == 2


# ---------------------------------------------------------------------------
# Recherche
# ---------------------------------------------------------------------------
def test_search_requires_authentication(client, opportunity):
    assert client.get("/api/v1/funding").status_code == 401


def test_full_text_search(client, auth_headers, opportunity):
    found = client.get("/api/v1/funding?query=Écritures", headers=auth_headers).json()
    assert found["total"] == 1

    absent = client.get("/api/v1/funding?query=introuvable", headers=auth_headers).json()
    assert absent["total"] == 0


def test_filters_by_country_type_and_category(client, auth_headers, opportunity):
    assert client.get("/api/v1/funding?country=Sénégal", headers=auth_headers).json()["total"] == 1
    assert client.get("/api/v1/funding?country=Canada", headers=auth_headers).json()["total"] == 0
    assert (
        client.get("/api/v1/funding?project_type=DOCUMENTARY", headers=auth_headers).json()["total"]
        == 1
    )
    assert (
        client.get("/api/v1/funding?project_type=ANIMATION", headers=auth_headers).json()["total"]
        == 0
    )
    assert client.get("/api/v1/funding?category=FUND", headers=auth_headers).json()["total"] == 1
    assert (
        client.get("/api/v1/funding?category=RESIDENCY", headers=auth_headers).json()["total"] == 0
    )


def test_amount_filter_keeps_opportunities_without_amount(client, auth_headers, admin_headers):
    client.post(
        "/api/v1/admin/funding",
        json=opportunity_payload(
            name="Sans montant", minimum_budget=None, maximum_budget=None
        ),
        headers=admin_headers,
    )
    results = client.get("/api/v1/funding?min_amount=50000", headers=auth_headers).json()
    # L'absence d'information n'est pas une exclusion.
    assert [item["name"] for item in results["items"]] == ["Sans montant"]


def test_expired_opportunities_are_hidden_by_default(client, auth_headers, admin_headers):
    client.post(
        "/api/v1/admin/funding",
        json=opportunity_payload(
            name="Échéance passée", deadline=str(date.today() - timedelta(days=5))
        ),
        headers=admin_headers,
    )
    assert client.get("/api/v1/funding", headers=auth_headers).json()["total"] == 0
    assert (
        client.get("/api/v1/funding?include_closed=true", headers=auth_headers).json()["total"] == 1
    )


def test_search_exposes_source_and_verification_date(client, auth_headers, opportunity):
    item = client.get("/api/v1/funding", headers=auth_headers).json()["items"][0]
    # Aucune opportunité ne doit être affichée sans sa traçabilité.
    assert item["source_name"]
    assert item["source_url"]
    assert item["last_verified_at"]


def test_facets_are_returned_for_the_filters(client, auth_headers, opportunity):
    facets = client.get("/api/v1/funding", headers=auth_headers).json()["facets"]
    assert "Sénégal" in facets["countries"]
    assert "Français" in facets["languages"]
    assert "FUND" in facets["categories"]


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------
def _matching_project(client, headers, **overrides):
    payload = {**PROJECT_PAYLOAD, **overrides}
    return client.post("/api/v1/projects", json=payload, headers=headers).json()


def test_matching_is_free_and_deterministic(client, auth_headers, opportunity, make_user):
    project = _matching_project(client, auth_headers)

    before = client.get("/api/v1/auth/me", headers=auth_headers).json()["ai_credits_remaining"]
    first = client.post(
        f"/api/v1/projects/{project['id']}/match-funding", headers=auth_headers
    )
    assert first.status_code == 200
    after = client.get("/api/v1/auth/me", headers=auth_headers).json()["ai_credits_remaining"]

    # Le score ne consomme aucun crédit.
    assert before == after

    second = client.post(
        f"/api/v1/projects/{project['id']}/match-funding", headers=auth_headers
    )
    assert [r["compatibility"] for r in first.json()["results"]] == [
        r["compatibility"] for r in second.json()["results"]
    ]


def test_matching_response_carries_the_disclaimer(client, auth_headers, opportunity):
    project = _matching_project(client, auth_headers)
    response = client.post(
        f"/api/v1/projects/{project['id']}/match-funding", headers=auth_headers
    ).json()
    assert "ne garantit en aucun cas" in response["disclaimer"]


def test_eligible_project_scores_high(client, auth_headers, opportunity):
    project = _matching_project(client, auth_headers)  # Sénégal, documentaire, 90 min
    result = client.post(
        f"/api/v1/projects/{project['id']}/match-funding", headers=auth_headers
    ).json()["results"][0]

    assert result["eligible"] is True
    assert result["compatibility"] >= 70
    assert result["met_conditions"]


def test_ineligible_country_is_blocking_but_still_visible(client, auth_headers, opportunity):
    project = _matching_project(client, auth_headers, title="Projet canadien", country="Canada")
    result = client.post(
        f"/api/v1/projects/{project['id']}/match-funding", headers=auth_headers
    ).json()["results"][0]

    assert result["eligible"] is False
    # Le dispositif reste affiché, avec la raison du refus.
    assert any("Canada" in condition for condition in result["missing_conditions"])


def test_unknown_data_is_not_guessed(client, auth_headers, opportunity):
    """Un champ non renseigné produit « à vérifier », jamais une supposition."""
    project = _matching_project(
        client, auth_headers, title="Projet incomplet", country=None, genre=None, duration=None
    )
    result = client.post(
        f"/api/v1/projects/{project['id']}/match-funding", headers=auth_headers
    ).json()["results"][0]

    assert result["unknown_conditions"]
    assert result["assessed_ratio"] < 100
    states = {c["key"]: c["state"] for c in result["criteria"]}
    assert states["country"] == "unknown"
    assert states["genre"] == "unknown"
    assert states["duration"] == "unknown"


def test_missing_required_documents_are_listed(client, auth_headers, opportunity):
    project = _matching_project(client, auth_headers)
    result = client.post(
        f"/api/v1/projects/{project['id']}/match-funding", headers=auth_headers
    ).json()["results"][0]

    assert set(result["required_documents"]) == {"Synopsis court", "Note d'intention"}
    assert set(result["missing_documents"]) == {"Synopsis court", "Note d'intention"}

    # Après génération, le synopsis n'est plus manquant.
    client.post(
        f"/api/v1/projects/{project['id']}/documents/SHORT_SYNOPSIS/generate",
        json={"language": "fr"},
        headers=auth_headers,
    )
    updated = client.post(
        f"/api/v1/projects/{project['id']}/match-funding", headers=auth_headers
    ).json()["results"][0]
    assert updated["missing_documents"] == ["Note d'intention"]


def test_criteria_weights_sum_to_one_hundred(client, auth_headers, opportunity):
    project = _matching_project(client, auth_headers)
    result = client.post(
        f"/api/v1/projects/{project['id']}/match-funding", headers=auth_headers
    ).json()["results"][0]
    assert sum(c["weight"] for c in result["criteria"]) == 100


def test_matches_are_scoped_to_the_owner(client, make_user, opportunity):
    alice, _ = make_user("alice@example.com", plan="PRO_AUTHOR")
    bob, _ = make_user("bob@example.com", plan="PRO_AUTHOR")
    project = _matching_project(client, alice)

    assert (
        client.post(f"/api/v1/projects/{project['id']}/match-funding", headers=bob).status_code
        == 404
    )
    assert client.get(f"/api/v1/projects/{project['id']}/matches", headers=bob).status_code == 404


def test_matches_feed_the_dashboard(client, auth_headers, opportunity):
    project = _matching_project(client, auth_headers)
    client.post(f"/api/v1/projects/{project['id']}/match-funding", headers=auth_headers)

    dashboard = client.get("/api/v1/dashboard", headers=auth_headers).json()
    assert dashboard["stats"]["compatible_opportunities"] == 1
    # L'échéance du dispositif de test tombe dans la fenêtre de 45 jours.
    assert dashboard["stats"]["upcoming_deadlines"] == 1
    recommended = dashboard["recommended_opportunities"][0]
    assert recommended["source_url"]
    assert recommended["last_verified_at"]


# ---------------------------------------------------------------------------
# Explication IA
# ---------------------------------------------------------------------------
def test_explanation_costs_one_credit_then_is_cached(client, auth_headers, opportunity):
    project = _matching_project(client, auth_headers)
    client.post(f"/api/v1/projects/{project['id']}/match-funding", headers=auth_headers)

    before = client.get("/api/v1/auth/me", headers=auth_headers).json()["ai_credits_remaining"]
    first = client.post(
        f"/api/v1/projects/{project['id']}/matches/{opportunity['id']}/explain",
        headers=auth_headers,
    )
    assert first.status_code == 200
    assert first.json()["credits_consumed"] == 1
    assert first.json()["credits_remaining"] == before - 1
    assert "ne garantit en aucun cas" in first.json()["disclaimer"]

    # La seconde demande réutilise l'explication : pas de nouveau débit.
    second = client.post(
        f"/api/v1/projects/{project['id']}/matches/{opportunity['id']}/explain",
        headers=auth_headers,
    )
    assert second.json()["credits_consumed"] == 0
    assert second.json()["credits_remaining"] == first.json()["credits_remaining"]


def test_explanation_is_refused_without_credits(client, make_user, opportunity):
    headers, _ = make_user("gratuit@example.com")  # plan FREE : 1 crédit
    project = _matching_project(client, headers)
    client.post(
        f"/api/v1/projects/{project['id']}/documents/SHORT_SYNOPSIS/generate",
        json={"language": "fr"},
        headers=headers,
    )  # consomme l'unique crédit

    response = client.post(
        f"/api/v1/projects/{project['id']}/matches/{opportunity['id']}/explain",
        headers=headers,
    )
    assert response.status_code == 402
    assert response.json()["code"] == "ai_credits_exhausted"


def test_explanation_marks_the_match_as_explained(client, auth_headers, opportunity):
    project = _matching_project(client, auth_headers)
    client.post(f"/api/v1/projects/{project['id']}/match-funding", headers=auth_headers)
    client.post(
        f"/api/v1/projects/{project['id']}/matches/{opportunity['id']}/explain",
        headers=auth_headers,
    )

    stored = client.get(f"/api/v1/projects/{project['id']}/matches", headers=auth_headers).json()
    assert stored["results"][0]["has_explanation"] is True


def test_document_criterion_gives_partial_credit(client, auth_headers, opportunity):
    """Le score doit progresser à mesure que l'auteur rédige les pièces exigées."""
    project = _matching_project(client, auth_headers)

    empty = client.post(
        f"/api/v1/projects/{project['id']}/match-funding", headers=auth_headers
    ).json()["results"][0]

    client.post(
        f"/api/v1/projects/{project['id']}/documents/SHORT_SYNOPSIS/generate",
        json={"language": "fr"},
        headers=auth_headers,
    )
    half = client.post(
        f"/api/v1/projects/{project['id']}/match-funding", headers=auth_headers
    ).json()["results"][0]

    client.post(
        f"/api/v1/projects/{project['id']}/documents/INTENT_NOTE/generate",
        json={"language": "fr"},
        headers=auth_headers,
    )
    full = client.post(
        f"/api/v1/projects/{project['id']}/match-funding", headers=auth_headers
    ).json()["results"][0]

    assert empty["compatibility"] < half["compatibility"] < full["compatibility"]

    documents = next(c for c in half["criteria"] if c["key"] == "documents")
    assert documents["state"] == "unmet"
    assert 0 < documents["earned"] < documents["weight"]

    assert next(c for c in full["criteria"] if c["key"] == "documents")["state"] == "met"
