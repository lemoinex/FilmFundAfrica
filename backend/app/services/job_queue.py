"""File d'attente des taches de generation.

Redis ne porte que le signal de reveil : la table `generation_jobs` reste la
source de verite. Une liste perdue (Redis vide, `FLUSHALL`, redemarrage sans
persistance) ne perd donc aucune tache — le worker balaye la base et reprend
celles qui attendent.

Le worker publie un battement de coeur. Sans battement recent, l'API n'a
personne a qui confier la tache : elle l'execute elle-meme plutot que de la
deposer dans une file que personne ne lit.
"""

from __future__ import annotations

import logging

from app.core.redis import RedisError, build_client

logger = logging.getLogger("filmfund.jobs")

QUEUE_KEY = "filmfund:jobs:queued"
HEARTBEAT_KEY = "filmfund:jobs:worker"

#: Duree de vie du battement de coeur. Le worker le renouvelle plus souvent
#: que cela ; au-dela, on considere qu'il n'y a plus de worker.
HEARTBEAT_TTL_SECONDS = 30


class JobQueue:
    """Depot et retrait des identifiants de tache."""

    def __init__(self, client=None) -> None:
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = build_client()
        return self._client

    @property
    def available(self) -> bool:
        """Vrai si une tache peut etre confiee a un worker."""
        return self.client is not None and self.worker_alive()

    # ------------------------------------------------------------------
    def push(self, job_id: str) -> bool:
        """Depose une tache. Renvoie False si elle n'a pas pu l'etre."""
        client = self.client
        if client is None:
            return False
        try:
            client.rpush(QUEUE_KEY, job_id)
            return True
        except RedisError as exc:
            logger.warning(
                "dépôt de la tâche %s impossible : %s",
                job_id,
                exc,
                extra={"event": "job_enqueue_failed"},
            )
            return False

    def pop(self, timeout: int = 5) -> str | None:
        """Attend une tache, au plus `timeout` secondes."""
        client = self.client
        if client is None:
            return None
        try:
            entry = client.blpop(QUEUE_KEY, timeout=timeout)
        except RedisError as exc:
            logger.warning(
                "lecture de la file impossible : %s", exc, extra={"event": "job_pop_failed"}
            )
            return None
        if entry is None:
            return None
        return entry[1]

    # ------------------------------------------------------------------
    def heartbeat(self, ttl: int = HEARTBEAT_TTL_SECONDS) -> None:
        client = self.client
        if client is None:
            return
        try:
            client.set(HEARTBEAT_KEY, "1", ex=ttl)
        except RedisError:  # pragma: no cover - chemin de secours
            logger.warning("battement de cœur du worker non publié")

    def worker_alive(self) -> bool:
        client = self.client
        if client is None:
            return False
        try:
            return bool(client.exists(HEARTBEAT_KEY))
        except RedisError:
            return False

    def pending(self) -> int:
        """Nombre de taches en attente dans la file (indicatif)."""
        client = self.client
        if client is None:
            return 0
        try:
            return int(client.llen(QUEUE_KEY))
        except RedisError:
            return 0


#: File partagee par l'API. Le worker construit la sienne, avec un client dont
#: le delai de lecture couvre l'attente bloquante.
job_queue = JobQueue()
