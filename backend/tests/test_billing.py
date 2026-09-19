"""Tests du cycle d'abonnement : paiement, activation, résiliation, échéance.

Trois propriétés portent le module et sont testées en priorité : un paiement
non abouti n'accorde rien, une notification rejouée ne prolonge pas
l'abonnement, et une notification non signée est refusée.

**Le module s'exécute en mode `public`.** Le cycle commercial appartient à la
phase commerciale : pendant la bêta privée la souscription est fermée, et un
module qui tournerait dans ce mode ne vérifierait plus que la fermeture.
Elle a ses propres tests, en fin de fichier, qui posent le mode interne
explicitement.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from app.core.database import SessionLocal
from app.models.billing import Subscription
from app.models.enums import PaymentStatus, PlanCode, SubscriptionStatus
from app.models.payment import Payment
from app.models.user import User
from app.services.payments import sign_payload
from app.services.subscription_service import SubscriptionService


@pytest.fixture(autouse=True)
def _phase_commerciale(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.platform_mode", "public")


def _checkout(client, headers, plan="PRO_AUTHOR", **body) -> dict:
    payload = {"plan_code": plan}
    payload.update(body)
    response = client.post("/api/v1/billing/checkout", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _notify(client, reference: str, status: str = "SUCCEEDED", **extra):
    """Envoie une notification signée, comme le ferait le prestataire."""
    payload = {"reference": reference, "status": status}
    payload.update(extra)
    body = json.dumps(payload).encode("utf-8")
    return client.post(
        "/api/v1/billing/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Payment-Signature": sign_payload(body),
        },
    )


def _plan_of(email: str) -> str:
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).one()
        return str(user.subscription.plan.code)


# ---------------------------------------------------------------------------
# Offres
# ---------------------------------------------------------------------------
def test_plans_are_served_from_the_database(client, auth_headers):
    plans = client.get("/api/v1/billing/plans", headers=auth_headers).json()
    codes = {plan["code"] for plan in plans}
    assert {"FREE", "PRO_AUTHOR", "PRODUCER"} <= codes
    # Les prix ne sont jamais codés en dur côté frontend.
    pro = next(plan for plan in plans if plan["code"] == "PRO_AUTHOR")
    assert pro["price_amount"] > 0
    assert pro["price_currency"]


def test_a_new_account_starts_on_the_free_plan(client, make_user):
    headers, _ = make_user("depart@example.com")
    subscription = client.get("/api/v1/billing/subscription", headers=headers).json()
    assert subscription["plan"]["code"] == "FREE"
    assert subscription["is_active"] is True


# ---------------------------------------------------------------------------
# Un paiement donne des droits, il ne les suppose pas
# ---------------------------------------------------------------------------
def test_opening_a_checkout_grants_nothing_yet(client, make_user):
    headers, _ = make_user("attente@example.com")
    result = _checkout(client, headers)

    assert result["payment"]["status"] == "PENDING"
    # L'offre n'a pas bougé tant que le paiement n'a pas abouti.
    assert _plan_of("attente@example.com") == "FREE"
    assert (
        client.get("/api/v1/billing/subscription", headers=headers).json()["plan"]["code"]
        == "FREE"
    )


def test_a_successful_payment_activates_the_plan_and_reloads_credits(client, make_user):
    headers, _ = make_user("abonne@example.com")
    payment = _checkout(client, headers)["payment"]

    assert _notify(client, payment["provider_reference"]).status_code == 200

    subscription = client.get("/api/v1/billing/subscription", headers=headers).json()
    assert subscription["plan"]["code"] == "PRO_AUTHOR"
    assert subscription["is_active"] is True
    assert subscription["current_period_end"] is not None
    # Les crédits de la nouvelle offre sont accordés immédiatement.
    assert subscription["ai_credits_remaining"] == subscription["plan"]["monthly_ai_credits"]


def test_a_failed_payment_leaves_the_account_where_it_was(client, make_user):
    headers, _ = make_user("echec@example.com")
    payment = _checkout(client, headers)["payment"]

    response = _notify(
        client, payment["provider_reference"], status="FAILED", failure_reason="Solde insuffisant"
    )
    assert response.status_code == 200

    assert _plan_of("echec@example.com") == "FREE"
    mine = client.get("/api/v1/billing/payments", headers=headers).json()
    assert mine[0]["status"] == "FAILED"
    assert mine[0]["failure_reason"] == "Solde insuffisant"


# ---------------------------------------------------------------------------
# Idempotence : tous les prestataires renvoient la même notification
# ---------------------------------------------------------------------------
def test_a_replayed_notification_does_not_extend_the_subscription(client, make_user):
    headers, _ = make_user("rejeu@example.com")
    payment = _checkout(client, headers)["payment"]

    _notify(client, payment["provider_reference"])
    first = client.get("/api/v1/billing/subscription", headers=headers).json()

    for _ in range(3):
        assert _notify(client, payment["provider_reference"]).status_code == 200

    second = client.get("/api/v1/billing/subscription", headers=headers).json()
    assert second["current_period_end"] == first["current_period_end"]

    # Et une seule ligne de paiement, pas quatre.
    assert len(client.get("/api/v1/billing/payments", headers=headers).json()) == 1


def test_a_late_failure_cannot_undo_a_completed_payment(client, make_user):
    """Un statut final ne se rejoue pas : l'abonnement payé reste acquis."""
    headers, _ = make_user("tardif@example.com")
    payment = _checkout(client, headers)["payment"]
    _notify(client, payment["provider_reference"])

    _notify(client, payment["provider_reference"], status="FAILED")

    assert _plan_of("tardif@example.com") == "PRO_AUTHOR"
    assert client.get("/api/v1/billing/payments", headers=headers).json()[0]["status"] == (
        "SUCCEEDED"
    )


