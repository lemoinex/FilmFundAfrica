"""Fixtures de test : base SQLite isolée, client HTTP et utilisateurs."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator

import pytest

# La configuration doit être fixée AVANT l'import de l'application.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_db_fd)
os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DEBUG": "false",
        "DATABASE_URL": f"sqlite:///{_db_path}",
        "JWT_SECRET": "test-secret-not-used-in-production",
        "AI_PROVIDER": "mock",
        "RATE_LIMIT_AUTH_PER_MINUTE": "1000",
        "RATE_LIMIT_AI_PER_MINUTE": "1000",
        "SMTP_HOST": "",
        # Prestataire simulé : la chaîne de paiement s'exerce en entier, y
        # compris le rejet d'une notification mal signée, sans compte nulle part.
        "PAYMENT_PROVIDER": "mock",
        "PAYMENT_WEBHOOK_SECRET": "test-webhook-secret",
    }
)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.rate_limit import ai_limiter, auth_limiter  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.services.credit_service import CreditService  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_schema() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # Sous Windows, un fichier encore ouvert par le pool ne peut pas être supprimé.
    engine.dispose()
    if os.path.exists(_db_path):
        os.unlink(_db_path)


@pytest.fixture(autouse=True)
def _clean_tables() -> Generator[None, None, None]:
    auth_limiter.reset()
    ai_limiter.reset()
    yield
    with SessionLocal() as db:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session() -> Generator:
    with SessionLocal() as session:
        yield session


def job_result(response) -> dict:
    """Résultat d'une génération, à partir de la réponse qui l'a lancée.

    Le lancement répond 202 avec une tâche. Aucun worker n'est configuré en
    test (`REDIS_URL` vide) : l'API exécute la tâche elle-même, elle est donc
    déjà terminée quand la réponse arrive.
    """
    assert response.status_code == 202, response.text
    job = response.json()
    assert job["status"] == "SUCCEEDED", job
    assert job["result"] is not None, job
    return job["result"]


def register_payload(email: str = "user@example.com", **overrides) -> dict:
    payload = {
        "email": email,
        "password": "MotDePasse123",
        "first_name": "Aïcha",
        "last_name": "Ndiaye",
        "user_type": "AUTHOR",
        "country": "Sénégal",
    }
    payload.update(overrides)
    return payload


def pending_verification_token(email: str) -> str:
    """Jeton de confirmation en attente pour cette adresse.

    En test (`ENVIRONMENT=test`), l'API ne renvoie jamais le jeton : le lire en
    base est la seule façon d'ouvrir le lien, exactement comme un utilisateur
    ouvre celui qu'il a reçu par e-mail.
    """
    from app.core.security import hash_url_token
    from app.models.user import EmailVerificationToken, User

    with SessionLocal() as db:
        user = db.scalars(select(User).where(User.email == email.strip().lower())).one()
        tokens = db.scalars(
            select(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user.id,
                EmailVerificationToken.used_at.is_(None),
            )
        ).all()
        assert tokens, f"aucun jeton de confirmation en attente pour {email}"
        # Le jeton clair n'est pas stocké : on le retrouve par son empreinte.
        raw = _RAW_TOKENS.get(tokens[-1].token_hash)
        assert raw is not None, "jeton non capturé"
        assert hash_url_token(raw) == tokens[-1].token_hash
        return raw


#: Jetons émis pendant les tests, indexés par empreinte (voir `_capture_tokens`).
_RAW_TOKENS: dict[str, str] = {}


@pytest.fixture(autouse=True)
def _capture_tokens(monkeypatch):
    """Retient les jetons émis, comme le ferait la boîte mail du destinataire."""
    from app.core import security

    original = security.generate_url_token

    def _remember() -> str:
        raw = original()
        _RAW_TOKENS[security.hash_url_token(raw)] = raw
        return raw

    monkeypatch.setattr("app.services.auth_service.generate_url_token", _remember)
    yield
    _RAW_TOKENS.clear()


def register_and_verify(client, email: str = "user@example.com", **overrides) -> dict:
    """Inscrit un compte et ouvre son lien de confirmation.

    L'inscription n'ouvre plus de session : le compte s'active en ouvrant le
    lien reçu par e-mail. C'est ce parcours-là que les tests rejouent.
    """
    response = client.post("/api/v1/auth/register", json=register_payload(email, **overrides))
    assert response.status_code == 202, response.text
    verified = client.post(
        "/api/v1/auth/verify-email", json={"token": pending_verification_token(email)}
    )
    assert verified.status_code == 200, verified.text
    return verified.json()


@pytest.fixture
def make_user(client: TestClient):
    """Crée un compte, confirme l'adresse, et renvoie (headers, corps)."""

    def _make(email: str = "user@example.com", plan: str | None = None, **overrides):
        data = register_and_verify(client, email, **overrides)

        if plan:
            from app.models.enums import PlanCode
            from app.models.user import User

            with SessionLocal() as db:
                user = db.get(User, data["user"]["id"])
                credits = CreditService(db)
                target = credits.get_plan(PlanCode(plan))
                user.subscription.plan_id = target.id
                user.ai_credits_remaining = target.monthly_ai_credits
                db.commit()

        headers = {"Authorization": f"Bearer {data['access_token']}"}
        return headers, data

    return _make


@pytest.fixture
def auth_headers(make_user) -> dict:
    headers, _ = make_user(plan="PRO_AUTHOR")
    return headers


PROJECT_PAYLOAD = {
    "title": "Les Gardiennes du fleuve",
    "project_type": "DOCUMENTARY",
    "genre": "Documentaire de création",
    "country": "Sénégal",
    "duration": 90,
    "theme": "Transmission et écologie",
    "concept": "Trois générations de femmes face à la salinisation du delta.",
    "characters": [
        {
            "name": "Fatou Sow",
            "role": "Protagoniste",
            "description": "Gardienne de la mémoire du fleuve depuis soixante ans.",
        }
    ],
}


@pytest.fixture
def project(client: TestClient, auth_headers: dict) -> dict:
    response = client.post("/api/v1/projects", json=PROJECT_PAYLOAD, headers=auth_headers)
    assert response.status_code == 201, response.text
    return response.json()
