"""Configuration du fournisseur d'IA depuis l'administration.

Un écran qui reçoit une clé d'API a deux façons d'échouer, et une seule se
voit à l'usage. La première — la clé ne s'applique pas — se remarque au
premier appel. La seconde — la clé fuit, en clair en base, dans une réponse
HTTP, dans une trace d'audit — ne se remarque jamais, jusqu'au jour où elle
coûte cher. Ces tests portent surtout sur la seconde.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.database import SessionLocal
from app.core.errors import AppError
from app.models.system import AppSetting, AuditLog
from app.models.user import User

#: Forme d'une vraie clé, sans en être une.
FAKE_KEY = "sk-ant-api03-EXEMPLE-DE-CLE-QUI-NEST-PAS-UNE-CLE-1234ABCD"


@pytest.fixture
def admin_headers(make_user):
    from app.models.enums import UserType

    headers, _ = make_user("admin.ia@example.com")
    with SessionLocal() as db:
        db.query(User).filter(User.email == "admin.ia@example.com").one().user_type = (
            UserType.ADMIN
        )
        db.commit()
    return headers


def _config(client: TestClient, headers: dict) -> dict:
    response = client.get("/api/v1/admin/ai/config", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _state(config: dict, provider: str) -> dict:
    return next(p for p in config["providers"] if p["name"] == provider)


# ----------------------------------------------------------------------
# Le chiffrement


def test_a_secret_survives_a_round_trip():
    assert decrypt_secret(encrypt_secret(FAKE_KEY)) == FAKE_KEY


def test_the_same_secret_never_produces_the_same_ciphertext():
    """Deux chiffrés identiques diraient que deux fournisseurs partagent la clé."""
    assert encrypt_secret(FAKE_KEY) != encrypt_secret(FAKE_KEY)


def test_a_rotated_server_key_says_so_instead_of_returning_nothing(monkeypatch):
    """Le silence serait pire : on chercherait une clé absente, elle est là.

    Rendre une chaîne vide ferait passer « illisible » pour « non
    configuré ». L'administrateur ressaisirait une clé... qui serait de
    nouveau illisible au redémarrage suivant, sans qu'il comprenne pourquoi.
    """
    stored = encrypt_secret(FAKE_KEY)
    monkeypatch.setattr("app.core.config.settings.secrets_key", "un-autre-secret-de-serveur")
    with pytest.raises(AppError) as unreadable:
        decrypt_secret(stored)
    assert unreadable.value.code == "secret_unreadable"


def test_a_corrupted_value_is_refused():
    with pytest.raises(AppError):
        decrypt_secret("v1:ceci-nest-pas-un-jeton")


def test_a_value_without_its_scheme_is_refused():
    """Sans préfixe de version, on lirait un futur format comme du charabia."""
    with pytest.raises(AppError):
        decrypt_secret(FAKE_KEY)


# ----------------------------------------------------------------------
# Ce que la base contient, et ce que l'API rend


def test_the_key_is_never_written_in_clear(client, admin_headers, db_session):
    """Une sauvegarde de base ne doit pas être une facture ouverte."""
    response = client.put(
        "/api/v1/admin/ai/config",
        json={"key_provider": "anthropic", "api_key": FAKE_KEY},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text

    row = db_session.execute(
        select(AppSetting).where(AppSetting.key == "ai.key.anthropic")
    ).scalar_one()
    assert FAKE_KEY not in row.value
    assert row.value.startswith("v1:")
    assert row.value_type == "secret"
    # Et elle reste relisible par l'application.
    assert decrypt_secret(row.value) == FAKE_KEY


def test_the_api_returns_a_hint_and_never_the_key(client, admin_headers):
    client.put(
        "/api/v1/admin/ai/config",
        json={"key_provider": "anthropic", "api_key": FAKE_KEY},
        headers=admin_headers,
    )
    response = client.get("/api/v1/admin/ai/config", headers=admin_headers)
    assert FAKE_KEY not in response.text
    # Quatre derniers caractères : de quoi reconnaître laquelle est en place.
    state = _state(response.json(), "anthropic")
    assert state["key_hint"] == "…ABCD"
    assert state["key_source"] == "database"
    assert state["configured"] is True


def test_the_audit_trail_records_the_change_without_the_secret(
    client, admin_headers, db_session
):
    """Une trace d'audit se conserve longtemps et se lit largement."""
    client.put(
        "/api/v1/admin/ai/config",
        json={"key_provider": "anthropic", "api_key": FAKE_KEY},
        headers=admin_headers,
    )
    entries = db_session.execute(
        select(AuditLog).where(AuditLog.action == "ai.config.updated")
    ).scalars().all()
    assert len(entries) == 1
    assert "anthropic" in entries[0].detail
    assert FAKE_KEY not in entries[0].detail
    assert "ABCD" not in entries[0].detail


def test_only_an_administrator_can_read_the_configuration(client, auth_headers):
    assert client.get("/api/v1/admin/ai/config", headers=auth_headers).status_code == 403
    assert client.get("/api/v1/admin/ai/config").status_code == 401