# ---------------------------------------------------------------------------
# Authenticité des notifications
# ---------------------------------------------------------------------------
def test_an_unsigned_notification_is_refused(client, make_user):
    """Sans cette vérification, n'importe qui s'offrirait un abonnement."""
    headers, _ = make_user("faussaire@example.com")
    payment = _checkout(client, headers)["payment"]

    response = client.post(
        "/api/v1/billing/webhook",
        json={"reference": payment["provider_reference"], "status": "SUCCEEDED"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_payment_signature"
    assert _plan_of("faussaire@example.com") == "FREE"


def test_a_tampered_notification_is_refused(client, make_user):
    headers, _ = make_user("falsifie@example.com")
    payment = _checkout(client, headers)["payment"]

    signed = json.dumps({"reference": payment["provider_reference"], "status": "FAILED"}).encode()
    tampered = json.dumps(
        {"reference": payment["provider_reference"], "status": "SUCCEEDED"}
    ).encode()

    response = client.post(
        "/api/v1/billing/webhook",
        content=tampered,
        headers={"Content-Type": "application/json", "X-Payment-Signature": sign_payload(signed)},
    )
    assert response.status_code == 401
    assert _plan_of("falsifie@example.com") == "FREE"


def test_a_notification_for_an_unknown_payment_is_a_404(client):
    assert _notify(client, "mock_inexistant").status_code == 404


# ---------------------------------------------------------------------------
# Refus prévisibles
# ---------------------------------------------------------------------------
def test_the_free_plan_cannot_be_paid_for(client, make_user):
    headers, _ = make_user("gratuit.checkout@example.com")
    response = client.post(
        "/api/v1/billing/checkout", json={"plan_code": "FREE"}, headers=headers
    )
    assert response.status_code == 400
    assert response.json()["code"] == "plan_is_free"


def test_subscribing_twice_to_the_same_plan_is_refused(client, make_user):
    headers, _ = make_user("deja.abonne@example.com")
    payment = _checkout(client, headers)["payment"]
    _notify(client, payment["provider_reference"])

    response = client.post(
        "/api/v1/billing/checkout", json={"plan_code": "PRO_AUTHOR"}, headers=headers
    )
    assert response.status_code == 400
    assert response.json()["code"] == "plan_already_active"


def test_paying_for_a_higher_plan_while_subscribed_is_allowed(client, make_user):
    headers, _ = make_user("montee@example.com")
    payment = _checkout(client, headers)["payment"]
    _notify(client, payment["provider_reference"])

    upgrade = _checkout(client, headers, plan="PRODUCER")["payment"]
    _notify(client, upgrade["provider_reference"])

    assert _plan_of("montee@example.com") == "PRODUCER"


# ---------------------------------------------------------------------------
# Résiliation et échéance
# ---------------------------------------------------------------------------
def test_cancelling_keeps_access_until_the_end_of_the_paid_period(client, make_user):
    headers, _ = make_user("resiliation@example.com")
    payment = _checkout(client, headers)["payment"]
    _notify(client, payment["provider_reference"])

    response = client.post("/api/v1/billing/cancel", headers=headers)
    assert response.status_code == 200

    subscription = client.get("/api/v1/billing/subscription", headers=headers).json()
    assert subscription["status"] == "CANCELLED"
    # Résilier ne coupe pas : la période payée va à son terme…
    assert subscription["plan"]["code"] == "PRO_AUTHOR"
    assert subscription["is_active"] is True
    # …mais elle ne sera pas reconduite.
    assert subscription["is_renewing"] is False


def test_resubscribing_after_cancelling_reactivates_the_renewal(client, make_user):
    """Une résiliation doit pouvoir se défaire en payant de nouveau."""
    headers, _ = make_user("retour@example.com")
    payment = _checkout(client, headers)["payment"]
    _notify(client, payment["provider_reference"])
    client.post("/api/v1/billing/cancel", headers=headers)

    again = _checkout(client, headers)["payment"]
    _notify(client, again["provider_reference"])

    subscription = client.get("/api/v1/billing/subscription", headers=headers).json()
    assert subscription["status"] == "ACTIVE"
    assert subscription["is_renewing"] is True


def test_cancelling_a_free_account_is_refused(client, make_user):
    headers, _ = make_user("rien.a.resilier@example.com")
    response = client.post("/api/v1/billing/cancel", headers=headers)
    assert response.status_code == 400
    assert response.json()["code"] == "no_paid_subscription"


def test_an_expired_period_falls_back_to_the_free_plan(client, make_user, db_session):
    headers, _ = make_user("echeance@example.com")
    payment = _checkout(client, headers)["payment"]
    _notify(client, payment["provider_reference"])
    assert _plan_of("echeance@example.com") == "PRO_AUTHOR"

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "echeance@example.com").one()
        subscription = db.get(Subscription, user.subscription.id)
        subscription.current_period_end = datetime.now(UTC) - timedelta(days=1)
        db.commit()

    assert SubscriptionService(db_session).expire_due() >= 1

    assert _plan_of("echeance@example.com") == "FREE"
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "echeance@example.com").one()
        assert user.subscription.status is SubscriptionStatus.EXPIRED


