"""Routes du dossier et mise en file d'un passage.

Ce qui est verifie ici : qu'un passage ne tient pas la requete ouverte, qu'il
coute ce qu'il consomme, qu'un dossier d'autrui reste invisible, et qu'aucune
reponse ne declare exportable un dossier qui ne l'est pas.
"""

from __future__ import annotations

import json

import pytest

from app.models.enums import AIOperation, JobKind, JobStatus
from app.services.ai.base import AICompletionResponse, AIProvider
from app.services.credit_service import OPERATION_COST
from tests.conftest import job_result

PATCHES = {
    "DEVELOPMENT": {"public_cible": "18-35, urbain"},
    "PRODUCER": {"jours_tournage": 24},
}


class Scripted(AIProvider):
    name = "scripted"

    def __init__(self, verdict: str = "PASS", findings: list | None = None) -> None:
        self.verdict = verdict
        self.findings = findings or []
        self.calls = 0

    def complete(self, request):
        self.calls += 1
        role = request.metadata["agent_role"]
        patch = PATCHES.get(role)
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
                        "added": list(patch) if patch else [],
                        "reasoning": ["passe"] if patch else [],
                    },
                    "findings": self.findings if role.endswith("VALIDATOR") else [],
                    "verdict": self.verdict if role.endswith("VALIDATOR") else None,
                    "state_patch": patch,
                    "next_agent_instructions": "",
                },
                ensure_ascii=False,
            ),
            model="m",
            provider=self.name,
        )


@pytest.fixture
def scripted(monkeypatch):
    """Remplace le fournisseur pour toute la chaîne, worker compris."""
    provider = Scripted()
    monkeypatch.setattr("app.services.ai.service.build_provider", lambda *a, **k: provider)
    return provider


def _run(client, headers, project_id):
    return client.post(f"/api/v1/projects/{project_id}/dossier/run", headers=headers)


# ----------------------------------------------------------------------
# Lecture


def test_a_project_without_a_run_has_an_empty_dossier(client, auth_headers, project):
    """Un dossier vide n'est pas une erreur : il existe dès le projet."""
    response = client.get(f"/api/v1/projects/{project['id']}/dossier", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["concept"] == {}
    assert body["characters"] == []


def test_a_project_without_a_run_is_not_exportable(client, auth_headers, project):
    """Le défaut doit être « non », pas « on ne sait pas »."""
    body = client.get(
        f"/api/v1/projects/{project['id']}/dossier/status", headers=auth_headers
    ).json()
    assert body["exportable"] is False
    assert body["verdict"] is None
    assert body["runs"] == 0


# ----------------------------------------------------------------------
# Lancement


def test_running_the_chain_returns_a_job_not_a_dossier(client, auth_headers, project, scripted):
    """La requête ne tient pas huit appels ouverts : elle rend une tâche."""
    response = _run(client, auth_headers, project["id"])
    assert response.status_code == 202
    body = response.json()
    assert body["kind"] == JobKind.RUN_AGENT_CHAIN
    # Sans worker, le repli exécute tout de suite — la forme ne change pas.
    assert body["status"] in (JobStatus.QUEUED, JobStatus.SUCCEEDED)


def test_a_run_fills_the_dossier_and_records_its_steps(
    client, auth_headers, project, scripted
):
    job_result(_run(client, auth_headers, project["id"]))

    dossier = client.get(
        f"/api/v1/projects/{project['id']}/dossier", headers=auth_headers
    ).json()
    assert dossier["concept"] == {"public_cible": "18-35, urbain"}
    assert dossier["production_plan"] == {"jours_tournage": 24}

    runs = client.get(
        f"/api/v1/projects/{project['id']}/dossier/runs", headers=auth_headers
    ).json()
    assert len(runs) == 1
    assert runs[0]["verdict"] == "PASS"

    detail = client.get(
        f"/api/v1/projects/{project['id']}/dossier/runs/{runs[0]['id']}", headers=auth_headers
    ).json()
    assert [step["sequence"] for step in detail["steps"]] == list(range(1, 9))
    assert detail["steps"][0]["agent"] == "DEVELOPMENT"


def test_a_clean_run_makes_the_dossier_exportable(client, auth_headers, project, scripted):
    job_result(_run(client, auth_headers, project["id"]))
    status = client.get(
        f"/api/v1/projects/{project['id']}/dossier/status", headers=auth_headers
    ).json()
    assert status["exportable"] is True
    assert status["verdict"] == "PASS"
    assert status["blocking_findings"] == 0


# ----------------------------------------------------------------------
# Le coût


def test_a_chain_costs_one_credit_per_agent(client, make_user, scripted):
    """Facturer un passage comme un synopsis reviendrait à vendre à perte."""
    headers, _ = make_user("chaine@example.com", plan="PRO_AUTHOR")
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Projet chaîne", "project_type": "DOCUMENTARY"},
        headers=headers,
    ).json()["id"]

    before = client.get("/api/v1/users/me", headers=headers).json()["ai_credits_remaining"]
    job_result(_run(client, headers, project_id))
    after = client.get("/api/v1/users/me", headers=headers).json()["ai_credits_remaining"]

    assert before - after == 8 * OPERATION_COST[AIOperation.RUN_AGENT_CHAIN]


