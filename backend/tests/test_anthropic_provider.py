"""Fournisseur Anthropic : ce qu'on envoie, et ce qu'on refuse de croire.

L'API Messages a change. Les modeles actuels **rejettent** `temperature` avec
une 400 et acceptent en echange une reflexion adaptative. Ces tests fixent ce
qui part sur le reseau selon le modele : une erreur ici ne degrade pas la
qualite d'une reponse, elle empeche toute reponse.
"""

from __future__ import annotations

import httpx
import pytest

from app.core.errors import AIProviderError
from app.services.ai.base import AICompletionRequest
from app.services.ai.providers.anthropic_provider import (
    AnthropicProvider,
    ModelCapabilities,
    capabilities_for,
)


def _request(model: str = "claude-opus-5", temperature: float = 0.4) -> AICompletionRequest:
    return AICompletionRequest(
        system_prompt="Tu es un consultant.",
        user_prompt="Rédige une logline.",
        model=model,
        max_output_tokens=8000,
        temperature=temperature,
    )


@pytest.fixture
def provider():
    return AnthropicProvider(api_key="clé-de-test")


# ----------------------------------------------------------------------
# Ce qui part sur le réseau


def test_a_current_model_never_receives_temperature(provider):
    """Le défaut corrigé : les modèles actuels répondent 400 à `temperature`.

    Ce n'est pas une dégradation de qualité — c'est un appel qui échoue.
    """
    payload = provider.build_payload(_request("claude-opus-5"))
    assert "temperature" not in payload


@pytest.mark.parametrize(
    "model", ["claude-opus-5", "claude-sonnet-5", "claude-opus-4-8", "claude-opus-4-7"]
)
def test_current_models_get_adaptive_thinking_and_effort(provider, model):
    payload = provider.build_payload(_request(model))
    assert payload["thinking"] == {"type": "adaptive"}
    assert payload["output_config"]["effort"] == "high"
    assert "temperature" not in payload


@pytest.mark.parametrize("model", ["claude-sonnet-4-5", "claude-haiku-4-5"])
def test_older_models_still_get_their_sampling(provider, model):
    """Ils ne connaissent ni la réflexion adaptative ni l'effort."""
    payload = provider.build_payload(_request(model, temperature=0.25))
    assert payload["temperature"] == 0.25
    assert "thinking" not in payload
    assert "output_config" not in payload


def test_an_unknown_model_receives_nothing_optional(provider):
    """Se taire est la seule option qui ne casse rien.

    Un paramètre omis prend son défaut serveur ; un paramètre de trop fait
    échouer l'appel. Devant un modèle inconnu, on n'envoie que l'essentiel.
    """
    payload = provider.build_payload(_request("claude-modele-a-venir"))
    assert set(payload) == {"model", "max_tokens", "system", "messages"}


def test_the_essentials_are_always_sent(provider):
    payload = provider.build_payload(_request())
    assert payload["model"] == "claude-opus-5"
    assert payload["max_tokens"] == 8000
    assert payload["system"] == "Tu es un consultant."
    assert payload["messages"] == [
        {"role": "user", "content": "Rédige une logline."}
    ]


def test_the_transitional_generation_accepts_both(provider):
    """4.6 accepte les deux : ne rien retirer ne casse rien, et prépare la suite."""
    payload = provider.build_payload(_request("claude-opus-4-6"))
    assert payload["thinking"] == {"type": "adaptive"}
    assert "temperature" in payload


def test_capabilities_fall_back_rather_than_guess():
    assert capabilities_for("inconnu") == ModelCapabilities()
    assert capabilities_for("claude-opus-5").adaptive_thinking
    assert not capabilities_for("claude-opus-5").sampling


def test_effort_can_be_turned_off(provider, monkeypatch):
    """Vide = on laisse le serveur décider, plutôt que d'imposer un niveau."""
    monkeypatch.setattr("app.core.config.settings.ai_effort", "")
    assert "output_config" not in provider.build_payload(_request())


# ----------------------------------------------------------------------
# Ce qu'on fait de la réponse


def _respond(monkeypatch, payload: dict, status: int = 200) -> None:
    def fake_post(self, url, json=None, headers=None):  # noqa: ARG001
        return httpx.Response(status, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.Client, "post", fake_post)


def test_a_normal_response_is_read(provider, monkeypatch):
    _respond(
        monkeypatch,
        {
            "content": [{"type": "text", "text": "Une logline."}],
            "model": "claude-opus-5",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 120, "output_tokens": 30},
        },
    )
    response = provider.complete(_request())
    assert response.text == "Une logline."
    assert response.input_tokens == 120
    assert response.output_tokens == 30
    assert response.provider == "anthropic"


def test_a_refusal_is_not_treated_as_a_reply(provider, monkeypatch):
    """Un refus arrive en 200, sans contenu exploitable.

    Le laisser passer produirait une étape vide qu'on prendrait pour une
    réponse du modèle — et, dans la chaîne, un dossier amputé d'une section
    sans que rien ne le signale.
    """
    _respond(
        monkeypatch,
        {
            "content": [],
            "model": "claude-opus-5",
            "stop_reason": "refusal",
            "stop_details": {"type": "refusal", "category": "cyber"},
        },
    )
    with pytest.raises(AIProviderError) as refused:
        provider.complete(_request())
    assert refused.value.code == "ai_refused"
    assert "cyber" in refused.value.detail


def test_a_refusal_without_a_category_still_says_something(provider, monkeypatch):
    _respond(
        monkeypatch,
        {"content": [], "model": "claude-opus-5", "stop_reason": "refusal"},
    )
    with pytest.raises(AIProviderError) as refused:
        provider.complete(_request())
    assert refused.value.code == "ai_refused"


def test_an_empty_response_is_refused(provider, monkeypatch):
    _respond(monkeypatch, {"content": [], "model": "claude-opus-5", "stop_reason": "end_turn"})
    with pytest.raises(AIProviderError):
        provider.complete(_request())


def test_an_http_error_is_reported_as_such(provider, monkeypatch):
    _respond(monkeypatch, {"error": {"message": "nope"}}, status=400)
    with pytest.raises(AIProviderError) as failed:
        provider.complete(_request())
    assert failed.value.code == "ai_provider_error"


def test_a_missing_key_refuses_to_build_the_provider(monkeypatch):
    """Mieux vaut échouer au démarrage qu'au premier appel payant."""
    monkeypatch.setattr("app.core.config.settings.ai_api_key", "")
    with pytest.raises(AIProviderError) as refused:
        AnthropicProvider()
    assert refused.value.code == "ai_provider_not_configured"
