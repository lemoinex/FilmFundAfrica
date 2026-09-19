"""Ce que le compilateur TypeScript garantit a l'interface, ces tests le
garantissent a l'API.

Cote frontend, `en.ts` est type d'apres `fr.ts` : une cle oubliee fait echouer
`tsc`. Python n'a pas cet equivalent, alors on le reconstruit ici — parite des
deux catalogues, et verification que toute cle citee dans le code existe.
Sans cela, une traduction manquante ne se verrait qu'en production, sous la
forme d'une cle brute affichee a quelqu'un.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.core.i18n import EN, FR, parse_accept_language, plural, translate

APP = Path(__file__).resolve().parent.parent / "app"

#: Fonctions dont le premier argument est une cle de message.
ERROR_CALLS = {
    "AppError",
    "NotFoundError",
    "PermissionDeniedError",
    "AuthenticationError",
    "ConflictError",
    "QuotaExceededError",
    "AIProviderError",
    "PaymentProviderError",
}


# --- Parite des catalogues ------------------------------------------------


def test_les_deux_catalogues_ont_les_memes_cles():
    manquantes_en = sorted(set(FR) - set(EN))
    manquantes_fr = sorted(set(EN) - set(FR))

    assert not manquantes_en, f"absentes de EN : {manquantes_en}"
    assert not manquantes_fr, f"absentes de FR : {manquantes_fr}"


def test_aucune_traduction_vide():
    vides = [key for key, value in {**FR, **EN}.items() if not value.strip()]
    assert not vides, f"traductions vides : {vides}"


def test_les_variables_sont_les_memes_dans_les_deux_langues():
    """Une variable oubliee en traduction rend un message incomplet."""
    import string

    def variables(template: str) -> set[str]:
        return {
            name for _, name, _, _ in string.Formatter().parse(template) if name
        }

    divergentes = {
        key: (variables(FR[key]), variables(EN[key]))
        for key in FR
        if variables(FR[key]) != variables(EN[key])
    }
    assert not divergentes, f"variables divergentes : {divergentes}"


def test_le_francais_reste_la_langue_de_reference():
    """Toute cle nait en francais : c'est la langue dans laquelle on redige."""
    assert set(EN).issubset(set(FR))


# --- Cles citees par le code ----------------------------------------------


def _keys_used_in_source() -> set[tuple[str, str]]:
    """Cles passees a une erreur applicative ou au traducteur, avec leur fichier."""
    used: set[tuple[str, str]] = set()
    for path in APP.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            first = node.args[0]
            if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
                continue
            name = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else getattr(node.func, "attr", "")
            )
            if name in ERROR_CALLS or name == "t":
                used.add((first.value, str(path.relative_to(APP))))
    return used


def test_toutes_les_cles_citees_existent():
    inconnues = sorted(
        (key, source) for key, source in _keys_used_in_source() if key not in FR
    )
    assert not inconnues, f"clés absentes du catalogue : {inconnues}"


def test_le_scan_trouve_bien_des_cles():
    """Garde-fou : un scan qui ne trouve rien validerait n'importe quoi."""
    assert len(_keys_used_in_source()) > 40


# --- Rendu ----------------------------------------------------------------


def test_un_message_se_rend_dans_chaque_langue():
    assert translate("fr", "project.notFound") == "Projet introuvable."
    assert translate("en", "project.notFound") == "Project not found."


def test_les_variables_sont_remplies():
    rendu = translate("en", "quota.projectLimit", plan="Free", max=1)
    assert "Free" in rendu and "1" in rendu


def test_une_cle_inconnue_se_rend_elle_meme():
    """Mieux vaut une clé brute qu'une 500 : l'erreur métier reste lisible."""
    assert translate("fr", "cle.inexistante") == "cle.inexistante"


def test_un_parametre_manquant_ne_leve_pas():
    assert "{" in translate("fr", "quota.projectLimit")


def test_l_accord_suit_la_langue():
    """0 est singulier en français, pluriel en anglais."""
    from app.core.i18n import EN as en_cat
    from app.core.i18n import FR as fr_cat

    fr_cat["test.item_one"] = "{count} élément"
    fr_cat["test.item_other"] = "{count} éléments"
    en_cat["test.item_one"] = "{count} item"
    en_cat["test.item_other"] = "{count} items"
    try:
        assert plural("fr", "test.item", 0) == "0 élément"
        assert plural("en", "test.item", 0) == "0 items"
        assert plural("fr", "test.item", 1) == "1 élément"
        assert plural("en", "test.item", 1) == "1 item"
        assert plural("fr", "test.item", 2) == "2 éléments"
    finally:
        for catalog in (fr_cat, en_cat):
            catalog.pop("test.item_one", None)
            catalog.pop("test.item_other", None)


