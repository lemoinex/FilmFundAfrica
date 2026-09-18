"""Connexion SQLAlchemy et session factory."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_connect_args: dict = {}
_engine_kwargs: dict = {"pool_pre_ping": True, "future": True}

if settings.database_url.startswith("sqlite"):
    # Utilise uniquement pour les tests.
    _connect_args = {"check_same_thread": False}
    _engine_kwargs.pop("pool_pre_ping", None)

engine = create_engine(settings.database_url, connect_args=_connect_args, **_engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    """Dependance FastAPI : une session par requete, fermee systematiquement."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
