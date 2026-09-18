"""Client Redis partage par la limitation de debit et la file de taches.

Redis reste optionnel : sans `REDIS_URL`, ce module renvoie `None` et chaque
appelant applique son propre repli (compteurs en memoire pour la limitation de
debit, execution immediate pour la generation).
"""

from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger("filmfund.redis")

try:  # pragma: no cover - depend de l'environnement d'installation
    from redis import Redis
    from redis.exceptions import RedisError
except ModuleNotFoundError:  # pragma: no cover
    Redis = None

    class RedisError(Exception):
        """Repli si le paquet `redis` n'est pas installe."""


def build_client(*, timeout: float | None = None):
    """Construit un client, ou `None` si Redis n'est pas configure.

    `timeout` surcharge le delai par defaut : le worker, qui attend une tache
    avec `BLPOP`, a besoin d'un delai plus long que les appels de la limitation
    de debit, ou une attente normale passerait pour une panne.
    """
    url = settings.redis_url.strip()
    if not url:
        return None
    if Redis is None:  # pragma: no cover - installation incomplete
        logger.warning(
            "REDIS_URL est défini mais le paquet `redis` n'est pas installé : "
            "les fonctions qui en dépendent restent en mode dégradé."
        )
        return None
    delay = settings.redis_timeout_seconds if timeout is None else timeout
    return Redis.from_url(
        url,
        socket_connect_timeout=settings.redis_timeout_seconds,
        socket_timeout=delay,
        retry_on_timeout=False,
        decode_responses=True,
    )


__all__ = ["Redis", "RedisError", "build_client"]
