"""Tests des garde-fous de sécurité et de configuration.

Chacun de ces tests correspond à un défaut réel identifié en revue : ils
existent pour empêcher sa réapparition.
"""

from __future__ import annotations

import pytest

from app.core.config import DEV_JWT_SECRET, Settings
from app.core.rate_limit import MemoryBackend, RateLimiter, RateLimitExceeded, auth_limiter
from tests.conftest import PROJECT_PAYLOAD, register_payload


# ---------------------------------------------------------------------------
# Configuration : refus de démarrer en production avec des réglages dangereux
# ---------------------------------------------------------------------------
def _production_settings(**overrides) -> Settings:
    base = {
        "environment": "production",
        "debug": False,
        "jwt_secret": "a" * 64,
        "ai_provider": "mock",
        # Les tests tournent avec PAYMENT_PROVIDER=mock, que la production
        # refuse : on repart d'une configuration d'encaissement légitime.
        "payment_provider": "manual",
        "_env_file": None,
    }
    base.update(overrides)
    return Settings(**base)


def test_production_rejects_the_development_jwt_secret():
    with pytest.raises(ValueError, match="JWT_SECRET"):
        _production_settings(jwt_secret=DEV_JWT_SECRET)


def test_production_rejects_a_short_jwt_secret():
    with pytest.raises(ValueError, match="32 caractères"):
        _production_settings(jwt_secret="trop-court")


def test_production_rejects_debug_mode():
    with pytest.raises(ValueError, match="DEBUG"):
        _production_settings(debug=True)


def test_production_rejects_an_ai_provider_without_key():
    with pytest.raises(ValueError, match="AI_API_KEY"):
        _production_settings(ai_provider="anthropic", ai_api_key="")


def test_valid_production_settings_are_accepted():
    settings = _production_settings()
    assert settings.is_production
    assert not settings.is_development


# ---------------------------------------------------------------------------
# Limitation de débit
# ---------------------------------------------------------------------------
def test_rate_limiter_blocks_after_the_limit():
    limiter = RateLimiter(max_calls=3)
    for _ in range(3):
        limiter.check("1.2.3.4:/login")
    with pytest.raises(RateLimitExceeded):
        limiter.check("1.2.3.4:/login")


def test_forged_x_forwarded_for_cannot_bypass_the_rate_limit(client):
    """Sans proxy déclaré, l'en-tête client ne doit pas changer l'identification."""
    auth_limiter.reset()
    limit = auth_limiter.max_calls
    auth_limiter.max_calls = 3
    try:
        statuses = [
            client.post(
                "/api/v1/auth/login",
                json={"email": f"inconnu{index}@example.com", "password": "MotDePasse123"},
                headers={"X-Forwarded-For": f"10.0.0.{index}"},
            ).status_code
            for index in range(6)
        ]
    finally:
        auth_limiter.max_calls = limit
        auth_limiter.reset()

    # Malgré une IP usurpée différente à chaque appel, la limite s'applique.
    assert 429 in statuses


def test_rate_limiter_evicts_stale_buckets(monkeypatch):
    # Horloge simulée : la résolution de `time.monotonic()` (~15 ms sous
    # Windows) donnerait le même instant aux 50 appels.
    clock = iter(range(0, 10_000, 2))
    monkeypatch.setattr("app.core.rate_limit.time.monotonic", lambda: next(clock))
    backend = MemoryBackend()
    limiter = RateLimiter(max_calls=5, window_seconds=1, backend=backend)
    for index in range(50):
        limiter.check(f"10.0.0.{index}:/login")
    # La purge empêche le dictionnaire de croître indéfiniment.
    assert len(backend._hits) < 50


# ---------------------------------------------------------------------------
# L'export est une fonctionnalité d'offre
# ---------------------------------------------------------------------------
def test_free_plan_cannot_export(client, make_user):
    headers, _ = make_user("gratuit@example.com")  # plan FREE : allows_export=False
    project_id = client.post(
        "/api/v1/projects", json=PROJECT_PAYLOAD, headers=headers
    ).json()["id"]
    client.post(
        f"/api/v1/projects/{project_id}/documents/SHORT_SYNOPSIS/generate",
        json={"language": "fr"},
        headers=headers,
    )

    for path in ("pdf", "zip"):
        response = client.get(f"/api/v1/projects/{project_id}/export/{path}", headers=headers)
        assert response.status_code == 402, path
        assert response.json()["code"] == "export_not_included"


