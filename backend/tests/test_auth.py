"""Tests d'authentification et de securite des comptes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tests.conftest import (
    pending_verification_token,
    register_and_verify,
    register_payload,
)


def test_registration_does_not_open_a_session(client):
    """Rien n'est accordé avant que l'adresse ne soit confirmée."""
    response = client.post("/api/v1/auth/register", json=register_payload())
    assert response.status_code == 202
    body = response.json()
    assert "access_token" not in body
    assert "refresh_token" not in body


def test_verifying_the_email_opens_the_session(client):
    data = register_and_verify(client)
    assert data["access_token"] and data["refresh_token"]
    assert data["user"]["email"] == "user@example.com"
    assert data["user"]["profile"]["first_name"] == "Aïcha"
    # Le plan gratuit accorde des credits IA des la confirmation.
    assert data["user"]["ai_credits_remaining"] >= 1


def test_password_is_never_returned(client):
    response = client.post("/api/v1/auth/register", json=register_payload())
    assert "password" not in response.text
    assert "hashed_password" not in response.text


def test_registration_answers_the_same_for_a_free_and_a_taken_address(client):
    """Le défaut corrigé : un 409 permettait de tester si une adresse est inscrite."""
    first = client.post("/api/v1/auth/register", json=register_payload())
    second = client.post("/api/v1/auth/register", json=register_payload())

    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()


def test_registering_on_a_taken_address_changes_nothing(client):
    """Une inscription sur l'adresse d'autrui ne doit rien lui prendre."""
    register_and_verify(client)

    intrus = client.post(
        "/api/v1/auth/register",
        json=register_payload(password="MotDePasseIntrus1", first_name="Intrus"),
    )
    assert intrus.status_code == 202

    # Le mot de passe du titulaire est intact, et son profil n'a pas bougé.
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "MotDePasse123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["profile"]["first_name"] == "Aïcha"
    # Et le mot de passe choisi par l'intrus ne vaut rien.
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "MotDePasseIntrus1"},
    ).status_code == 401


def test_registration_timing_does_not_reveal_a_taken_address(client):
    """Sans hachage dans les deux branches, l'écart de temps refait l'oracle.

    La branche « adresse déjà prise » ne crée rien : si elle ne hachait pas de
    mot de passe, elle répondrait en quelques millisecondes là où l'autre en
    prend deux cents.
    """
    import time

    def _duration(email: str) -> float:
        start = time.perf_counter()
        client.post("/api/v1/auth/register", json=register_payload(email))
        return time.perf_counter() - start

    _duration("occupee@example.com")  # rend l'adresse indisponible
    taken = min(_duration("occupee@example.com") for _ in range(3))
    free = min(_duration(f"libre{index}@example.com") for index in range(3))

    # Bornes larges : on vérifie l'ordre de grandeur, pas une égalité stricte.
    assert taken > free / 3, f"branche « adresse prise » trop rapide : {taken:.3f}s vs {free:.3f}s"


def test_an_unverified_account_cannot_log_in(client):
    client.post("/api/v1/auth/register", json=register_payload())
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "MotDePasse123"},
    )
    assert response.status_code == 401
    # Ce code n'est atteignable qu'avec le bon mot de passe : il ne révèle rien
    # à qui ne connaît pas déjà le compte.
    assert response.json()["code"] == "email_not_verified"


def test_a_verification_link_works_only_once(client):
    client.post("/api/v1/auth/register", json=register_payload())
    token = pending_verification_token("user@example.com")

    assert client.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 200
    assert client.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 401


def test_an_expired_verification_link_is_refused(client):
    from app.core.database import SessionLocal
    from app.core.security import hash_url_token
    from app.models.user import EmailVerificationToken

    client.post("/api/v1/auth/register", json=register_payload())
    token = pending_verification_token("user@example.com")

    with SessionLocal() as db:
        stored = db.query(EmailVerificationToken).filter(
            EmailVerificationToken.token_hash == hash_url_token(token)
        ).one()
        stored.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()

    assert client.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 401


def test_resending_replaces_the_previous_link(client):
    client.post("/api/v1/auth/register", json=register_payload())
    first = pending_verification_token("user@example.com")

    assert client.post(
        "/api/v1/auth/resend-verification", json={"email": "user@example.com"}
    ).status_code == 200
    second = pending_verification_token("user@example.com")

    assert second != first
    # Un lien remplacé ne vaut plus rien : sinon un lien intercepté resterait utile.
    assert client.post("/api/v1/auth/verify-email", json={"token": first}).status_code == 401
    assert client.post("/api/v1/auth/verify-email", json={"token": second}).status_code == 200


def test_resending_reveals_nothing_about_an_unknown_address(client):
    client.post("/api/v1/auth/register", json=register_payload())
    known = client.post(
        "/api/v1/auth/resend-verification", json={"email": "user@example.com"}
    )
    unknown = client.post(
        "/api/v1/auth/resend-verification", json={"email": "jamais.vu@example.com"}
    )
    verified = client.post(
        "/api/v1/auth/resend-verification", json={"email": "user@example.com"}
    )

    assert known.status_code == unknown.status_code == verified.status_code == 200
    assert known.json() == unknown.json() == verified.json()


def test_weak_password_is_rejected(client):
    response = client.post(
        "/api/v1/auth/register", json=register_payload(password="motdepasse")
    )
    assert response.status_code == 422


def test_cannot_self_register_as_admin(client):
    response = client.post(
        "/api/v1/auth/register", json=register_payload(user_type="ADMIN")
    )
    assert response.status_code == 422


def test_login_and_me(client):
    register_and_verify(client)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "MotDePasse123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"


def test_login_with_wrong_password_is_generic(client):
    client.post("/api/v1/auth/register", json=register_payload())
    wrong = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "MauvaisMotDePasse1"},
    )
    unknown = client.post(
        "/api/v1/auth/login",
        json={"email": "inconnu@example.com", "password": "MauvaisMotDePasse1"},
    )
    # Meme message : pas d'enumeration de comptes.
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


def test_protected_route_requires_token(client):
    assert client.get("/api/v1/projects").status_code == 401
    assert (
        client.get("/api/v1/projects", headers={"Authorization": "Bearer invalide"}).status_code
        == 401
    )


def test_refresh_token_rotates_access_token(client):
    registered = register_and_verify(client)
    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": registered["refresh_token"]}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_access_token_cannot_be_used_as_refresh_token(client):
    registered = register_and_verify(client)
    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": registered["access_token"]}
    )
    assert response.status_code == 401


def _issue_reset_token(email: str) -> str:
    """Crée un jeton de réinitialisation et renvoie sa valeur en clair.

    L'API ne divulgue le jeton qu'en environnement `development` ; le test
    passe donc par le service, comme le ferait le lien reçu par e-mail.
    """
    from app.core.database import SessionLocal
    from app.core.security import generate_url_token, hash_url_token
    from app.models.user import PasswordResetToken, User

    raw = generate_url_token()
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).one()
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_url_token(raw),
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                created_at=datetime.now(UTC),
            )
        )
        db.commit()
    return raw


def test_password_reset_flow(client):
    register_and_verify(client)
    assert client.post(
        "/api/v1/auth/forgot-password", json={"email": "user@example.com"}
    ).status_code == 200

    token = _issue_reset_token("user@example.com")
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NouveauMotDePasse1"},
    )
    assert reset.status_code == 200

    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "NouveauMotDePasse1"},
        ).status_code
        == 200
    )
    # Le jeton de reinitialisation n'est utilisable qu'une fois.
    assert (
        client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "EncoreUnAutre1"},
        ).status_code
        == 401
    )


def test_reset_token_is_never_returned_outside_development(client):
    """Renvoyer le jeton dans la réponse permettrait de prendre tout compte connu."""
    client.post("/api/v1/auth/register", json=register_payload())
    response = client.post("/api/v1/auth/forgot-password", json={"email": "user@example.com"})
    assert response.status_code == 200
    assert "Jeton" not in response.json()["detail"]


def test_changing_password_revokes_existing_tokens(client):
    """Un changement de mot de passe doit déconnecter les sessions ouvertes."""
    registered = register_and_verify(client)
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    changed = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "MotDePasse123", "new_password": "NouveauMotDePasse1"},
        headers=headers,
    )
    assert changed.status_code == 200

    # L'ancien jeton d'accès ne vaut plus rien...
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    # ...et l'ancien jeton de rafraîchissement non plus.
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": registered["refresh_token"]}
        ).status_code
        == 401
    )


def test_resetting_password_revokes_existing_tokens(client):
    """La réinitialisation remédie à un compte compromis : elle doit chasser l'intrus."""
    registered = register_and_verify(client)
    headers = {"Authorization": f"Bearer {registered['access_token']}"}

    token = _issue_reset_token("user@example.com")
    client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NouveauMotDePasse1"},
    )

    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": registered["refresh_token"]}
        ).status_code
        == 401
    )


def test_forgot_password_does_not_reveal_unknown_account(client):
    response = client.post("/api/v1/auth/forgot-password", json={"email": "inconnu@example.com"})
    assert response.status_code == 200
    assert "Jeton" not in response.json()["detail"]
