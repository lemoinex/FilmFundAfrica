"""Tests de la limitation de débit partagée entre répliques.

Le défaut corrigé ici : avec des compteurs en mémoire, chaque réplique applique
sa propre limite. Derrière un répartiteur de charge à N répliques, la limite
réelle vaut N fois la limite annoncée sur les routes d'authentification et de
génération IA.

Une « réplique » est simulée par un `RedisBackend` distinct — processus
séparés, même Redis.
"""

from __future__ import annotations

import os
import time

import pytest

from app.core.rate_limit import (
    MemoryBackend,
    RateLimiter,
    RateLimitExceeded,
    RedisBackend,
    RedisError,
)


# ---------------------------------------------------------------------------
# Faux Redis : le sous-ensemble de commandes réellement utilisé
# ---------------------------------------------------------------------------
class FakePipeline:
    def __init__(self, client: FakeRedis) -> None:
        self._client = client
        self._queued: list[tuple[str, tuple]] = []

    def zremrangebyscore(self, key, minimum, maximum):
        self._queued.append(("zremrangebyscore", (key, minimum, maximum)))
        return self

    def zadd(self, key, mapping):
        self._queued.append(("zadd", (key, mapping)))
        return self

    def zcard(self, key):
        self._queued.append(("zcard", (key,)))
        return self

    def expire(self, key, seconds):
        self._queued.append(("expire", (key, seconds)))
        return self

    def execute(self):
        if self._client.broken:
            raise RedisError("connection refused")
        # MULTI/EXEC : les commandes s'exécutent d'un bloc.
        with self._client.lock:
            return [getattr(self._client, name)(*args) for name, args in self._queued]


class FakeRedis:
    """Stockage ZSET en mémoire, partagé par tous les backends qui le reçoivent."""

    def __init__(self) -> None:
        self.data: dict[str, dict[str, float]] = {}
        self.expirations: dict[str, int] = {}
        self.broken = False
        self.pipeline_calls = 0
        # Le vrai client sérialise ; le faux doit au moins ne pas mentir sur ce point.
        import threading

        self.lock = threading.Lock()

    def _guard(self):
        if self.broken:
            raise RedisError("connection refused")

    def pipeline(self, transaction=True):
        self.pipeline_calls += 1
        self._guard()
        return FakePipeline(self)

    def zremrangebyscore(self, key, minimum, maximum):
        bucket = self.data.get(key, {})
        stale = [m for m, score in bucket.items() if minimum <= score <= maximum]
        for member in stale:
            del bucket[member]
        return len(stale)

    def zadd(self, key, mapping):
        self.data.setdefault(key, {}).update(mapping)
        return len(mapping)

    def zcard(self, key):
        return len(self.data.get(key, {}))

    def zrem(self, key, member):
        self._guard()
        return 1 if self.data.get(key, {}).pop(member, None) is not None else 0

    def zrange(self, key, start, stop, withscores=False):
        self._guard()
        ordered = sorted(self.data.get(key, {}).items(), key=lambda item: item[1])
        window = ordered[start : (stop + 1 if stop >= 0 else None)]
        return window if withscores else [member for member, _ in window]

    def expire(self, key, seconds):
        self.expirations[key] = seconds
        return True

    def scan_iter(self, pattern):
        self._guard()
        prefix = pattern.rstrip("*")
        return [key for key in list(self.data) if key.startswith(prefix)]

    def delete(self, key):
        self._guard()
        self.data.pop(key, None)
        return 1

    def ping(self):
        self._guard()
        return True


def _replica(client, fallback=None) -> RedisBackend:
    return RedisBackend(client, fallback or MemoryBackend())


# ---------------------------------------------------------------------------
# Le défaut corrigé
# ---------------------------------------------------------------------------
def test_memory_backend_does_not_share_counters_between_replicas():
    """Le comportement qu'on corrige, épinglé pour que la suite ait un sens."""
    key = "1.2.3.4:/login"
    first, second = MemoryBackend(), MemoryBackend()

    for _ in range(3):
        assert first.hit(key, max_calls=3, window_seconds=60) is None
    assert first.hit(key, max_calls=3, window_seconds=60) is not None
    # La seconde réplique n'a rien vu passer : 3 appels de plus sont accordés.
    assert second.hit(key, max_calls=3, window_seconds=60) is None


def test_redis_backend_shares_counters_between_replicas():
    client = FakeRedis()
    first, second = _replica(client), _replica(client)
    key = "1.2.3.4:/login"

    assert first.hit(key, max_calls=3, window_seconds=60) is None
    assert second.hit(key, max_calls=3, window_seconds=60) is None
    assert first.hit(key, max_calls=3, window_seconds=60) is None
    # Quatrième appel, quelle que soit la réplique qui le reçoit.
    assert second.hit(key, max_calls=3, window_seconds=60) is not None
    assert first.hit(key, max_calls=3, window_seconds=60) is not None


def test_ten_replicas_still_enforce_a_single_limit():
    client = FakeRedis()
    replicas = [_replica(client) for _ in range(10)]
    allowed = sum(
        1
        for index in range(30)
        if replicas[index % 10].hit("1.2.3.4:/login", max_calls=10, window_seconds=60) is None
    )
    # Sans partage, les 10 répliques auraient laissé passer les 30 appels.
    assert allowed == 10


# ---------------------------------------------------------------------------
# Détails de comptage
# ---------------------------------------------------------------------------
def test_a_rejected_call_does_not_consume_a_slot():
    """Un client bloqué ne doit pas repousser sa propre fenêtre en insistant."""
    client = FakeRedis()
    backend = _replica(client)
    for _ in range(2):
        backend.hit("ip:/login", max_calls=2, window_seconds=60)
    for _ in range(20):
        backend.hit("ip:/login", max_calls=2, window_seconds=60)

    stored = client.data["ratelimit:ip:/login"]
    assert len(stored) == 2


