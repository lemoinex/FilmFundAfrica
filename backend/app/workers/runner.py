"""Worker de generation : `python -m app.workers.runner`.

Boucle d'attente sur la file Redis. A chaque tour :

1. publier un battement de coeur — sans lui, l'API considere qu'il n'y a pas
   de worker et execute les generations elle-meme plutot que de les deposer
   dans une file que personne ne lit ;
2. attendre une tache (`BLPOP`), et l'executer ;
3. quand rien ne vient, balayer la base : taches en attente dont le signal
   s'est perdu, taches `RUNNING` dont le worker a disparu.

Le balayage est ce qui rend le systeme reparable : meme sans Redis persistant,
aucune tache n'est definitivement perdue.
"""

from __future__ import annotations

import logging
import signal
import sys

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import setup_logging
from app.core.observability import setup_sentry
from app.core.redis import build_client
from app.services.job_queue import HEARTBEAT_TTL_SECONDS, JobQueue
from app.services.job_service import JobService, run_job

logger = logging.getLogger("filmfund.worker")

#: Attente maximale d'une tache avant de rendre la main a la boucle.
POLL_TIMEOUT_SECONDS = 5


class Worker:
    def __init__(self, queue: JobQueue | None = None) -> None:
        # Le client du worker attend une tache : son delai de lecture doit
        # couvrir l'attente bloquante, sinon une file calme passerait pour
        # une panne.
        self.queue = queue or JobQueue(
            client=build_client(timeout=POLL_TIMEOUT_SECONDS + 5)
        )
        self._running = True

    def stop(self, *_: object) -> None:
        """Arrete la boucle a la fin de la tache en cours."""
        logger.info("arrêt demandé", extra={"event": "worker_stopping"})
        self._running = False

    # ------------------------------------------------------------------
    def run(self) -> None:
        if self.queue.client is None:
            logger.error(
                "REDIS_URL n'est pas défini : le worker n'a aucune file à écouter. "
                "L'API exécute alors les générations elle-même."
            )
            return

        logger.info("worker de génération démarré", extra={"event": "worker_started"})
        while self._running:
            self.queue.heartbeat(HEARTBEAT_TTL_SECONDS)
            job_id = self.queue.pop(timeout=POLL_TIMEOUT_SECONDS)
            if job_id is not None:
                self._execute(job_id)
                continue
            self.sweep()

    def _execute(self, job_id: str) -> None:
        try:
            run_job(job_id)
        except Exception:  # noqa: BLE001 - une tache ne doit jamais tuer le worker
            logger.exception(
                "tâche non exécutée jusqu'au bout", extra={"event": "worker_job_crashed"}
            )

    # ------------------------------------------------------------------
    def sweep(self) -> int:
        """Reprend ce que la file a laissé passer. Renvoie le nombre de reprises."""
        with SessionLocal() as db:
            service = JobService(db, queue=self.queue)
            service.fail_timed_out()
            pending = service.stale_queued_ids()

        for job_id in pending:
            logger.info(
                "tâche reprise par le balayage", extra={"event": "job_recovered"}
            )
            self._execute(job_id)
        return len(pending)


def main() -> int:
    setup_logging()
    # Une generation echoue loin de toute requete HTTP : sans suivi cote
    # worker, la moitie des erreurs du produit ne serait jamais remontee.
    setup_sentry()
    worker = Worker()
    signal.signal(signal.SIGTERM, worker.stop)
    signal.signal(signal.SIGINT, worker.stop)
    logger.info(
        "délai d'exécution maximal par tâche : %s s",
        settings.job_timeout_seconds,
        extra={"event": "worker_config"},
    )
    worker.run()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
