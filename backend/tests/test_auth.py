"""Tests d'authentification et de securite des comptes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tests.conftest import register_payload


def test_register_returns_tokens_and_profile(client):
    response = client.post("/api/v1/auth/register", json=register_payload())
    assert response.status_code == 201
    data = response.json()
    assert data["access_token"] and data["refresh_token"]
    assert data["user"]["email"] == "user@example.com"
    assert data["user"]["profile"]["first_name"] == "Aïcha"
    # Le plan gratuit accorde des credits IA des l'inscription.
    assert data["user"]["ai_credits_remaining"] >= 1


def test_password_is_never_returned(client):
    response = client.post("/api/v1/auth/register", json=register_payload())
    assert "password" not in response.text
    assert "hashed_password" not in response.text


def test_duplicate_email_is_rejected(client):
    client.post("/api/v1/auth/register", json=register_payload())
    response = client.post("/api/v1/auth/register", json=register_payload())
    assert response.status_code == 409


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
    client.post("/api/v1/auth/register", json=register_payload())
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
    registered = client.post("/api/v1/auth/register", json=register_payload()).json()
    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": registered["refresh_token"]}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_access_token_cannot_be_used_as_refresh_token(client):
    registered = client.post("/api/v1/auth/register", json=register_payload()).json()
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
    from app.core.security import generate_reset_token, hash_reset_token
    from app.models.user import PasswordResetToken, User

    raw = generate_reset_token()
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).one()
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_reset_token(raw),
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                created_at=datetime.now(UTC),
            )
        )
        db.commit()
    return raw


def test_password_reset_flow(client):
    client.post("/api/v1/auth/register", json=register_payload())
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
    registered = client.post("/api/v1/auth/register", json=register_payload()).json()
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
    registered = client.post("/api/v1/auth/register", json=register_payload()).json()
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
