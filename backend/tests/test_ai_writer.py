"""Tests de l'AI Writer : generation, versioning, retravail, credits."""

from __future__ import annotations

import pytest

from app.core.errors import AppError
from app.models.enums import DocumentType
from app.prompts import PROMPT_REGISTRY, PromptContext, get_prompt
from app.services.ai.service import AIService
from app.services.screenplay_service import (
    SCREENPLAY_MAX_TOKENS_PER_CALL,
    build_segment_prompt,
    last_scene_number,
    pages_per_pass,
    plan_segments,
)
from tests.conftest import job_result


def _generate(client, headers, project_id, document_type="SHORT_SYNOPSIS", **payload):
    body = {"language": "fr", "overwrite": True}
    body.update(payload)
    return client.post(
        f"/api/v1/projects/{project_id}/documents/{document_type}/generate",
        json=body,
        headers=headers,
    )


def test_every_document_type_has_a_prompt():
    for document_type in DocumentType:
        assert document_type in PROMPT_REGISTRY, document_type
        template = PROMPT_REGISTRY[document_type]
        assert template.version
        assert template.outline


def test_document_types_endpoint_lists_prompts(client, auth_headers):
    response = client.get("/api/v1/documents/types", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == len(DocumentType)


def test_generate_creates_document_and_first_version(client, auth_headers, project):
    response = _generate(client, auth_headers, project["id"])
    result = job_result(response)

    assert result["document"]["document_type"] == "SHORT_SYNOPSIS"
    assert result["document"]["current_version"] == 1
    assert result["document"]["word_count"] > 0
    assert result["credits_consumed"] == 1
    assert result["provider"] == "mock"
    assert result["prompt_version"]

    versions = client.get(
        f"/api/v1/projects/{project['id']}/documents/{result['document']['id']}/versions",
        headers=auth_headers,
    ).json()
    assert len(versions) == 1
    assert versions[0]["origin"] == "AI_GENERATE"


def test_regenerating_adds_a_version_without_duplicating_document(client, auth_headers, project):
    first = job_result(_generate(client, auth_headers, project["id"]))
    second = job_result(_generate(client, auth_headers, project["id"]))

    assert first["document"]["id"] == second["document"]["id"]
    assert second["document"]["current_version"] == 2
    documents = client.get(
        f"/api/v1/projects/{project['id']}/documents", headers=auth_headers
    ).json()
    assert len([d for d in documents if d["document_type"] == "SHORT_SYNOPSIS"]) == 1


def test_overwrite_false_protects_existing_content(client, auth_headers, project):
    _generate(client, auth_headers, project["id"])
    blocked = _generate(client, auth_headers, project["id"], overwrite=False)
    assert blocked.status_code == 400
    assert blocked.json()["code"] == "document_exists"


def test_manual_save_then_restore_previous_version(client, auth_headers, project):
    document = job_result(_generate(client, auth_headers, project["id"]))["document"]
    original = document["content"]

    saved = client.put(
        f"/api/v1/projects/{project['id']}/documents/{document['id']}",
        json={"content": "Texte réécrit à la main par l'auteur.", "note": "Passe manuelle"},
        headers=auth_headers,
    )
    assert saved.status_code == 200
    assert saved.json()["current_version"] == 2

    restored = client.post(
        f"/api/v1/projects/{project['id']}/documents/{document['id']}/versions/1/restore",
        headers=auth_headers,
    )
    assert restored.status_code == 200
    assert restored.json()["content"] == original
    assert restored.json()["current_version"] == 3


def test_saving_identical_content_does_not_create_a_version(client, auth_headers, project):
    document = job_result(_generate(client, auth_headers, project["id"]))["document"]
    response = client.put(
        f"/api/v1/projects/{project['id']}/documents/{document['id']}",
        json={"content": document["content"]},
        headers=auth_headers,
    )
    assert response.json()["current_version"] == 1


@pytest.mark.parametrize("action", ["IMPROVE", "SHORTEN", "EXPAND", "CORRECT"])
def test_refine_actions(client, auth_headers, project, action):
    document = job_result(_generate(client, auth_headers, project["id"]))["document"]
    response = client.post(
        f"/api/v1/projects/{project['id']}/documents/{document['id']}/refine",
        json={"action": action},
        headers=auth_headers,
    )
    assert job_result(response)["document"]["current_version"] == 2


def test_generation_consumes_credits_and_stops_at_zero(client, make_user):
    headers, registered = make_user("free@example.com")  # plan FREE : 1 credit
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Projet test", "project_type": "DOCUMENTARY"},
        headers=headers,
    ).json()["id"]

    first = _generate(client, headers, project_id)
    assert job_result(first)["credits_remaining"] == 0

    second = _generate(client, headers, project_id)
    assert second.status_code == 402
    assert second.json()["code"] == "ai_credits_exhausted"