def test_retry_delay_is_bounded_by_the_window():
    client = FakeRedis()
    backend = _replica(client)
    for _ in range(2):
        backend.hit("ip:/login", max_calls=2, window_seconds=60)

    retry_in = backend.hit("ip:/login", max_calls=2, window_seconds=60)
    assert retry_in is not None
    assert 0 < retry_in <= 60


def test_expired_entries_leave_the_window():
    client = FakeRedis()
    backend = _replica(client)
    for _ in range(2):
        backend.hit("ip:/login", max_calls=2, window_seconds=1)
    assert backend.hit("ip:/login", max_calls=2, window_seconds=1) is not None

    time.sleep(1.1)
    assert backend.hit("ip:/login", max_calls=2, window_seconds=1) is None


def test_limiters_with_different_ceilings_do_not_share_a_counter():
    """`auth` (10/min) et `ai` (10/min) partagent le même Redis, pas la même clé."""
    client = FakeRedis()
    backend = _replica(client)
    auth = RateLimiter(max_calls=2, name="auth", backend=backend)
    ai = RateLimiter(max_calls=2, name="ai", backend=backend)

    for _ in range(2):
        auth.check("1.2.3.4:/x")
    with pytest.raises(RateLimitExceeded):
        auth.check("1.2.3.4:/x")

    # Le quota IA du même appelant est intact.
    ai.check("1.2.3.4:/x")


# ---------------------------------------------------------------------------
# Redis injoignable : on dégrade, on ne tombe pas
# ---------------------------------------------------------------------------
def test_redis_failure_falls_back_to_memory_instead_of_failing_the_request():
    client = FakeRedis()
    fallback = MemoryBackend()
    backend = _replica(client, fallback)
    limiter = RateLimiter(max_calls=2, name="auth", backend=backend)

    client.broken = True

    # L'API répond toujours...
    limiter.check("1.2.3.4:/login")
    limiter.check("1.2.3.4:/login")
    # ... et continue de limiter, à l'échelle de cette instance.
    with pytest.raises(RateLimitExceeded):
        limiter.check("1.2.3.4:/login")


def test_degraded_warning_is_not_logged_on_every_call(caplog):
    client = FakeRedis()
    client.broken = True
    backend = _replica(client)

    with caplog.at_level("WARNING", logger="filmfund.rate_limit"):
        for _ in range(5):
            # Le coupe-circuit est rouvert à la main : on veut cinq échecs réels.
            backend._circuit_open_until = 0.0
            backend.hit("ip:/login", max_calls=100, window_seconds=60)

    degraded = [r for r in caplog.records if getattr(r, "event", "") == "rate_limit_degraded"]
    assert len(degraded) == 1


def test_an_open_circuit_stops_calling_a_redis_known_to_be_down():
    """Sinon chaque requête paierait le délai de connexion pendant toute la panne."""
    client = FakeRedis()
    client.broken = True
    backend = _replica(client)
    backend.hit("ip:/login", max_calls=5, window_seconds=60)

    # Redis est revenu, mais le coupe-circuit n'a pas encore expiré : on ne le
    # rappelle pas, on continue de compter en mémoire.
    client.broken = False
    calls_before = client.pipeline_calls
    backend.hit("ip:/login", max_calls=5, window_seconds=60)
    assert client.pipeline_calls == calls_before


def test_recovery_returns_to_shared_counting():
    client = FakeRedis()
    backend = _replica(client)
    client.broken = True
    backend.hit("ip:/login", max_calls=5, window_seconds=60)

    client.broken = False
    # La sonde de santé teste la connexion pour de bon : son succès referme le
    # coupe-circuit sans attendre.
    assert backend.ping() is True
    assert backend.hit("ip:/login", max_calls=5, window_seconds=60) is None
    assert client.zcard("ratelimit:ip:/login") == 1


def test_ping_reports_the_connection_state():
    client = FakeRedis()
    backend = _replica(client)
    assert backend.ping() is True
    client.broken = True
    assert backend.ping() is False


# ---------------------------------------------------------------------------
# Intégration : vrai serveur Redis si l'environnement en fournit un
# ---------------------------------------------------------------------------
REDIS_TEST_URL = os.environ.get("REDIS_TEST_URL", "redis://localhost:6379/15")


def _real_client():
    try:
        from redis import Redis
    except ModuleNotFoundError:  # pragma: no cover
        return None
    try:
        client = Redis.from_url(
            REDIS_TEST_URL,
            socket_connect_timeout=0.25,
            socket_timeout=0.25,
            decode_responses=True,
        )
        client.ping()
    except Exception:  # noqa: BLE001 - aucun Redis disponible ici
        return None
    return client


@pytest.mark.skipif(_real_client() is None, reason="aucun serveur Redis joignable")
def test_real_redis_enforces_one_limit_across_replicas():
    """Vérifie que le faux Redis ne ment pas sur le comportement réel."""
    client = _real_client()
    first, second = _replica(client), _replica(client)
    first.reset()
    try:
        key = f"integration-{os.getpid()}:/login"
        assert first.hit(key, max_calls=2, window_seconds=60) is None
        assert second.hit(key, max_calls=2, window_seconds=60) is None
        assert second.hit(key, max_calls=2, window_seconds=60) is not None
        assert first.hit(key, max_calls=2, window_seconds=60) is not None
    finally:
        first.reset()
