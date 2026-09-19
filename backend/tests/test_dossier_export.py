"""Export PDF du dossier construit par la chaine.

Ce qui compte ici n'est pas que le PDF existe, mais qu'il ne mente jamais sur
son etat : un dossier non valide ne doit pas pouvoir passer pour un document
final, et les constats internes ne doivent pas se retrouver dans ce qu'on
envoie a un financeur.
"""

from __future__ import annotations

import json

import pytest

from app.services.ai.base import AICompletionResponse, AIProvider
from tests.conftest import job_result

PATCHES = {
    "DEVELOPMENT": {"public cible": "18-35, urbain"},
    "PRODUCER": {"jours de tournage": 24},
}


class Scripted(AIProvider):
    name = "scripted"

    def __init__(self, verdict: str = "PASS", findings: list | None = None) -> None:
        self.verdict = verdict
        self.findings = findings or []

    def complete(self, request):
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
                        "added": [],
                        "reasoning": [],
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


def _blocking():
    return [
        {
            "severity": "CRITICAL",
            "element": "budget",
            "description": "Aucun budget fourni.",
            "owner": "PRODUCER",
            "suggested_correction": "Chiffrer les 24 jours de tournage.",
        }
    ]


@pytest.fixture
def paid(client, make_user):
    """L'export est réservé aux offres qui l'incluent."""
    headers, _ = make_user("export@example.com", plan="PRO_AUTHOR")
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Taxi 237", "project_type": "FEATURE_FILM"},
        headers=headers,
    ).json()["id"]
    return headers, project_id


def _run_chain(client, headers, project_id, monkeypatch, provider):
    monkeypatch.setattr("app.services.ai.service.build_provider", lambda *a, **k: provider)
    job_result(client.post(f"/api/v1/projects/{project_id}/dossier/run", headers=headers))


def _export(client, headers, project_id):
    return client.get(f"/api/v1/projects/{project_id}/export/dossier/pdf", headers=headers)


# ----------------------------------------------------------------------


def test_nothing_to_export_before_the_chain_has_run(client, paid):
    """Un PDF vide serait plus déroutant qu'une erreur qui dit quoi faire."""
    headers, project_id = paid
    response = _export(client, headers, project_id)
    assert response.status_code == 400
    assert response.json()["code"] == "dossier_not_built"


def test_a_validated_dossier_exports_as_a_pdf(client, paid, monkeypatch):
    headers, project_id = paid
    _run_chain(client, headers, project_id, monkeypatch, Scripted())

    response = _export(client, headers, project_id)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    # Le nom du fichier ne porte pas la mention brouillon.
    assert "BROUILLON" not in response.headers["content-disposition"]


def test_an_unvalidated_dossier_is_named_a_draft(client, paid, monkeypatch):
    """Le nom du fichier doit dire l'état : il survit au téléchargement."""
    headers, project_id = paid
    _run_chain(
        client, headers, project_id, monkeypatch, Scripted("BLOCKED", _blocking())
    )

    response = _export(client, headers, project_id)
    assert response.status_code == 200
    assert "BROUILLON" in response.headers["content-disposition"]


def test_the_draft_says_so_inside_the_document(client, paid, monkeypatch):
    """Un fichier renommé perdrait l'avertissement : il est aussi dans la page."""
    from pypdf import PdfReader

    headers, project_id = paid
    _run_chain(
        client, headers, project_id, monkeypatch, Scripted("BLOCKED", _blocking())
    )

    text = _pdf_text(PdfReader, _export(client, headers, project_id).content)
    assert "BROUILLON" in text
    assert "ne doit pas être soumis" in text
    assert "bloqué" in text


def test_a_validated_dossier_never_claims_to_be_a_guarantee(client, paid, monkeypatch):
    """Règle produit : le score et le dossier aident, ils ne garantissent rien."""
    from pypdf import PdfReader

    headers, project_id = paid
    _run_chain(client, headers, project_id, monkeypatch, Scripted())

    text = _pdf_text(PdfReader, _export(client, headers, project_id).content)
    assert "relecture humaine" in text
    assert "BROUILLON" not in text


def test_internal_findings_stay_out_of_a_validated_dossier(client, paid, monkeypatch):
    """Les exposer à un financeur desservirait le projet.

    Un constat mineur ne bloque pas l'export ; il ne doit pas pour autant se
    retrouver dans le document qu'un comité va lire.
    """
    from pypdf import PdfReader

    headers, project_id = paid
    minor = [
        {
            "severity": "MINOR",
            "element": "titre",
            "description": "Formulation perfectible du titre.",
            "owner": "DEVELOPMENT",
        }
    ]
    _run_chain(
        client, headers, project_id, monkeypatch, Scripted("PASS_WITH_WARNINGS", minor)
    )

    response = _export(client, headers, project_id)
    assert "BROUILLON" not in response.headers["content-disposition"]

    text = _pdf_text(PdfReader, response.content)
    assert "Points à traiter" not in text
    assert "Formulation perfectible" not in text


def test_a_draft_carries_its_findings_and_their_owner(client, paid, monkeypatch):
    """C'est la seule raison de produire ce PDF-là : savoir quoi corriger."""
    from pypdf import PdfReader

    headers, project_id = paid
    _run_chain(
        client, headers, project_id, monkeypatch, Scripted("BLOCKED", _blocking())
    )

    text = _pdf_text(PdfReader, _export(client, headers, project_id).content)
    assert "Points à traiter" in text
    assert "Aucun budget fourni" in text
    assert "Production" in text  # l'agent capable de corriger
    assert "Chiffrer les 24 jours" in text


def test_the_sections_produced_by_the_agents_are_in_the_pdf(client, paid, monkeypatch):
    from pypdf import PdfReader

    headers, project_id = paid
    _run_chain(client, headers, project_id, monkeypatch, Scripted())

    text = _pdf_text(PdfReader, _export(client, headers, project_id).content)
    assert "Concept" in text
    assert "18-35, urbain" in text
    assert "Plan de production" in text


def test_an_empty_section_is_not_printed(client, paid, monkeypatch):
    """Un titre suivi de rien se lit comme un défaut de mise en page."""
    from pypdf import PdfReader

    headers, project_id = paid
    _run_chain(client, headers, project_id, monkeypatch, Scripted())

    text = _pdf_text(PdfReader, _export(client, headers, project_id).content)
    # Aucun agent n'a rempli l'analyse culturelle dans ce scénario.
    assert "Analyse culturelle" not in text


def test_another_user_cannot_export_this_dossier(client, paid, make_user, monkeypatch):
    headers, project_id = paid
    _run_chain(client, headers, project_id, monkeypatch, Scripted())

    intruder, _ = make_user("intrus-export@example.com", plan="PRO_AUTHOR")
    assert _export(client, intruder, project_id).status_code == 404


def test_the_free_plan_cannot_export(client, make_user):
    """L'export est une fonctionnalité d'offre, dossier compris."""
    headers, _ = make_user("gratuit-export@example.com")
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Projet gratuit", "project_type": "DOCUMENTARY"},
        headers=headers,
    ).json()["id"]
    assert _export(client, headers, project_id).status_code == 402


def _pdf_text(reader_cls, content: bytes) -> str:
    import io

    reader = reader_cls(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)
