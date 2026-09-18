"""Tests de la continuité entre les passes d'un scénario long.

Le défaut corrigé : chaque passe ne recevait que la FIN de la précédente
(3500 caractères). Un personnage présenté au premier acte avait donc disparu
du contexte à la quatrième passe, et rien n'empêchait l'IA de le renommer ou
de le présenter une seconde fois.

Les faits sont extraits du texte déjà produit, sans appel supplémentaire au
fournisseur : la continuité ne coûte aucun crédit.
"""

from __future__ import annotations

import pytest

from app.models.enums import DocumentType
from app.prompts import PromptContext, get_prompt
from app.services.ai.base import AICompletionResponse
from app.services.screenplay_service import (
    MAX_TRACKED_CHARACTERS,
    ScreenplayState,
    build_segment_prompt,
    extract_characters,
    extract_locations,
    plan_segments,
)

ACTE_I = """1. INT. MAISON DE FATOU - NUIT

Fatou veille près de la lampe à pétrole.

FATOU
Le fleuve monte encore.

AMINATA (inquiète)
Il faudra partir avant l'aube.

2. EXT. BERGE DU FLEUVE - AUBE

Les pirogues sont vides.

FATOU
Personne n'est revenu.
"""

ACTE_II = """14. INT. DISPENSAIRE DE NDIAYENE - JOUR

Une file d'attente silencieuse.

MOUSSA
Il n'y a plus d'eau potable.
"""


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------
def test_characters_and_locations_are_extracted_from_the_produced_text():
    assert extract_characters(ACTE_I) == ["FATOU", "AMINATA", "FATOU"]
    assert extract_locations(ACTE_I) == ["MAISON DE FATOU", "BERGE DU FLEUVE"]


def test_scene_headings_and_markers_are_not_taken_for_characters():
    text = "3. INT. BUREAU - JOUR\n\nACTE II\n\nFIN\n\nJOUR\n"
    assert extract_characters(text) == []


def test_free_prose_yields_no_fact_rather_than_a_wrong_one():
    """Un texte hors format ne doit rien inventer : on retombe sur l'ancien comportement."""
    text = "Le fleuve monte. Les habitants partent. Personne ne revient jamais.\n"
    assert extract_characters(text) == []
    assert extract_locations(text) == []
    assert ScreenplayState().as_prompt_block() == []


# ---------------------------------------------------------------------------
# Le défaut corrigé
# ---------------------------------------------------------------------------
def _prompt_for_last_segment(state: ScreenplayState, previous_text: str) -> str:
    segments = plan_segments(110, max_tokens_per_call=8000)
    context = PromptContext(title="Le fleuve", project_type="FEATURE_FILM")
    return build_segment_prompt(
        get_prompt(DocumentType.SCREENPLAY),
        context,
        segments[-1],
        language="français",
        target_minutes=110,
        previous_text=previous_text,
        user_instructions=None,
        state=state,
    ).user_prompt


def test_a_character_from_the_first_pass_is_still_known_at_the_last():
    state = ScreenplayState()
    state.absorb(ACTE_I, "Acte I — exposition")
    for index in range(6):
        state.absorb(ACTE_II, f"Acte II — partie {index + 1}")

    prompt = _prompt_for_last_segment(state, previous_text=ACTE_II)

    # FATOU n'apparaît plus dans le texte transmis pour la continuité…
    assert "FATOU" not in ACTE_II
    # …mais reste connue de la dernière passe.
    assert "FATOU" in prompt
    assert "AMINATA" in prompt
    assert "MAISON DE FATOU" in prompt


def test_without_the_state_the_first_act_is_forgotten():
    """Épingle le comportement d'avant : c'est lui que le test précédent corrige."""
    prompt = _prompt_for_last_segment(ScreenplayState(), previous_text=ACTE_II)
    assert "FATOU" not in prompt


