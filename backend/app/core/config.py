"""Configuration centrale de l'application.

Toutes les valeurs sensibles proviennent de variables d'environnement.
Aucun secret n'est ecrit en dur dans le code.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Secret de developpement, volontairement reconnaissable.
#: L'application refuse de demarrer en production tant qu'il n'est pas remplace.
DEV_JWT_SECRET = "dev-only-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    app_name: str = "FilmFund Africa"
    api_v1_prefix: str = "/api/v1"
    environment: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = True
    default_locale: Literal["fr", "en"] = "fr"

    # --- Base de donnees ---
    database_url: str = "postgresql+psycopg://filmfund:filmfund@localhost:5432/filmfund"

    # --- Securite ---
    #: Valeur sentinelle : acceptee en developpement, refusee en production.
    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14
    password_reset_expire_minutes: int = 60
    #: Duree de validite du lien de confirmation d'adresse (24 h par defaut).
    email_verification_expire_minutes: int = 1440
    cors_origins: str = "http://localhost:3000"
    #: IP des proxys de confiance, seules autorisees a definir X-Forwarded-For.
    trusted_proxy_ips: str = ""

    # --- Rate limiting ---
    rate_limit_auth_per_minute: int = 10
    rate_limit_ai_per_minute: int = 10
    rate_limit_default_per_minute: int = 120
    #: Vide : compteurs en memoire, propres a chaque processus. Renseigne
    #: (`redis://host:6379/0`) : compteurs partages par toutes les repliques.
    redis_url: str = ""
    #: Un Redis lent ne doit pas tenir la requete ouverte : au-dela, on compte
    #: en memoire pour cet appel.
    redis_timeout_seconds: float = 0.25

    # --- Taches de generation ---
    #: Duree SANS SIGNE DE VIE au-dela de laquelle une tache est consideree
    #: interrompue (worker disparu) : elle echoue et ses credits sont rendus.
    #: Le worker touche la tache a chaque passe, si bien qu'une generation
    #: longue mais vivante n'est jamais prise pour une tache morte. Le seuil
    #: doit rester superieur a `AI_TIMEOUT_SECONDS`, duree maximale d'une passe.
    job_timeout_seconds: int = 900
    #: Age a partir duquel une tache encore en attente est reprise par le
    #: balayage, meme si le signal Redis s'est perdu.
    job_stale_seconds: int = 60

    # --- Observabilite ---
    #: Vide : aucun suivi d'erreurs, aucune requete vers un tiers.
    sentry_dsn: str = ""
    #: Environnement affiche dans Sentry ; reprend `ENVIRONMENT` si vide.
    sentry_environment: str = ""
    #: Version deployee, pour rattacher une erreur a un lot de code.
    sentry_release: str = ""
    #: Part des requetes tracees pour la performance. 0 = aucune : le suivi
    #: d'erreurs n'a pas besoin de traces, et elles coutent cher.
    sentry_traces_sample_rate: float = 0.0

    # --- Paiements et abonnements ---
    #: `manual` : encaissement hors ligne, valide depuis l'administration.
    #: `mock` : prestataire simule, pour le developpement et les tests.
    #: Brancher un prestataire reel revient a ajouter une classe et un nom ici.
    payment_provider: Literal["manual", "mock"] = "manual"
    #: Secret partage avec le prestataire, qui signe ses notifications. Sans
    #: lui, aucune notification n'est acceptee : une verification qui s'ouvre
    #: quand la configuration est incomplete ne protege rien.
    payment_webhook_secret: str = ""

    # --- IA ---
    ai_provider: Literal["anthropic", "openai", "mock"] = "mock"
    ai_api_key: str = ""
    ai_model: str = "claude-sonnet-4-5"
    ai_max_output_tokens: int = 8000
    #: Nombre maximal de passes pour un scenario. Plafond de securite, pas
    #: limite d'usage : c'est la duree demandee qui fixe le nombre de passes.
    screenplay_max_passes: int = 40
    ai_timeout_seconds: int = 180

    # --- Credits IA par defaut (surchargeables en base) ---
    ai_credits_free: int = 1
    ai_credits_pro: int = 300
    ai_credits_producer: int = 500

    # --- n8n ---
    n8n_webhook_url: str = ""
    n8n_api_key: str = ""

    # --- Email ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-reply@filmfundafrica.com"
    smtp_tls: bool = True

    # --- Stockage ---
    storage_url: str = "./storage"
    storage_backend: Literal["local", "s3"] = "local"

    frontend_url: str = Field(default="http://localhost:3000")

    @field_validator("database_url")
    @classmethod
    def _normalise_database_url(cls, value: str) -> str:
        """Accepte les URL `postgresql://` et les convertit pour psycopg v3."""
        if value.startswith("postgres://"):
            value = value.replace("postgres://", "postgresql://", 1)
        if value.startswith("postgresql://"):
            value = value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @model_validator(mode="after")
    def _refuse_unsafe_production(self) -> Settings:
        """Interdit de démarrer en production avec une configuration non sécurisée."""
        if self.environment != "production":
            return self

        problems: list[str] = []
        if not self.jwt_secret or self.jwt_secret == DEV_JWT_SECRET:
            problems.append(
                "JWT_SECRET doit être défini et différent de la valeur de développement "
                "(générez-le avec `openssl rand -hex 32`)"
            )
        if len(self.jwt_secret) < 32:
            problems.append("JWT_SECRET doit faire au moins 32 caractères")
        if self.debug:
            problems.append("DEBUG doit valoir false en production")
        if self.ai_provider != "mock" and not self.ai_api_key:
            problems.append(f"AI_API_KEY est requis avec AI_PROVIDER={self.ai_provider}")
        if self.payment_provider == "mock":
            problems.append(
                "PAYMENT_PROVIDER=mock encaisse des paiements fictifs : interdit en production"
            )
        if self.payment_provider != "manual" and not self.payment_webhook_secret:
            problems.append(
                "PAYMENT_WEBHOOK_SECRET est requis avec "
                f"PAYMENT_PROVIDER={self.payment_provider} : sans lui, n'importe qui "
                "pourrait s'offrir un abonnement en appelant le webhook"
            )

        if problems:
            raise ValueError(
                "Configuration de production invalide :\n- " + "\n- ".join(problems)
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def trusted_proxy_list(self) -> list[str]:
        return [ip.strip() for ip in self.trusted_proxy_ips.split(",") if ip.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
