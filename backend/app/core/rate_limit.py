"""Limitation de debit, en memoire ou partagee entre repliques via Redis.

Sans `REDIS_URL`, les compteurs vivent dans le processus : correct pour une
instance unique, mais chaque replique applique alors *sa* limite. Avec N
repliques derriere un repartiteur de charge, un attaquant obtient N fois la
limite annoncee — la protection des routes d'authentification et de generation
IA est donc divisee par N.

Avec `REDIS_URL`, les compteurs sont partages : la limite vaut pour le
deploiement entier, quel que soit le nombre de repliques. Si Redis devient
injoignable, on retombe sur les compteurs en memoire plutot que de refuser le
trafic : une limite approximative vaut mieux qu'une API indisponible.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import defaultdict, deque
from typing import Protocol

from fastapi import Request

from app.core.config import settings
from app.core.errors import AppError
from app.core.redis import RedisError, build_client

logger = logging.getLogger("filmfund.rate_limit")


#: Delai minimal entre deux avertissements « Redis injoignable ».
_DEGRADED_LOG_INTERVAL_SECONDS = 60

#: Duree pendant laquelle on cesse d'appeler un Redis qui vient d'echouer.
#: Sans ce coupe-circuit, chaque requete paierait le delai de connexion
#: (`redis_timeout_seconds`) tant que la panne dure.
_CIRCUIT_OPEN_SECONDS = 5


class RateLimitExceeded(AppError):
    status_code = 429
    code = "rate_limit_exceeded"


class RateLimitBackend(Protocol):
    """Stockage des compteurs.

    `hit` enregistre un appel et renvoie `None` s'il est autorise, sinon le
    nombre de secondes a attendre avant le prochain essai possible.
    """

    name: str

    def hit(self, key: str, max_calls: int, window_seconds: int) -> float | None: ...

    def reset(self) -> None: ...


class MemoryBackend:
    """Fenetre glissante en memoire, propre au processus."""

    name = "memory"

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._last_eviction = 0.0

    def hit(self, key: str, max_calls: int, window_seconds: int) -> float | None:
        now = time.monotonic()
        with self._lock:
            self._evict_expired(now, window_seconds)
            bucket = self._hits[key]
            while bucket and now - bucket[0] > window_seconds:
                bucket.popleft()
            if len(bucket) >= max_calls:
                return window_seconds - (now - bucket[0])
            bucket.append(now)
            return None

    def _evict_expired(self, now: float, window_seconds: int) -> None:
        """Purge les compteurs inactifs.

        Sans cette purge, un flux de cles distinctes ferait croitre le
        dictionnaire indefiniment.
        """
        if now - self._last_eviction < window_seconds:
            return
        self._last_eviction = now
        stale = [
            key
            for key, bucket in self._hits.items()
            if not bucket or now - bucket[-1] > window_seconds
        ]
        for key in stale:
            del self._hits[key]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
            self._last_eviction = 0.0


class RedisBackend:
    """Fenetre glissante partagee : un ensemble ordonne (ZSET) par cle.

    Les quatre commandes du comptage partent dans une meme transaction
    MULTI/EXEC. Sans cela, deux repliques pourraient lire le meme total et
    accorder chacune la derniere place de la fenetre.

    L'horodatage est l'heure murale (`time.time`) et non `time.monotonic` :
    les repliques doivent partager la meme reference de temps.
    """

    name = "redis"

    def __init__(self, client, fallback: MemoryBackend, *, prefix: str = "ratelimit") -> None:
        self._client = client
        self._fallback = fallback
        self._prefix = prefix
        self._last_degraded_log = 0.0
        self._circuit_open_until = 0.0

    def hit(self, key: str, max_calls: int, window_seconds: int) -> float | None:
        # Coupe-circuit : apres un echec, on compte en memoire pendant quelques
        # secondes plutot que d'attendre un serveur qu'on sait injoignable.
        if time.monotonic() < self._circuit_open_until:
            return self._fallback.hit(key, max_calls, window_seconds)

        now = time.time()
        redis_key = f"{self._prefix}:{key}"
        # Deux appels simultanes doivent occuper deux places distinctes : le
        # seul horodatage ne suffit pas a les distinguer.
        member = f"{now:.6f}:{uuid.uuid4().hex}"
        try:
            pipe = self._client.pipeline(transaction=True)
            pipe.zremrangebyscore(redis_key, 0, now - window_seconds)
            pipe.zadd(redis_key, {member: now})
            pipe.zcard(redis_key)
            # Une cle dont plus personne ne se sert expire d'elle-meme.
            pipe.expire(redis_key, window_seconds + 1)
            count = pipe.execute()[2]

            if count > max_calls:
                # L'appel refuse ne compte pas : sinon un client bloque
                # repousserait sa propre fenetre a chaque nouvelle tentative.
                self._client.zrem(redis_key, member)
                oldest = self._client.zrange(redis_key, 0, 0, withscores=True)
                if oldest:
                    return max(window_seconds - (now - oldest[0][1]), 0.0)
                return float(window_seconds)
            return None
        except RedisError as exc:
            self._circuit_open_until = time.monotonic() + _CIRCUIT_OPEN_SECONDS
            self._warn_degraded(exc)
            return self._fallback.hit(key, max_calls, window_seconds)

    def ping(self) -> bool:
        """Teste la connexion pour de bon : la sonde de santé doit dire le vrai."""
        try:
            reachable = bool(self._client.ping())
        except RedisError:
            return False
        if reachable:
            # Redis est revenu : inutile d'attendre la fin du coupe-circuit.
            self._circuit_open_until = 0.0
        return reachable

    def reset(self) -> None:
        self._fallback.reset()
        try:
            for key in self._client.scan_iter(f"{self._prefix}:*"):
                self._client.delete(key)
        except RedisError as exc:  # pragma: no cover - chemin de secours
            self._warn_degraded(exc)

    def _warn_degraded(self, exc: Exception) -> None:
        """Signale la bascule en memoire, sans inonder les journaux.

        Redis injoignable, c'est une requete sur deux qui echoue : un
        avertissement par appel rendrait les journaux illisibles au moment
        precis ou on les lit.
        """
        now = time.monotonic()
        if now - self._last_degraded_log < _DEGRADED_LOG_INTERVAL_SECONDS:
            return
        self._last_degraded_log = now
        logger.warning(
            "Redis injoignable : la limitation de débit retombe sur les compteurs "
            "en mémoire, propres à cette instance (%s)",
            exc,
            extra={"event": "rate_limit_degraded"},
        )


def build_backend() -> RateLimitBackend:
    """Choisit le stockage des compteurs d'apres la configuration.

    Un Redis lent ne doit pas bloquer l'API : le client est construit avec un
    delai court, et on prefere compter en memoire plutot que tenir la requete
    ouverte.
    """
    memory = MemoryBackend()
    client = build_client()
    if client is None:
        return memory
    return RedisBackend(client, memory)


_backend: RateLimitBackend = build_backend()


class RateLimiter:
    """Limite `max_calls` appels par cle et par fenetre glissante."""

    def __init__(
        self,
        max_calls: int,
        window_seconds: int = 60,
        *,
        name: str = "default",
        backend: RateLimitBackend | None = None,
    ) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.name = name
        self._backend = backend if backend is not None else _backend

    def check(self, key: str) -> None:
        # Le nom prefixe la cle : deux limiteurs aux plafonds differents ne
        # doivent pas se partager un compteur dans un Redis commun.
        retry_in = self._backend.hit(f"{self.name}:{key}", self.max_calls, self.window_seconds)
        if retry_in is not None:
            raise RateLimitExceeded(
                f"Trop de requêtes. Réessayez dans {int(retry_in) + 1} seconde(s)."
            )

    def reset(self) -> None:
        self._backend.reset()

    @property
    def backend_name(self) -> str:
        return self._backend.name


auth_limiter = RateLimiter(settings.rate_limit_auth_per_minute, name="auth")
ai_limiter = RateLimiter(settings.rate_limit_ai_per_minute, name="ai")


def backend_status() -> str:
    """Etat du stockage des compteurs, pour la sonde de sante.

    `redis-unreachable` signale un deploiement configure pour une limite
    partagee qui ne l'obtient pas : chaque replique compte de son cote.
    """
    if isinstance(_backend, RedisBackend):
        return "redis" if _backend.ping() else "redis-unreachable"
    return _backend.name


def client_identifier(request: Request) -> str:
    """Identifie l'appelant pour la limitation de débit.

    `X-Forwarded-For` n'est lu QUE si la connexion provient d'un proxy déclaré
    dans `TRUSTED_PROXY_IPS`. Sinon, n'importe qui pourrait faire tourner cet
    en-tête et contourner entièrement la limitation.
    """
    peer = request.client.host if request.client else "unknown"
    if peer in settings.trusted_proxy_list:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip() or peer
    return peer


def _request_key(request: Request) -> str:
    return f"{client_identifier(request)}:{request.url.path}"


def rate_limit_auth(request: Request) -> None:
    auth_limiter.check(_request_key(request))


def rate_limit_ai(request: Request) -> None:
    ai_limiter.check(_request_key(request))