def test_a_free_plan_cannot_afford_a_chain(client, make_user, scripted):
    """L'offre gratuite accorde un crédit : elle ne peut pas payer huit agents.

    Le refus doit tomber tout de suite, pas après huit appels facturés.
    """
    headers, _ = make_user("gratuit@example.com")  # plan FREE : 1 crédit
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Projet gratuit", "project_type": "DOCUMENTARY"},
        headers=headers,
    ).json()["id"]

    response = _run(client, headers, project_id)
    assert response.status_code == 402
    assert scripted.calls == 0, "aucun appel au fournisseur ne doit avoir été payé"


# ----------------------------------------------------------------------
# Constats


def _blocking():
    return [
        {
            "severity": "CRITICAL",
            "element": "budget",
            "description": "Aucun budget fourni.",
            "owner": "PRODUCER",
        }
    ]


def test_a_blocking_finding_keeps_the_dossier_from_being_exportable(
    client, auth_headers, project, monkeypatch
):
    provider = Scripted(verdict="BLOCKED", findings=_blocking())
    monkeypatch.setattr("app.services.ai.service.build_provider", lambda *a, **k: provider)
    job_result(_run(client, auth_headers, project["id"]))

    status = client.get(
        f"/api/v1/projects/{project['id']}/dossier/status", headers=auth_headers
    ).json()
    assert status["exportable"] is False
    assert status["blocking_findings"] == 1

    findings = client.get(
        f"/api/v1/projects/{project['id']}/dossier/findings", headers=auth_headers
    ).json()
    assert findings[0]["severity"] == "CRITICAL"
    assert findings[0]["owner"] == "PRODUCER"


def test_resolved_findings_are_hidden_unless_asked_for(
    client, auth_headers, project, monkeypatch
):
    """Un constat levé reste consultable : il a existé, et cela se sait."""
    blocked = Scripted(verdict="BLOCKED", findings=_blocking())
    monkeypatch.setattr("app.services.ai.service.build_provider", lambda *a, **k: blocked)
    job_result(_run(client, auth_headers, project["id"]))

    clean = Scripted()
    monkeypatch.setattr("app.services.ai.service.build_provider", lambda *a, **k: clean)
    job_result(_run(client, auth_headers, project["id"]))

    base = f"/api/v1/projects/{project['id']}/dossier/findings"
    assert client.get(base, headers=auth_headers).json() == []
    resolved = client.get(f"{base}?include_resolved=true", headers=auth_headers).json()
    assert len(resolved) == 1
    assert resolved[0]["resolved_at"] is not None


def test_findings_come_worst_first(client, auth_headers, project, monkeypatch):
    mixed = Scripted(
        verdict="BLOCKED",
        findings=[
            {"severity": "MINOR", "element": "titre", "description": "perfectible"},
            {"severity": "CRITICAL", "element": "budget", "description": "absent"},
            {"severity": "MAJOR", "element": "lieu", "description": "contradictoire"},
        ],
    )
    monkeypatch.setattr("app.services.ai.service.build_provider", lambda *a, **k: mixed)
    job_result(_run(client, auth_headers, project["id"]))

    findings = client.get(
        f"/api/v1/projects/{project['id']}/dossier/findings", headers=auth_headers
    ).json()
    assert [f["severity"] for f in findings] == ["CRITICAL", "MAJOR", "MINOR"]


def test_modifications_are_readable_with_their_author(client, auth_headers, project, scripted):
    job_result(_run(client, auth_headers, project["id"]))
    rows = client.get(
        f"/api/v1/projects/{project['id']}/dossier/modifications", headers=auth_headers
    ).json()
    assert rows
    assert {row["agent"] for row in rows} == {"DEVELOPMENT", "PRODUCER"}
    assert all(row["reason"] for row in rows)


# ----------------------------------------------------------------------
# Cloisonnement


def test_another_users_dossier_is_invisible(client, make_user, project, scripted):
    """404 et non 403 : dire « interdit » révélerait que le projet existe."""
    intruder, _ = make_user("intrus@example.com")
    for path in ("", "/status", "/findings", "/runs", "/modifications"):
        response = client.get(
            f"/api/v1/projects/{project['id']}/dossier{path}", headers=intruder
        )
        assert response.status_code == 404, path


def test_another_users_run_is_invisible(client, auth_headers, make_user, project, scripted):
    job_result(_run(client, auth_headers, project["id"]))
    run_id = client.get(
        f"/api/v1/projects/{project['id']}/dossier/runs", headers=auth_headers
    ).json()[0]["id"]

    intruder, _ = make_user("intrus2@example.com")
    assert (
        client.get(
            f"/api/v1/projects/{project['id']}/dossier/runs/{run_id}", headers=intruder
        ).status_code
        == 404
    )


def test_an_unknown_run_is_a_404_not_a_crash(client, auth_headers, project):
    response = client.get(
        f"/api/v1/projects/{project['id']}/dossier/runs/inexistant", headers=auth_headers
    )
    assert response.status_code == 404
    assert response.json()["code"] == "agent_run_not_found"


def test_running_a_chain_requires_authentication(client, project):
    assert client.post(f"/api/v1/projects/{project['id']}/dossier/run").status_code == 401