def test_generation_is_scoped_to_the_owner(client, make_user):
    alice, _ = make_user("alice@example.com", plan="PRO_AUTHOR")
    bob, _ = make_user("bob@example.com", plan="PRO_AUTHOR")
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Projet d'Alice", "project_type": "DOCUMENTARY"},
        headers=alice,
    ).json()["id"]

    assert _generate(client, bob, project_id).status_code == 404


def test_dependent_document_receives_previous_documents(client, auth_headers, project, db_session):
    """La note de realisation doit recevoir le synopsis et la note d'intention."""
    _generate(client, auth_headers, project["id"], document_type="SHORT_SYNOPSIS")
    _generate(client, auth_headers, project["id"], document_type="INTENT_NOTE")

    from app.models.project import Project
    from app.services.document_service import DocumentService

    stored = db_session.get(Project, project["id"])
    context = DocumentService(db_session).build_context(stored, DocumentType.DIRECTING_NOTE)

    assert "Synopsis court" in context.existing_documents
    assert "Note d'intention" in context.existing_documents
    rendered = get_prompt(DocumentType.DIRECTING_NOTE).render(context)
    assert "DOCUMENTS DÉJÀ VALIDÉS" in rendered.user_prompt


def test_screenplay_length_follows_target_duration(db_session, project):
    from app.models.project import Project

    stored = db_session.get(Project, project["id"])
    context = PromptContext.from_project(stored)
    template = get_prompt(DocumentType.SCREENPLAY)

    prompt_90 = template.render(context, target_duration=90)
    prompt_120 = template.render(context, target_duration=120)

    assert "90 pages de scénario" in prompt_90.user_prompt
    assert "120 pages de scénario" in prompt_120.user_prompt
    assert prompt_120.target_words_hint > prompt_90.target_words_hint


def test_a_feature_length_screenplay_no_longer_depends_on_the_token_budget():
    """Le défaut corrigé : un plafond de passes fixe rendait un long métrage
    irréalisable dès que le fournisseur produisait peu par appel.

    Avec l'ancien plafond de 10 passes et `AI_MAX_OUTPUT_TOKENS=4000`, la durée
    maximale tombait à 66 minutes : un scénario de 120 minutes était refusé.
    """
    with pytest.raises(AppError) as refused:
        plan_segments(120, max_tokens_per_call=4000, max_passes=10)
    assert refused.value.code == "screenplay_too_long"

    # Le nombre de passes suit désormais la durée demandée.
    segments = plan_segments(120, max_tokens_per_call=4000)
    assert sum(segment.pages for segment in segments) >= 115
    assert all(segment.pages <= pages_per_pass(4000) for segment in segments)


def test_the_pass_count_follows_the_requested_duration():
    short = plan_segments(120, max_tokens_per_call=8000)
    long = plan_segments(240, max_tokens_per_call=8000)
    assert len(long) > len(short)
    # Chaque passe reste sous le plafond de sortie d'un appel.
    assert all(segment.pages <= pages_per_pass(8000) for segment in long)


def test_the_safety_ceiling_still_refuses_an_absurd_duration():
    """Le plafond n'est plus une limite d'usage, mais il protège encore."""
    with pytest.raises(AppError) as refused:
        plan_segments(5000, max_tokens_per_call=8000)
    assert refused.value.code == "screenplay_too_long"
    # Le message dit ce qui est réalisable plutôt que de laisser l'auteur deviner.
    assert "Maximum réalisable" in refused.value.detail


def test_announced_capacity_matches_what_the_planner_accepts(client, auth_headers):
    """L'interface n'affiche que des durées réellement productibles."""
    capacity = client.get("/api/v1/documents/screenplay-capacity", headers=auth_headers).json()
    budget = AIService.effective_max_output_tokens(SCREENPLAY_MAX_TOKENS_PER_CALL)

    assert len(plan_segments(capacity["max_minutes"], budget)) <= capacity["max_passes"]
    with pytest.raises(AppError):
        plan_segments(capacity["max_minutes"] + 1, budget)


def test_short_screenplay_fits_a_single_pass():
    segments = plan_segments(10, max_tokens_per_call=8000)
    assert len(segments) == 1
    assert segments[0].pages == 10


def test_long_screenplay_is_split_into_ordered_segments():
    segments = plan_segments(110, max_tokens_per_call=8000)

    assert len(segments) > 1
    assert [s.index for s in segments] == list(range(1, len(segments) + 1))
    assert all(s.total == len(segments) for s in segments)
    # Le découpage couvre la durée cible sans la dépasser fortement.
    assert 100 <= sum(s.pages for s in segments) <= 125
    # Chaque passe reste sous le plafond de sortie du fournisseur.
    assert all(s.words * 2.2 <= 8000 * 1.05 for s in segments)