# --- Negociation de langue ------------------------------------------------


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("en", "en"),
        ("en-GB,en;q=0.9", "en"),
        ("fr-CA", "fr"),
        # La langue la mieux notee que nous savons parler l'emporte, meme
        # citee en second.
        ("de,en;q=0.8,fr;q=0.9", "fr"),
        # Aucune langue connue : c'est au deploiement de trancher.
        ("de,es", None),
        ("", None),
        (None, None),
        # Un en-tete malforme ne doit rien casser.
        ("en;q=oui", "en"),
        (";;;", None),
    ],
)
def test_negociation_accept_language(header, expected):
    assert parse_accept_language(header) == expected


# --- Bout en bout ---------------------------------------------------------


def test_l_api_repond_dans_la_langue_de_l_en_tete(client):
    """Sans session, c'est le navigateur qui dit la langue."""
    fr = client.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "Nope1234"})
    en = client.post(
        "/api/v1/auth/login",
        json={"email": "x@example.com", "password": "Nope1234"},
        headers={"Accept-Language": "en-GB,en;q=0.9"},
    )

    assert fr.json()["detail"] == "Adresse e-mail ou mot de passe incorrect."
    assert en.json()["detail"] == "Incorrect email address or password."
    # Le code, lui, ne bouge pas : c'est sur lui que le client se branche.
    assert fr.json()["code"] == en.json()["code"] == "authentication_failed"


