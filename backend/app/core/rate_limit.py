"""Limitation de debit en memoire (fenetre glissante).

Suffisant pour un deploiement mono-instance. Pour plusieurs replicas,
remplacer le stockage par Redis sans changer l'interface `RateLimiter`.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import settings
from app.core.errors import AppError


class RateLimitExceeded(AppError):
    status_code = 429
    code = "rate_limit_exceeded"


class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: int = 60) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._last_eviction = 0.0

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._evict_expired(now)
            bucket = self._hits[key]
            while bucket and now - bucket[0] > self.window_seconds:
                bucket.popleft()
            if len(bucket) >= self.max_calls:
                retry_in = int(self.window_seconds - (now - bucket[0])) + 1
                raise RateLimitExceeded(
                    f"Trop de requêtes. Réessayez dans {retry_in} seconde(s)."
                )
            bucket.append(now)

    def _evict_expired(self, now: float) -> None:
        """Purge les compteurs inactifs.

        Sans cette purge, un flux de clés distinctes ferait croître le
        dictionnaire indéfiniment.
        """
        if now - self._last_eviction < self.window_seconds:
            return
        self._last_eviction = now
        stale = [
            key
            for key, bucket in self._hits.items()
            if not bucket or now - bucket[-1] > self.window_seconds
        ]
        for key in stale:
            del self._hits[key]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
            self._last_eviction = 0.0


auth_limiter = RateLimiter(settings.rate_limit_auth_per_minute)
ai_limiter = RateLimiter(settings.rate_limit_ai_per_minute)


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
