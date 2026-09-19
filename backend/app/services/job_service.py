"""Cycle de vie des taches de generation IA.

Une generation n'est plus executee dans la requete HTTP : l'API valide la
demande, reserve les credits, enregistre une tache et repond. Un worker
l'execute et met a jour son avancement, passe par passe.

Deux garde-fous portent tout le reste :

* **Les credits sont reserves a la mise en file.** Sans cela, on pourrait
  empiler cent taches avec un seul credit : aucune n'aurait encore debite quoi
  que ce soit au moment de la suivante. La reserve est remboursee si la tache
  echoue.
* **La base est la source de verite.** Redis ne porte que le signal de reveil.
  Une file perdue ne perd aucune tache : le balayage les retrouve.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents import AGENT_PIPELINE
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.errors import AppError, NotFoundError
from app.models.document import Document
from app.models.enums import AIOperation, DocumentType, JobKind, JobStatus
from app.models.jobs import GenerationJob
from app.models.project import Project
from app.models.user import User
from app.schemas.document import GenerateRequest, RefineRequest
from app.services.credit_service import CreditService
from app.services.document_service import DocumentService
from app.services.job_queue import JobQueue, job_queue

logger = logging.getLogger("filmfund.jobs")


class JobService:
    def __init__(self, db: Session, queue: JobQueue | None = None) -> None:
        self.db = db
        self.queue = queue if queue is not None else job_queue
        self.credits = CreditService(db)

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------
    def get_owned_job(self, job_id: str, user: User) -> GenerationJob:
        """Charge une tache en garantissant l'isolation des donnees.

        404 et non 403 : la reponse ne doit pas reveler l'existence de la tache
        d'un autre compte.
        """
        job = self.db.get(GenerationJob, job_id)
        if job is None or job.user_id != user.id:
            raise NotFoundError("job.notFound")
        return job

    def list_for_project(self, project: Project, limit: int = 20) -> list[GenerationJob]:
        return list(
            self.db.scalars(
                select(GenerationJob)
                .where(GenerationJob.project_id == project.id)
                .order_by(GenerationJob.created_at.desc())
                .limit(limit)
            )
        )

    # ------------------------------------------------------------------
    # Mise en file
    # ------------------------------------------------------------------
    def enqueue_generate(
        self,
        user: User,
        project: Project,
        document_type: DocumentType,
        payload: GenerateRequest,
    ) -> GenerationJob:
        documents = DocumentService(self.db)
        # Les refus previsibles (type inapplicable, document deja present,
        # scenario trop long) doivent repondre tout de suite, pas echouer plus
        # tard dans une tache que l'utilisateur devra aller consulter.
        passes = documents.prepare_generation(project, document_type, payload)

        job = GenerationJob(
            user_id=user.id,
            project_id=project.id,
            kind=JobKind.GENERATE_DOCUMENT,
            document_type=document_type,
            total_passes=passes,
            payload=payload.model_dump(mode="json"),
        )
        return self._reserve_and_dispatch(job, user, AIOperation.GENERATE_DOCUMENT, passes)

    def enqueue_refine(
        self, user: User, project: Project, document: Document, payload: RefineRequest
    ) -> GenerationJob:
        DocumentService(self.db).prepare_refine(document)

        job = GenerationJob(
            user_id=user.id,
            project_id=project.id,
            document_id=document.id,
            kind=JobKind.REFINE_DOCUMENT,
            document_type=document.document_type,
            total_passes=1,
            payload=payload.model_dump(mode="json"),
        )
        return self._reserve_and_dispatch(job, user, AIOperation.IMPROVE_DOCUMENT, 1)

    def enqueue_agent_chain(self, user: User, project: Project) -> GenerationJob:
        """Met en file un passage complet de la chaine d'agents.

        Les credits sont reserves pour **chaque agent**, pas pour le passage :
        huit etapes, c'est huit appels au fournisseur. Reserver un seul credit
        laisserait un compte epuise lancer une chaine entiere.

        Les reprises ne sont pas reservees d'avance — on ne sait pas encore
        s'il y en aura. Elles sont journalisees a l'execution.
        """
        job = GenerationJob(
            user_id=user.id,
            project_id=project.id,
            kind=JobKind.RUN_AGENT_CHAIN,
            document_type=None,
            total_passes=len(AGENT_PIPELINE),
            payload={},
        )
        return self._reserve_and_dispatch(
            job, user, AIOperation.RUN_AGENT_CHAIN, len(AGENT_PIPELINE)
        )

    def _reserve_and_dispatch(
        self, job: GenerationJob, user: User, operation: AIOperation, units: int
    ) -> GenerationJob:
        job.credits_reserved = self.credits.reserve(user, operation, units=units)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        # Confier la tache a un worker suppose qu'il y en ait un. Sinon on
        # l'execute ici : une generation lente vaut mieux qu'une tache deposee
        # dans une file que personne ne lit.
        if self.queue.available and self.queue.push(job.id):
            logger.info(
                "tâche de génération mise en file",
                extra={"event": "job_queued"},
            )
            return job

        run_job(job.id, db=self.db)
        self.db.refresh(job)
        return job

    # ------------------------------------------------------------------
    # Reprise
    # ------------------------------------------------------------------
    def stale_queued_ids(self, older_than_seconds: int | None = None) -> list[str]:
        """Taches en attente qu'aucun worker n'a prises.

        Couvre le signal Redis perdu : la tache est en base, la file ne la
        contient plus (ou ne l'a jamais contenue).
        """
        delay = (
            settings.job_stale_seconds if older_than_seconds is None else older_than_seconds
        )
        cutoff = datetime.now(UTC) - timedelta(seconds=delay)
        return list(
            self.db.scalars(
                select(GenerationJob.id)
                .where(GenerationJob.status == JobStatus.QUEUED)
                .where(GenerationJob.created_at < cutoff)
                .order_by(GenerationJob.created_at)
            )
        )

    def fail_timed_out(self) -> int:
        """Termine les taches dont le worker a disparu en cours d'execution.

        Sans cela, une tache resterait `RUNNING` pour toujours et ses credits
        ne seraient jamais rendus.

        Le delai se compte depuis le DERNIER SIGNE DE VIE, pas depuis le
        demarrage : un scenario de quarante passes est long sans etre mort, et
        le tuer parce qu'il dure ferait perdre le travail deja paye.
        """
        cutoff = datetime.now(UTC) - timedelta(seconds=settings.job_timeout_seconds)
        stuck = list(
            self.db.scalars(
                select(GenerationJob)
                .where(GenerationJob.status == JobStatus.RUNNING)
                .where(func.coalesce(GenerationJob.heartbeat_at, GenerationJob.started_at) < cutoff)
            )
        )
        for job in stuck:
            self._fail(
                job,
                code="job_interrupted",
                message=(
                    "La génération a été interrompue avant de se terminer. "
                    "Vos crédits ont été rendus : vous pouvez relancer."
                ),
            )
        if stuck:
            self.db.commit()
            logger.warning(
                "tâches interrompues rendues à l'utilisateur : %s",
                len(stuck),
                extra={"event": "job_timeout"},
            )
        return len(stuck)

    # ------------------------------------------------------------------
    def _fail(self, job: GenerationJob, *, code: str, message: str) -> None:
        user = self.db.get(User, job.user_id)
        if user is not None:
            self.credits.refund(user, job.credits_reserved)
        job.status = JobStatus.FAILED
        job.error_code = code
        job.error_message = message
        job.finished_at = datetime.now(UTC)


# ----------------------------------------------------------------------
# Execution
# ----------------------------------------------------------------------
def run_job(job_id: str, db: Session | None = None) -> JobStatus:
    """Execute une tache. Appelee par le worker, ou par l'API en repli."""
    if db is not None:
        return _run(db, job_id)
    with SessionLocal() as session:
        return _run(session, job_id)


def _run(db: Session, job_id: str) -> JobStatus:
    job = db.get(GenerationJob, job_id)
    if job is None:
        logger.warning("tâche introuvable : %s", job_id, extra={"event": "job_missing"})
        return JobStatus.FAILED
    if job.status != JobStatus.QUEUED:
        # Deja prise par un autre worker, ou deja terminee : ne rien refaire.
        return job.status

    job.status = JobStatus.RUNNING
    job.started_at = datetime.now(UTC)
    job.heartbeat_at = job.started_at
    db.commit()

    user = db.get(User, job.user_id)
    project = db.get(Project, job.project_id)
    if user is None or project is None:
        _finish_failed(db, job, "job_orphaned", "Le projet ou le compte n'existe plus.")
        return JobStatus.FAILED

    documents = DocumentService(db)

    def publish_progress(done: int, total: int) -> None:
        """Rend l'avancement visible pendant que la generation continue.

        Le commit ne porte que sur ce qui est deja acquis : les appels au
        fournisseur deja journalises et le compteur de passes. Le document,
        lui, n'est ecrit qu'une fois toutes les passes terminees.
        """
        job.completed_passes = done
        job.total_passes = max(total, job.total_passes)
        job.heartbeat_at = datetime.now(UTC)
        db.commit()

    try:
        if job.kind == JobKind.RUN_AGENT_CHAIN:
            return _run_agent_chain(db, job, project, publish_progress)
        if job.kind == JobKind.GENERATE_DOCUMENT:
            result = documents.generate(
                user,
                project,
                job.document_type,
                GenerateRequest(**job.payload),
                reserved_credits=job.credits_reserved,
                on_pass=publish_progress,
            )
        else:
            document = documents.get_owned_document(job.document_id or "", project)
            result = documents.refine(
                user,
                project,
                document,
                RefineRequest(**job.payload),
                reserved_credits=job.credits_reserved,
            )
    except AppError as exc:
        _finish_failed(db, job, exc.code, exc.detail)
        return JobStatus.FAILED
    except Exception:  # noqa: BLE001 - une tache ne doit jamais tuer le worker
        logger.exception("échec inattendu de la tâche", extra={"event": "job_crashed"})
        _finish_failed(
            db,
            job,
            "internal_error",
            "La génération a échoué pour une raison inattendue. "
            "Vos crédits ont été rendus : vous pouvez relancer.",
        )
        return JobStatus.FAILED

    job = db.get(GenerationJob, job_id)
    job.status = JobStatus.SUCCEEDED
    job.document_id = result.document.id
    job.result = result.model_dump(mode="json")
    job.completed_passes = job.total_passes
    job.finished_at = datetime.now(UTC)
    db.commit()
    logger.info("tâche de génération terminée", extra={"event": "job_succeeded"})
    return JobStatus.SUCCEEDED


def _finish_failed(db: Session, job: GenerationJob, code: str, message: str) -> None:
    """Termine une tache en echec et rend les credits reserves.

    La session peut etre dans un etat incertain apres l'exception : on la
    rembobine avant d'ecrire le resultat.
    """
    db.rollback()
    job = db.get(GenerationJob, job.id)
    JobService(db)._fail(job, code=code, message=message)
    db.commit()
    logger.info(
        "tâche de génération en échec : %s", code, extra={"event": "job_failed"}
    )


def _run_agent_chain(
    db: Session,
    job: GenerationJob,
    project: Project,
    publish_progress: Callable[[int, int], None],
) -> JobStatus:
    """Execute un passage complet de la chaine et enregistre son resultat.

    Le dossier est sauvegarde **quel que soit le verdict**. Un passage qui
    finit sur `BLOCKED` a tout de meme produit du travail : le jeter obligerait
    a tout refaire pour corriger un seul point, et couterait huit appels de
    plus a chaque tentative.
    """
    from app.agents.orchestrator import Orchestrator
    from app.services.dossier_service import DossierService

    dossiers = DossierService(db)
    state = dossiers.load_state(project.id)

    run = Orchestrator().run(state, on_step=publish_progress)
    record = dossiers.save_run(project.id, run)

    job = db.get(GenerationJob, job.id)
    job.status = JobStatus.SUCCEEDED
    job.completed_passes = len(run.outputs)
    job.total_passes = max(job.total_passes, len(run.outputs))
    job.finished_at = datetime.now(UTC)
    # Le verdict n'est pas le statut de la tache : une chaine qui aboutit a un
    # dossier bloque a reussi son travail, elle a seulement conclu au refus.
    job.result = {
        "run_id": record.id,
        "verdict": run.verdict,
        "exportable": run.is_exportable,
        "rounds": run.rounds,
        "stalled": run.stalled,
        "exhausted": run.exhausted,
        "steps": len(run.outputs),
        "open_findings": len(run.state.unresolved_issues),
    }
    db.commit()
    logger.info(
        "passage de la chaîne terminé",
        extra={
            "event": "agent_chain_finished",
            "verdict": run.verdict,
            "rounds": run.rounds,
            "steps": len(run.outputs),
        },
    )
    return JobStatus.SUCCEEDED