def test_paid_plan_can_export(client, make_user):
    headers, _ = make_user("pro@example.com", plan="PRO_AUTHOR")
    project_id = client.post(
        "/api/v1/projects", json=PROJECT_PAYLOAD, headers=headers
    ).json()["id"]
    client.post(
        f"/api/v1/projects/{project_id}/documents/SHORT_SYNOPSIS/generate",
        json={"language": "fr"},
        headers=headers,
    )

    assert client.get(f"/api/v1/projects/{project_id}/export/pdf", headers=headers).status_code == 200


# ---------------------------------------------------------------------------
# Non-énumération des comptes
# ---------------------------------------------------------------------------
def test_login_verifies_a_hash_even_for_unknown_accounts(client, monkeypatch):
    """Sans cela, l'écart de temps de réponse révèle les adresses inscrites."""
    client.post("/api/v1/auth/register", json=register_payload())

    calls: list[str] = []
    import app.services.auth_service as auth_service

    original = auth_service.verify_password

    def spy(plain: str, hashed: str) -> bool:
        calls.append(hashed)
        return original(plain, hashed)

    monkeypatch.setattr(auth_service, "verify_password", spy)

    client.post(
        "/api/v1/auth/login",
        json={"email": "inconnu@example.com", "password": "MotDePasse123"},
    )
    assert calls == [auth_service.DUMMY_PASSWORD_HASH]


# ----------------------------------------------------------------------
# Une variable d'environnement vide n'est pas une variable renseignée


def test_an_empty_typed_variable_falls_back_to_its_default(monkeypatch):
    """Le défaut corrigé : le premier déploiement répondait 500.

    Recopier les clés de `.env.example` dans un tableau de bord sans leurs
    valeurs — le geste le plus naturel — produisait des variables vides.
    Pydantic tentait alors de lire `''` comme un entier et refusait de
    démarrer, sur une erreur illisible depuis l'extérieur
    (`FUNCTION_INVOCATION_FAILED`).
    """
    from app.core.config import Settings

    for nom in (
        "RATE_LIMIT_AI_PER_MINUTE",
        "AI_MAX_OUTPUT_TOKENS",
        "REDIS_TIMEOUT_SECONDS",
        "SENTRY_TRACES_SAMPLE_RATE",
        "PAYMENT_PROVIDER",
        "AI_PROVIDER",
        "ENVIRONMENT",
    ):
        monkeypatch.setenv(nom, "")

    settings = Settings(_env_file=None)
    assert settings.rate_limit_ai_per_minute == 10
    assert settings.ai_max_output_tokens == 8000
    assert settings.redis_timeout_seconds == 0.25
    assert settings.sentry_traces_sample_rate == 0.0
    assert settings.payment_provider == "manual"
    assert settings.ai_provider == "mock"
    assert settings.environment == "development"


def test_an_empty_value_that_means_something_is_left_alone(monkeypatch):
    """« Vide » est une valeur pour certains réglages, et le reste.

    `REDIS_URL` vide veut dire « pas de Redis », `AI_EFFORT` vide « laisse le
    serveur décider », `CORS_ORIGINS` vide « aucune origine autorisée ».
    Leur substituer un défaut changerait le comportement demandé — et pour
    `CORS_ORIGINS`, rouvrirait `localhost` en production.
    """
    from app.core.config import Settings

    for nom in ("REDIS_URL", "AI_EFFORT", "CORS_ORIGINS", "SENTRY_DSN", "AI_MODEL"):
        monkeypatch.setenv(nom, "")

    settings = Settings(_env_file=None)
    assert settings.redis_url == ""
    assert settings.ai_effort == ""
    assert settings.cors_origins == ""
    assert settings.cors_origin_list == []
    assert settings.sentry_dsn == ""
    assert settings.ai_model == ""


def test_a_variable_that_is_set_still_wins(monkeypatch):
    """La correction ne doit pas avaler les valeurs réelles."""
    from app.core.config import Settings

    monkeypatch.setenv("RATE_LIMIT_AI_PER_MINUTE", "42")
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    settings = Settings(_env_file=None)
    assert settings.rate_limit_ai_per_minute == 42
    assert settings.ai_provider == "anthropic"