def test_an_ordinary_user_cannot_change_the_key(client, auth_headers):
    response = client.put(
        "/api/v1/admin/ai/config",
        json={"key_provider": "anthropic", "api_key": FAKE_KEY},
        headers=auth_headers,
    )
    assert response.status_code == 403


def test_an_unreadable_key_does_not_take_the_screen_down_with_it(
    client, admin_headers, monkeypatch
):
    """Le défaut corrigé : l'écran renvoyait une 500 et devenait inutilisable.

    C'est pourtant le seul endroit où ressaisir la clé qu'il réclame.
    Échouer ici enfermait l'exploitant dehors : le message était juste, et
    personne ne pouvait agir dessus.
    """
    client.put(
        "/api/v1/admin/ai/config",
        json={"key_provider": "anthropic", "api_key": FAKE_KEY},
        headers=admin_headers,
    )
    monkeypatch.setattr("app.core.config.settings.secrets_key", "un-autre-secret")

    response = client.get("/api/v1/admin/ai/config", headers=admin_headers)
    assert response.status_code == 200, response.text
    state = _state(response.json(), "anthropic")
    assert state["key_source"] == "unreadable"
    assert state["configured"] is False
    # Et la ressaisie fonctionne, sans avoir à effacer quoi que ce soit.
    replaced = client.put(
        "/api/v1/admin/ai/config",
        json={"key_provider": "anthropic", "api_key": "sk-ant-NOUVELLE-CLE-WXYZ"},
        headers=admin_headers,
    )
    assert _state(replaced.json(), "anthropic")["key_hint"] == "…WXYZ"


# ----------------------------------------------------------------------
# Une clé par fournisseur


def test_each_provider_keeps_its_own_key(client, admin_headers):
    """Le cœur de la demande : deux comptes chez deux sociétés.

    Passer d'Anthropic à OpenAI puis revenir ne doit pas obliger à
    ressaisir la première — ce sont deux clés, pas deux valeurs d'un même
    réglage.
    """
    client.put(
        "/api/v1/admin/ai/config",
        json={"key_provider": "anthropic", "api_key": FAKE_KEY},
        headers=admin_headers,
    )
    client.put(
        "/api/v1/admin/ai/config",
        json={"key_provider": "openai", "api_key": "sk-openai-XYZW"},
        headers=admin_headers,
    )
    config = _config(client, admin_headers)
    assert _state(config, "anthropic")["key_hint"] == "…ABCD"
    assert _state(config, "openai")["key_hint"] == "…XYZW"


def test_switching_provider_does_not_touch_the_other_key(client, admin_headers):
    client.put(
        "/api/v1/admin/ai/config",
        json={"key_provider": "anthropic", "api_key": FAKE_KEY},
        headers=admin_headers,
    )
    client.put(
        "/api/v1/admin/ai/config", json={"provider": "openai"}, headers=admin_headers
    )
    config = _config(client, admin_headers)
    assert config["active_provider"] == "openai"
    assert _state(config, "anthropic")["key_hint"] == "…ABCD"


def test_a_key_without_a_destination_is_refused(client, admin_headers):
    """Elle irait au fournisseur actif du moment — pas forcément le bon.

    Une clé Anthropic présentée à OpenAI apparaîtrait dans les journaux
    d'un tiers.
    """
    response = client.put(
        "/api/v1/admin/ai/config", json={"api_key": FAKE_KEY}, headers=admin_headers
    )
    assert response.status_code == 400
    assert response.json()["code"] == "ai_key_provider_required"