def test_a_running_period_is_left_alone(client, make_user, db_session):
    headers, _ = make_user("en.cours@example.com")
    payment = _checkout(client, headers)["payment"]
    _notify(client, payment["provider_reference"])

    SubscriptionService(db_session).expire_due()
    assert _plan_of("en.cours@example.com") == "PRO_AUTHOR"


def test_renewing_early_extends_instead_of_shortening(client, make_user, db_session):
    """Payer plus tôt ne doit jamais faire perdre des jours déjà payés."""
    headers, _ = make_user("renouvellement@example.com")
    first = _checkout(client, headers)["payment"]
    _notify(client, first["provider_reference"])
    before = client.get("/api/v1/billing/subscription", headers=headers).json()

    second = _checkout(client, headers, plan="PRODUCER")["payment"]
    _notify(client, second["provider_reference"])
    after = client.get("/api/v1/billing/subscription", headers=headers).json()

    assert after["current_period_end"] > before["current_period_end"]


# ---------------------------------------------------------------------------
# Isolation et administration
# ---------------------------------------------------------------------------
def test_payments_are_scoped_to_their_owner(client, make_user):
    alice, _ = make_user("alice.paiement@example.com")
    bob, _ = make_user("bob.paiement@example.com")
    _checkout(client, alice)

    assert client.get("/api/v1/billing/payments", headers=bob).json() == []


