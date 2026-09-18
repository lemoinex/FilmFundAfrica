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
    }
)

from fastapi.testclient import TestClient  # noqa: E402

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


@pytest.fixture
def make_user(client: TestClient):
    """Crée un compte et renvoie (headers d'authentification, corps de réponse)."""

    def _make(email: str = "user@example.com", plan: str | None = None, **overrides):
        response = client.post(
            "/api/v1/auth/register", json=register_payload(email, **overrides)
        )
        assert response.status_code == 201, response.text
        data = response.json()

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