def test_segment_prompts_carry_continuity(db_session, project):
    from app.models.project import Project

    stored = db_session.get(Project, project["id"])
    context = PromptContext.from_project(stored)
    template = get_prompt(DocumentType.SCREENPLAY)
    segments = plan_segments(110, max_tokens_per_call=8000)

    first = build_segment_prompt(
        template, context, segments[0], language="français",
        target_minutes=110, previous_text="", user_instructions=None,
    )
    assert "page de titre" in first.user_prompt

    previous = "12. INT. MAISON DE FATOU - NUIT\n\nFatou veille.\n"
    second = build_segment_prompt(
        template, context, segments[1], language="français",
        target_minutes=110, previous_text=previous, user_instructions=None,
    )
    assert "reprend à 13" in second.user_prompt
    assert "FIN DU SEGMENT PRÉCÉDENT" in second.user_prompt
    assert "N'écris NI page de titre" in second.user_prompt

    last = build_segment_prompt(
        template, context, segments[-1], language="français",
        target_minutes=110, previous_text=previous, user_instructions=None,
    )
    assert "climax et la résolution" in last.user_prompt


def test_last_scene_number_resumes_numbering():
    assert last_scene_number("3. INT. BUREAU - JOUR\n\n7. EXT. RUE - NUIT\n") == 7
    assert last_scene_number("Aucune séquence numérotée.") == 0


def test_long_screenplay_generation_costs_one_credit_per_pass(client, make_user):
    headers, _ = make_user("producteur@example.com", plan="PRODUCER")
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Long métrage", "project_type": "FEATURE_FILM", "duration": 110},
        headers=headers,
    ).json()["id"]

    response = client.post(
        f"/api/v1/projects/{project_id}/documents/SCREENPLAY/generate",
        json={"language": "fr", "target_duration_minutes": 110},
        headers=headers,
    )
    result = job_result(response)
    assert result["passes"] > 1
    assert result["credits_consumed"] == result["passes"]


def test_screenplay_target_is_independent_of_project_duration(client, make_user):
    """Une durée annoncée par `/screenplay-capacity` doit être réalisable,
    même si la durée enregistrée sur le projet est bien plus courte."""
    headers, _ = make_user("court@example.com", plan="PRODUCER")
    capacity = client.get("/api/v1/documents/screenplay-capacity", headers=headers).json()
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Court devenu long", "project_type": "FEATURE_FILM", "duration": 10},
        headers=headers,
    ).json()["id"]

    response = client.post(
        f"/api/v1/projects/{project_id}/documents/SCREENPLAY/generate",
        json={"language": "fr", "target_duration_minutes": capacity["max_minutes"]},
        headers=headers,
    )
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "SUCCEEDED", response.text


def test_restoring_a_version_resyncs_project_fields(client, auth_headers, project):
    document = job_result(_generate(client, auth_headers, project["id"]))["document"]
    original = document["content"].strip()

    client.put(
        f"/api/v1/projects/{project['id']}/documents/{document['id']}",
        json={"content": "Synopsis réécrit à la main."},
        headers=auth_headers,
    )
    client.post(
        f"/api/v1/projects/{project['id']}/documents/{document['id']}/versions/1/restore",
        headers=auth_headers,
    )

    refreshed = client.get(f"/api/v1/projects/{project['id']}", headers=auth_headers).json()
    assert refreshed["short_synopsis"] == original


def test_screenplay_generation_refused_when_credits_insufficient(client, make_user):
    headers, _ = make_user("petit.budget@example.com")  # plan FREE : 1 crédit
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Long métrage", "project_type": "FEATURE_FILM", "duration": 110},
        headers=headers,
    ).json()["id"]

    response = client.post(
        f"/api/v1/projects/{project_id}/documents/SCREENPLAY/generate",
        json={"language": "fr", "target_duration_minutes": 110},
        headers=headers,
    )
    assert response.status_code == 402
    assert response.json()["code"] == "ai_credits_exhausted"


def test_prompt_forbids_inventing_information(project, db_session):
    from app.models.project import Project

    stored = db_session.get(Project, project["id"])
    rendered = get_prompt(DocumentType.SHORT_SYNOPSIS).render(PromptContext.from_project(stored))
    assert "Information non fournie." in rendered.system_prompt
    assert "N'invente jamais" in rendered.system_prompt


def test_missing_information_is_extracted():
    text = (
        "## Synopsis\n\nUn récit.\n\n"
        "## Informations à compléter\n\n- Le budget prévisionnel\n- Le public cible\n"
    )
    assert AIService.extract_missing_information(text) == [
        "Le budget prévisionnel",
        "Le public cible",
    ]
    assert AIService.extract_missing_information("## Synopsis\n\nUn récit.") == []


def test_mock_provider_never_invents_content(client, auth_headers, project):
    content = job_result(_generate(client, auth_headers, project["id"]))["document"]["content"]
    assert "MODE `mock`" in content
    assert "Information non fournie." in content
    # Le seul personnage present est celui saisi par l'utilisateur.
    assert "Fatou Sow" in content