def test_an_offline_payment_is_validated_by_an_administrator(client, make_user, db_session):
    """Contrepartie du mode `manual` : la validation est humaine, et tracée."""
    from app.models.enums import UserType

    headers, registered = make_user("hors.ligne@example.com")
    payment = _checkout(client, headers)["payment"]

    admin_headers, admin = make_user("admin.paiement@example.com")
    with SessionLocal() as db:
        db.query(User).filter(User.email == "admin.paiement@example.com").one().user_type = (
            UserType.ADMIN
        )
        db.commit()

    response = client.post(
        f"/api/v1/admin/payments/{payment['id']}/validate", headers=admin_headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "SUCCEEDED"
    assert _plan_of("hors.ligne@example.com") == "PRO_AUTHOR"

    stored = db_session.get(Payment, payment["id"])
    db_session.refresh(stored)
    # Qui a validé reste inscrit : un encaissement hors ligne se justifie.
    assert stored.provider_payload["validated_by"] == "admin.paiement@example.com"
    assert registered is not None
    assert admin is not None


def test_validating_a_settled_payment_twice_is_refused(client, make_user):
    from app.models.enums import UserType

    headers, _ = make_user("double.validation@example.com")
    payment = _checkout(client, headers)["payment"]
    _notify(client, payment["provider_reference"])

    admin_headers, _ = make_user("admin.double@example.com")
    with SessionLocal() as db:
        db.query(User).filter(User.email == "admin.double@example.com").one().user_type = (
            UserType.ADMIN
        )
        db.commit()

    response = client.post(
        f"/api/v1/admin/payments/{payment['id']}/validate", headers=admin_headers
    )
    assert response.status_code == 400
    assert response.json()["code"] == "payment_already_settled"


def test_the_admin_payment_list_is_reserved_to_administrators(client, make_user):
    headers, _ = make_user("curieux@example.com")
    assert client.get("/api/v1/admin/payments", headers=headers).status_code == 403


# ---------------------------------------------------------------------------
# Garde-fous de configuration
# ---------------------------------------------------------------------------
def test_production_refuses_a_simulated_payment_provider():
    from app.core.config import Settings

    with pytest.raises(ValueError, match="PAYMENT_PROVIDER=mock"):
        Settings(
            environment="production",
            debug=False,
            jwt_secret="a" * 64,
            ai_provider="mock",
            payment_provider="mock",
            _env_file=None,
        )


def test_payment_statuses_are_final_except_pending():
    assert not PaymentStatus.PENDING.is_final
    for status in (
        PaymentStatus.SUCCEEDED,
        PaymentStatus.FAILED,
        PaymentStatus.CANCELLED,
        PaymentStatus.REFUNDED,
    ):
        assert status.is_final


def test_every_plan_code_exists_in_database(client, auth_headers):
    plans = client.get("/api/v1/billing/plans", headers=auth_headers).json()
    assert {plan["code"] for plan in plans} == {code.value for code in PlanCode}


# ----------------------------------------------------------------------
# Une offre ne promet que ce que le serveur applique


def test_no_plan_advertises_a_feature_that_does_not_exist():
    """Le défaut corrigé : « budget avancé, collaboration d'équipe » à 100 000 XAF.

    Ni l'un ni l'autre n'existe dans le produit. Les drapeaux restent en base
    pour le jour où ces fonctionnalités seront écrites, mais une description
    payante ne peut pas les annoncer avant.
    """
    from app.services.credit_service import DEFAULT_PLANS

    interdits = ("collaboration", "budget avancé", "budget avance")
    for plan in DEFAULT_PLANS:
        description = plan["description"].lower()
        for mot in interdits:
            assert mot not in description, f"{plan['code']} annonce « {mot} »"


def test_the_enforced_flags_are_the_ones_the_plans_differ_on():
    """Ce qui distingue les offres doit être ce que le serveur vérifie.

    `allows_collaboration` et `allows_advanced_budget` ne gardent rien : si un
    jour ils deviennent la seule différence entre deux offres, la plus chère
    ne vaudra rien de plus que l'autre.
    """
    from app.services.credit_service import DEFAULT_PLANS

    appliques = ("max_projects", "monthly_ai_credits", "allows_export", "allows_matching")
    for plan in DEFAULT_PLANS:
        autres = [p for p in DEFAULT_PLANS if p["code"] != plan["code"]]
        for autre in autres:
            if all(plan[champ] == autre[champ] for champ in appliques):
                raise AssertionError(
                    f"« {plan['name']} » et « {autre['name']} » ne se distinguent par "
                    "aucune contrainte réellement appliquée"
                )


# ----------------------------------------------------------------------
# Bêta privée : la souscription est fermée, rien n'est supprimé


@pytest.fixture
def beta(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.platform_mode", "internal")


def test_subscribing_is_closed_during_the_private_beta(client, make_user, beta):
    headers, _ = make_user("beta.souscrit@example.com")
    response = client.post(
        "/api/v1/billing/checkout", json={"plan_code": "PRO_AUTHOR"}, headers=headers
    )
    assert response.status_code == 403
    assert response.json()["code"] == "subscription_closed"


def test_an_administrator_cannot_subscribe_either(client, make_user, beta):
    """Ce n'est pas une contrainte d'offre, c'est l'état du produit.

    Les autres restrictions s'effacent pour un administrateur en bêta ; la
    souscription, non — il n'y a rien à vendre pendant la phase interne, et
    laisser passer un paiement encaisserait pour un service non commercialisé.
    """
    from app.models.enums import UserType

    headers, _ = make_user("beta.admin@example.com")
    with SessionLocal() as db:
        db.query(User).filter(
            User.email == "beta.admin@example.com"
        ).one().user_type = UserType.ADMIN
        db.commit()

    response = client.post(
        "/api/v1/billing/checkout", json={"plan_code": "PRODUCER"}, headers=headers
    )
    assert response.status_code == 403
    assert response.json()["code"] == "subscription_closed"


def test_simulating_a_payment_is_closed_too(client, make_user, beta):
    """Sinon on contournerait la fermeture par la porte de développement."""
    headers, _ = make_user("beta.simule@example.com")
    response = client.post(
        "/api/v1/billing/simulate/une-reference", headers=headers
    )
    assert response.status_code == 403
    assert response.json()["code"] == "subscription_closed"


def test_the_offers_remain_visible_and_readable(client, make_user, beta):
    """Rien n'est supprimé : les offres restent lisibles, seule l'action ferme."""
    headers, _ = make_user("beta.lecture@example.com")
    plans = client.get("/api/v1/billing/plans", headers=headers)
    assert plans.status_code == 200
    assert {p["code"] for p in plans.json()} == {"FREE", "PRO_AUTHOR", "PRODUCER"}
    assert client.get("/api/v1/billing/subscription", headers=headers).status_code == 200
    assert client.get("/api/v1/billing/payments", headers=headers).status_code == 200


def test_cancelling_an_existing_subscription_stays_possible(client, make_user, beta):
    """Empêcher quelqu'un de résilier serait abusif, et sans rapport avec la bêta."""
    headers, _ = make_user("beta.resilie@example.com", plan="PRO_AUTHOR")
    assert client.post("/api/v1/billing/cancel", headers=headers).status_code == 200


def test_a_payment_already_under_way_can_still_settle(client, make_user, monkeypatch):
    """Le webhook reste ouvert : encaisser sans rien accorder serait pire.

    Un paiement engagé avant la bascule doit pouvoir aboutir — sa
    notification arrive après, quand la bêta est déjà en place.
    """
    monkeypatch.setattr("app.core.config.settings.platform_mode", "public")
    headers, _ = make_user("beta.encours@example.com")
    payment = _checkout(client, headers)["payment"]

    monkeypatch.setattr("app.core.config.settings.platform_mode", "internal")
    assert _notify(client, payment["provider_reference"]).status_code == 200
    assert _plan_of("beta.encours@example.com") == "PRO_AUTHOR"


def test_the_profile_says_the_subscription_is_closed(client, make_user, beta):
    """L'interface doit pouvoir le dire avant le clic, pas après le refus."""
    headers, _ = make_user("beta.profil@example.com")
    assert client.get(
        "/api/v1/auth/me", headers=headers
    ).json()["subscription_open"] is False


def test_the_commercial_phase_reopens_it(client, make_user, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.platform_mode", "public")
    headers, _ = make_user("public.souscrit@example.com")
    assert client.post(
        "/api/v1/billing/checkout", json={"plan_code": "PRO_AUTHOR"}, headers=headers
    ).status_code == 201