def test_the_prompt_lists_the_segments_already_written():
    state = ScreenplayState()
    state.absorb(ACTE_I, "Acte I — exposition")
    state.absorb(ACTE_II, "Acte II — partie 1/3")

    prompt = _prompt_for_last_segment(state, previous_text=ACTE_II)
    assert "Acte I — exposition" in prompt
    assert "Acte II — partie 1/3" in prompt


def test_the_continuity_block_stays_bounded():
    """Un scénario de quarante passes ne doit pas noyer le prompt sous ses rappels."""
    state = ScreenplayState()
    many = "\n\n".join(f"PERSONNAGE{index}\nUne réplique." for index in range(200))
    state.absorb(many, "Acte I")

    block = "\n".join(state.as_prompt_block())
    listed = [line for line in block.splitlines() if line.startswith("Personnages")]
    assert len(listed) == 1
    names = listed[0].split(" : ", 1)[1].split(", ")
    assert len(names) == MAX_TRACKED_CHARACTERS


def test_the_block_does_not_grow_with_the_number_of_passes():
    """Rappeler les quarante libellés d'acte ferait enfler le prompt sans rien apprendre.

    La position dans l'arc est déjà donnée par le libellé du segment en cours :
    seuls les segments récents sont nommés, les autres comptés.
    """
    segments = plan_segments(681, max_tokens_per_call=8000)
    assert len(segments) == 40

    state = ScreenplayState()
    tailles = []
    for index, segment in enumerate(segments, 1):
        state.absorb(ACTE_I if index == 1 else ACTE_II, segment.label)
        tailles.append(len("\n".join(state.as_prompt_block())))

    # La taille se stabilise au lieu de croître passe après passe.
    assert tailles[-1] < 2 * tailles[4]


def test_the_most_present_characters_come_first():
    state = ScreenplayState()
    state.absorb(ACTE_I, "Acte I")  # FATOU deux fois, AMINATA une fois
    block = "\n".join(state.as_prompt_block())
    assert block.index("FATOU (2)") < block.index("AMINATA (1)")


# ---------------------------------------------------------------------------
# Bout en bout, à travers la génération réelle
# ---------------------------------------------------------------------------
def test_a_real_generation_carries_the_first_act_to_every_later_pass(
    client, make_user, monkeypatch
):
    from app.services.ai.service import AIService

    prompts: list[str] = []
    texts = [ACTE_I] + [ACTE_II] * 40

    def _fake_run(self, prompt):
        prompts.append(prompt.user_prompt)
        return AICompletionResponse(
            text=texts[min(len(prompts) - 1, len(texts) - 1)],
            model="test",
            provider="stub",
            output_tokens=100,
        )

    monkeypatch.setattr(AIService, "run", _fake_run)

    headers, _ = make_user("continuite@example.com", plan="PRODUCER")
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Le fleuve", "project_type": "FEATURE_FILM", "duration": 110},
        headers=headers,
    ).json()["id"]

    response = client.post(
        f"/api/v1/projects/{project_id}/documents/SCREENPLAY/generate",
        json={"language": "fr", "target_duration_minutes": 110},
        headers=headers,
    )
    assert response.status_code == 202, response.text

    assert len(prompts) > 3, "un scénario de 110 minutes s'écrit en plusieurs passes"
    # La première passe n'a rien à rappeler ; toutes les suivantes connaissent
    # les personnages du premier acte.
    assert "FATOU" not in prompts[0].split("ÉLÉMENTS DÉJÀ ÉTABLIS")[0][-3500:]
    for index, prompt in enumerate(prompts[1:], start=1):
        assert "FATOU" in prompt, f"passe {index + 1} a oublié le premier acte"


@pytest.mark.parametrize("cue", ["FATOU", "FATOU (au téléphone)", "  FATOU"])
def test_usual_cue_forms_are_recognised(cue):
    assert extract_characters(f"{cue}\nUne réplique.\n") == ["FATOU"]
