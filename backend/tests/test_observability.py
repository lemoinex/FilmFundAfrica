"""Ce que le suivi des erreurs a le droit d'emporter — et ce qu'il n'a pas.

Un rapport d'erreur part chez un tiers. Ces tests fixent la limite : les
identifiants, les donnees personnelles et le travail des auteurs ne
franchissent jamais `before_send`.
"""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.core.observability import (
    REDACTED,
    before_send,
    scrub,
    scrub_text,
    sentry_status,
    setup_sentry,
)

#: DSN syntaxiquement valide et adresse a personne : `init` ne declenche
#: aucune requete tant qu'aucun evenement n'est capture.
FAKE_DSN = "https://public@exemple.invalid/1"


@pytest.fixture
def sentry_actif(monkeypatch):
    """Active le suivi le temps d'un test, puis referme le client."""
    import sentry_sdk

    from app.core import observability

    monkeypatch.setattr(settings, "sentry_dsn", FAKE_DSN)
    monkeypatch.setattr(observability, "_enabled", False)
    yield setup_sentry()
    sentry_sdk.get_client().close()
    monkeypatch.setattr(observability, "_enabled", False)


# --- Expurgation ----------------------------------------------------------


def test_les_identifiants_sont_retires():
    event = {
        "request": {
            "headers": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.charge-utile",
                "Cookie": "session=abc",
                "X-Payment-Signature": "9f2c...",
                "User-Agent": "Mozilla/5.0",
            }
        }
    }
    headers = before_send(event)["request"]["headers"]

    assert headers["Authorization"] == REDACTED
    assert headers["Cookie"] == REDACTED
    assert headers["X-Payment-Signature"] == REDACTED
    # Ce qui n'identifie personne reste : sinon le rapport ne sert plus a rien.
    assert headers["User-Agent"] == "Mozilla/5.0"


def test_les_mots_de_passe_sont_retires_a_toute_profondeur():
    event = {
        "extra": {
            "corps": {"email": "autrice@exemple.org", "password": "hunter2"},
            "utilisateur": {"hashed_password": "$2b$12$..."},
        }
    }
    extra = before_send(event)["extra"]

    assert extra["corps"]["password"] == REDACTED
    assert extra["utilisateur"]["hashed_password"] == REDACTED


def test_le_travail_des_auteurs_ne_part_pas():
    """Synopsis, scenario, budget : rien de tout cela n'a sa place la-bas."""
    event = {
        "extra": {
            "projet": {
                "title": "Les Rives du Wouri",
                "logline": "Une cheffe opératrice revient filmer le fleuve.",
                "long_synopsis": "Acte I. ...",
            }
        }
    }
    projet = before_send(event)["extra"]["projet"]

    assert projet["logline"] == REDACTED
    assert projet["long_synopsis"] == REDACTED
    # Le titre reste : c'est ce qui permet de retrouver le dossier en cause.
    assert projet["title"] == "Les Rives du Wouri"


def test_les_donnees_personnelles_sont_retirees_du_texte_libre():
    message = (
        "échec pour autrice@exemple.org, rappelée au +237 6 99 00 11 22, "
        "lien https://app.exemple.org/verifier-email?token=abcdef123456&x=1"
    )
    expurge = scrub_text(message)

    assert "autrice@exemple.org" not in expurge
    assert "6 99 00 11 22" not in expurge
    assert "abcdef123456" not in expurge
    # Le jeton disparait, pas l'URL : on garde de quoi situer l'erreur.
    assert "verifier-email?token=" in expurge
    assert "&x=1" in expurge


def test_les_listes_sont_parcourues():
    valeurs = scrub({"journal": [{"token": "abc"}, {"note": "ok"}]})

    assert valeurs["journal"][0]["token"] == REDACTED
    assert valeurs["journal"][1]["note"] == "ok"


def test_le_message_dune_exception_est_expurge():
    event = {
        "exception": {
            "values": [
                {
                    "type": "ValueError",
                    "value": "adresse déjà utilisée : autrice@exemple.org",
                }
            ]
        }
    }
    valeur = before_send(event)["exception"]["values"][0]

    assert valeur["type"] == "ValueError"
    assert "autrice@exemple.org" not in valeur["value"]


def test_les_valeurs_non_textuelles_traversent_intactes():
    """Codes et durees doivent rester lisibles : sans eux, plus de diagnostic."""
    event = {"extra": {"status_code": 500, "duration_ms": 1240, "retried": True}}

    assert before_send(event)["extra"] == {
        "status_code": 500,
        "duration_ms": 1240,
        "retried": True,
    }


# --- Activation -----------------------------------------------------------


def test_sans_dsn_rien_nest_initialise(monkeypatch):
    monkeypatch.setattr(settings, "sentry_dsn", "")

    assert setup_sentry() is False
    assert sentry_status() == "disabled"


def test_avec_dsn_le_client_applique_les_bons_reglages(sentry_actif):
    import sentry_sdk

    assert sentry_actif is True
    assert sentry_status() == "active"

    options = sentry_sdk.get_client().options
    assert options["before_send"] is before_send
    # Ce que l'expurgation par nom de cle ne peut pas couvrir est ferme a la
    # source : les variables locales portent le contenu des dossiers sous les
    # noms de variables du code, qu'aucune liste ne peut enumerer.
    assert options["send_default_pii"] is False
    assert options["max_request_body_size"] == "never"
    assert options["include_local_variables"] is False


def test_letiquette_de_requete_est_posee(sentry_actif):
    import sentry_sdk

    from app.core.observability import tag_request

    tag_request("f00dcafe")

    # L'etiquette est verifiee sur l'evenement produit, pas sur l'etat interne
    # du SDK : c'est ce qui part reellement.
    event: dict = {}
    sentry_sdk.get_isolation_scope().apply_to_event(event, {})
    assert event["tags"]["request_id"] == "f00dcafe"


def test_letiquette_de_requete_ne_fait_rien_sans_sentry(monkeypatch):
    """Le cas courant : ni DSN, ni cout a chaque requete."""
    from app.core import observability

    monkeypatch.setattr(observability, "_enabled", False)

    assert observability.tag_request("f00dcafe") is None
