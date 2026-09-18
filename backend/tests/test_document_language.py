"""La langue d'un document le suit du premier jet jusqu'au retravail.

Trois notions de langue coexistent et ne doivent pas se confondre :
`projects.language` est celle de l'oeuvre, le profil porte celle de
l'interface, et `documents.language` celle du dossier. Un long metrage en
wolof se presente en francais a un fonds francophone : deduire l'une de
l'autre produirait un document dans la mauvaise langue.
"""

from __future__ import annotations

import pytest

from app.prompts import PromptContext, build_refine_prompt
from tests.conftest import job_result


def _generate(client, headers, project_id, language, document_type="SHORT_SYNOPSIS"):
    return client.post(
        f"/api/v1/projects/{project_id}/documents/{document_type}/generate",
        json={"language": language, "overwrite": True},
        headers=headers,
    )


@pytest.mark.parametrize("language", ["fr", "en"])
def test_generation_records_the_language_it_was_written_in(
    client, auth_headers, project, language
):
    document = job_result(_generate(client, auth_headers, project["id"], language))["document"]
    assert document["language"] == language


def test_regenerating_in_another_language_moves_the_document(client, auth_headers, project):
    """Le contenu est remplace : la langue retenue doit suivre.

    Sinon le retravail suivant repartirait sur celle du premier jet et
    corrigerait un texte anglais selon la typographie francaise.
    """
    first = job_result(_generate(client, auth_headers, project["id"], "fr"))["document"]
    assert first["language"] == "fr"

    second = job_result(_generate(client, auth_headers, project["id"], "en"))["document"]
    assert second["id"] == first["id"]
    assert second["language"] == "en"


def test_the_document_list_exposes_the_language(client, auth_headers, project):
    job_result(_generate(client, auth_headers, project["id"], "en"))
    listed = client.get(
        f"/api/v1/projects/{project['id']}/documents", headers=auth_headers
    ).json()
    assert [entry["language"] for entry in listed] == ["en"]


def test_a_missing_language_falls_back_without_failing(client, auth_headers, project):
    """Le frontend peut ne rien envoyer : le serveur applique sa propre defaut."""
    response = client.post(
        f"/api/v1/projects/{project['id']}/documents/SHORT_SYNOPSIS/generate",
        json={"overwrite": True},
        headers=auth_headers,
    )
    assert job_result(response)["document"]["language"] == "fr"


# ----------------------------------------------------------------------
# Consignes de retravail


def _context() -> PromptContext:
    return PromptContext(title="Taxi 237", project_type="FEATURE_FILM")


def test_correcting_an_english_document_does_not_apply_french_typography():
    """Le defaut corrige : « corriger » imposait les guillemets « » a un texte anglais."""
    english = build_refine_prompt("CORRECT", "Synopsis", "A short text.", _context(), locale="en")
    assert "English typography" in english.user_prompt
    assert "typographie française" not in english.user_prompt
    assert "«" not in english.user_prompt
    # Le systeme demande bien la production en anglais.
    assert "Tu écris en anglais." in english.system_prompt


def test_correcting_a_french_document_keeps_french_typography():
    french = build_refine_prompt("CORRECT", "Synopsis", "Un texte court.", _context(), locale="fr")
    assert "typographie française" in french.user_prompt
    assert "Tu écris en français." in french.system_prompt


@pytest.mark.parametrize("action", ["IMPROVE", "SHORTEN", "EXPAND", "CORRECT"])
def test_every_refine_action_is_translated(action):
    """Une action sans traduction retomberait silencieusement sur le francais."""
    french = build_refine_prompt(action, "Synopsis", "Texte.", _context(), locale="fr")
    english = build_refine_prompt(action, "Synopsis", "Texte.", _context(), locale="en")
    assert french.user_prompt != english.user_prompt


def test_an_unknown_locale_falls_back_to_the_reference_language():
    """Garde-fou : une langue inconnue ne doit pas produire un prompt vide."""
    fallback = build_refine_prompt("CORRECT", "Synopsis", "Texte.", _context(), locale="xx")
    reference = build_refine_prompt("CORRECT", "Synopsis", "Texte.", _context(), locale="fr")
    assert fallback.user_prompt == reference.user_prompt