def test_the_mock_provider_refuses_a_key(client, admin_headers):
    response = client.put(
        "/api/v1/admin/ai/config",
        json={"key_provider": "mock", "api_key": FAKE_KEY},
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "ai_key_not_applicable"


def test_an_empty_key_clears_the_setting(client, admin_headers):
    client.put(
        "/api/v1/admin/ai/config",
        json={"key_provider": "anthropic", "api_key": FAKE_KEY},
        headers=admin_headers,
    )
    client.put(
        "/api/v1/admin/ai/config",
        json={"key_provider": "anthropic", "api_key": ""},
        headers=admin_headers,
    )
    state = _state(_config(client, admin_headers), "anthropic")
    assert state["key_hint"] is None
    assert state["key_source"] == "none"


# ----------------------------------------------------------------------
# Ce qui s'applique réellement


def test_the_screen_overrides_the_environment(client, admin_headers, monkeypatch):
    from app.services.ai.credentials import api_key_for

    monkeypatch.setattr("app.core.config.settings.ai_api_key", "cle-de-lenvironnement")
    client.put(
        "/api/v1/admin/ai/config",
        json={"key_provider": "anthropic", "api_key": FAKE_KEY},
        headers=admin_headers,
    )
    assert api_key_for("anthropic") == FAKE_KEY


def test_without_a_stored_key_the_environment_still_applies(monkeypatch):
    """Un déploiement qui n'ouvre jamais cet écran se comporte comme avant."""
    from app.services.ai.credentials import api_key_for

    monkeypatch.setattr("app.core.config.settings.ai_provider", "anthropic")
    monkeypatch.setattr("app.core.config.settings.ai_api_key", "cle-de-lenvironnement")
    assert api_key_for("anthropic") == "cle-de-lenvironnement"


def test_the_environment_key_belongs_to_the_active_provider_only(monkeypatch):
    """`AI_API_KEY` vient d'un compte précis : elle n'est pas interchangeable.

    La donner à OpenAI parce qu'aucune clé OpenAI n'est saisie enverrait un
    secret Anthropic chez un tiers, qui le journaliserait.
    """
    from app.services.ai.credentials import api_key_for

    monkeypatch.setattr("app.core.config.settings.ai_provider", "anthropic")
    monkeypatch.setattr("app.core.config.settings.ai_api_key", "cle-anthropic")
    assert api_key_for("openai") == ""


def test_choosing_a_provider_changes_what_gets_built(client, admin_headers, monkeypatch):
    from app.services.ai.service import build_provider

    monkeypatch.setattr("app.core.config.settings.ai_provider", "mock")
    client.put(
        "/api/v1/admin/ai/config",
        json={"provider": "anthropic", "key_provider": "anthropic", "api_key": FAKE_KEY},
        headers=admin_headers,
    )
    assert build_provider().name == "anthropic"


def test_the_answer_to_a_save_already_reflects_it(client, admin_headers):
    """Le défaut corrigé : la réponse arrivait en retard d'une modification.

    L'état était relu par une session distincte de celle de la requête, qui
    ne voyait pas encore l'écriture non validée. À l'écran, on cliquait
    « anthropic » et « mock » s'affichait en retour — la modification avait
    pourtant bien eu lieu, ce qui est pire qu'une erreur franche.
    """
    response = client.put(
        "/api/v1/admin/ai/config", json={"provider": "anthropic"}, headers=admin_headers
    )
    assert response.json()["active_provider"] == "anthropic"

    response = client.put(
        "/api/v1/admin/ai/config", json={"model": "claude-sonnet-5"}, headers=admin_headers
    )
    assert response.json()["configured_model"] == "claude-sonnet-5"

    response = client.put(
        "/api/v1/admin/ai/config",
        json={"key_provider": "openai", "api_key": "sk-openai-WXYZ"},
        headers=admin_headers,
    )
    assert _state(response.json(), "openai")["key_hint"] == "…WXYZ"


def test_an_empty_model_falls_back_to_the_provider_default(
    client, admin_headers, monkeypatch
):
    # Sans `AI_MODEL` dans l'environnement, sinon c'est lui qui s'applique —
    # et c'est le bon ordre : saisie, puis environnement, puis défaut.
    monkeypatch.setattr("app.core.config.settings.ai_model", "")
    client.put(
        "/api/v1/admin/ai/config",
        json={"provider": "anthropic", "model": "claude-sonnet-5"},
        headers=admin_headers,
    )
    assert _config(client, admin_headers)["effective_model"] == "claude-sonnet-5"

    client.put("/api/v1/admin/ai/config", json={"model": ""}, headers=admin_headers)
    config = _config(client, admin_headers)
    assert config["configured_model"] == ""
    assert config["effective_model"] == "claude-opus-5"
    assert config["model_source"] == "provider_default"


def test_the_dashboard_reports_what_the_screen_selected(
    client, admin_headers, monkeypatch
):
    """Sinon l'administration afficherait `mock` en générant chez Anthropic."""
    monkeypatch.setattr("app.core.config.settings.ai_model", "")
    client.put(
        "/api/v1/admin/ai/config",
        json={"provider": "anthropic", "key_provider": "anthropic", "api_key": FAKE_KEY},
        headers=admin_headers,
    )
    stats = client.get("/api/v1/admin/stats/ai", headers=admin_headers).json()
    assert stats["provider"] == "anthropic"
    assert stats["model"] == "claude-opus-5"


# ----------------------------------------------------------------------
# L'essai


def test_the_test_call_reports_success_and_is_audited(client, admin_headers, db_session):
    response = client.post("/api/v1/admin/ai/test", headers=admin_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["provider"] == "mock"

    entries = db_session.execute(
        select(AuditLog).where(AuditLog.action == "ai.config.tested")
    ).scalars().all()
    # Un essai dépense de l'argent : il laisse une trace, comme le reste.
    assert len(entries) == 1
    assert "succès" in entries[0].detail


def test_a_test_without_a_key_fails_without_raising(client, admin_headers):
    """L'écran doit rester utilisable pour corriger ce qu'il vient de signaler."""
    client.put(
        "/api/v1/admin/ai/config", json={"provider": "anthropic"}, headers=admin_headers
    )
    response = client.post("/api/v1/admin/ai/test", headers=admin_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is False
    assert "AI_API_KEY" in body["detail"]


def test_only_an_administrator_can_spend_money_on_a_test(client, auth_headers):
    assert client.post("/api/v1/admin/ai/test", headers=auth_headers).status_code == 403