def test_la_preference_du_compte_l_emporte_sur_l_en_tete(client, make_user):
    """Un compte en anglais reste en anglais dans un navigateur français."""
    headers, _ = make_user()
    client.put("/api/v1/users/me/profile", json={"preferred_locale": "en"}, headers=headers)

    response = client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000",
        headers={**headers, "Accept-Language": "fr-FR,fr;q=0.9"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found."


def test_un_message_de_succes_suit_aussi_la_langue(client, make_user):
    headers, _ = make_user()
    client.put("/api/v1/users/me/profile", json={"preferred_locale": "en"}, headers=headers)

    response = client.post("/api/v1/auth/logout", headers=headers)

    assert response.json()["detail"] == "Signed out."


def test_l_inscription_retient_la_langue_du_navigateur(client):
    """Sans cela, le profil naitrait sur le defaut de la colonne, indiscernable
    d'un choix — et l'API repondrait en francais a qui vient de lire en anglais."""
    from tests.conftest import pending_verification_token, register_payload

    client.post(
        "/api/v1/auth/register",
        json=register_payload("anglophone@example.com"),
        headers={"Accept-Language": "en-GB,en;q=0.9"},
    )
    verified = client.post(
        "/api/v1/auth/verify-email",
        json={"token": pending_verification_token("anglophone@example.com")},
    )

    assert verified.json()["user"]["profile"]["preferred_locale"] == "en"

    # Et l'API lui parle anglais, sans qu'il ait rien a demander.
    headers = {"Authorization": f"Bearer {verified.json()['access_token']}"}
    response = client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000", headers=headers)
    assert response.json()["detail"] == "Project not found."


def test_les_erreurs_de_validation_suivent_la_langue(client):
    response = client.post(
        "/api/v1/auth/login", json={}, headers={"Accept-Language": "en"}
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid data."


# --- Libelles calcules par le serveur -------------------------------------


def test_les_criteres_de_maturite_suivent_la_langue(client, make_user):
    """Le score est calcule par le serveur : l'interface ne peut que le relire."""
    headers, _ = make_user()
    created = client.post(
        "/api/v1/projects",
        json={"title": "Les Rives du Wouri", "project_type": "DOCUMENTARY"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    project = created.json()

    fr = client.get(f"/api/v1/projects/{project['id']}/score", headers=headers).json()
    # La preference du compte prime sur l'en-tete : c'est elle qu'on bascule.
    client.put("/api/v1/users/me/profile", json={"preferred_locale": "en"}, headers=headers)
    en = client.get(f"/api/v1/projects/{project['id']}/score", headers=headers).json()

    assert fr["total"] == en["total"], "la langue ne doit pas changer la note"

    labels_fr = {c["key"]: c["label"] for c in fr["criteria"]}
    labels_en = {c["key"]: c["label"] for c in en["criteria"]}
    assert labels_fr["vision"] == "Vision artistique"
    assert labels_en["vision"] == "Artistic vision"

    details_en = {c["key"]: c["detail"] for c in en["criteria"]}
    # Le detail enumere des champs : chaque fragment doit etre traduit aussi.
    assert "the logline" in details_en["concept"]
    assert details_en["characters"] == "No character entered."
    assert any("Enter at least the protagonist" in item for item in en["improvements"])


def test_les_criteres_de_compatibilite_suivent_la_langue(client, make_user, db_session):
    # Une offre qui inclut le rapprochement : ce test porte sur la langue des
    # critères, pas sur la garde commerciale qui les précède.
    headers, _ = make_user(plan="PRO_AUTHOR")
    created = client.post(
        "/api/v1/projects",
        json={"title": "Le Fleuve", "country": "Sénégal", "project_type": "DOCUMENTARY"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    project = created.json()

    from app.models.enums import FundingCategory, FundingStatus
    from app.models.funding import FundingOpportunity

    db_session.add(
        FundingOpportunity(
            name="Fonds test",
            organization="Organisme test",
            category=FundingCategory.FUND,
            status=FundingStatus.OPEN,
            eligible_countries="Mali",
            source_url="https://exemple.invalid/appel",
            source_name="Site officiel",
        )
    )
    db_session.commit()

    client.put("/api/v1/users/me/profile", json={"preferred_locale": "en"}, headers=headers)
    response = client.post(
        f"/api/v1/projects/{project['id']}/match-funding", headers=headers
    )
    assert response.status_code == 200, response.text
    en = response.json()

    criteria = {c["key"]: c for c in en["results"][0]["criteria"]}
    assert criteria["country"]["label"] == "Eligible country"
    assert criteria["country"]["detail"] == "Sénégal is not among the eligible countries (Mali)."
    assert criteria["country"]["state"] == "unmet"


# --- Notifications --------------------------------------------------------


def test_une_notification_est_relue_dans_la_langue_du_lecteur(client, make_user, db_session):
    """Écrite une fois, relue peut-être dans une autre langue."""
    from app.models.enums import NotificationType
    from app.services.notification_service import build_notification

    headers, data = make_user()
    db_session.add(
        build_notification(
            user_id=data["user"]["id"],
            notification_type=NotificationType.INCOMPLETE_FILE,
            title_key="notification.incompleteFile.title",
            body_key="notification.incompleteFile.body",
            params={"project": "Taxi 237", "score": 42},
        )
    )
    db_session.commit()

    fr = client.get("/api/v1/notifications", headers=headers).json()[0]
    assert fr["title"] == "Votre dossier est incomplet"
    assert "Le projet « Taxi 237 » atteint 42/100." in fr["body"]

    client.put("/api/v1/users/me/profile", json={"preferred_locale": "en"}, headers=headers)
    en = client.get("/api/v1/notifications", headers=headers).json()[0]
    assert en["title"] == "Your package is incomplete"
    assert "The “Taxi 237” project scores 42/100." in en["body"]

    # Le tableau de bord lit les mêmes notifications, par un autre chemin.
    tableau = client.get("/api/v1/dashboard", headers=headers).json()
    assert tableau["notifications"][0]["title"] == "Your package is incomplete"


def test_une_notification_sans_cle_garde_son_texte(client, make_user, db_session):
    """Celles écrites avant cette mécanique n'ont que leur texte : on le rend.

    Mieux vaut une phrase dans la mauvaise langue qu'une notification vide.
    """
    from app.models.enums import NotificationType
    from app.models.system import Notification

    headers, data = make_user()
    db_session.add(
        Notification(
            user_id=data["user"]["id"],
            notification_type=NotificationType.SYSTEM,
            title="Ancienne notification",
            body="Écrite avant l'internationalisation.",
        )
    )
    db_session.commit()

    client.put("/api/v1/users/me/profile", json={"preferred_locale": "en"}, headers=headers)
    lue = client.get("/api/v1/notifications", headers=headers).json()[0]

    assert lue["title"] == "Ancienne notification"
    assert lue["body"] == "Écrite avant l'internationalisation."


def test_le_texte_stocke_reste_en_langue_de_reference(db_session):
    """`title` sert de cache et à la déduplication : il doit rester rempli."""
    from app.services.notification_service import build_notification

    notification = build_notification(
        user_id="peu-importe",
        title_key="notification.deadlineSoon.title",
        body_key="notification.deadlineSoon.body",
        params={
            "days": 7,
            "opportunity": "Fonds A",
            "organization": "Organisme A",
            "date": "01/12/2026",
            "project": "Le Fleuve",
        },
    )

    assert notification.title == "Échéance dans 7 jours — Fonds A"
    assert "Fonds A" in notification.body
