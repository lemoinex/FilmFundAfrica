"""Pont entre l'etat en memoire de la chaine et sa forme persistee.

`ProjectState` est ce que les agents manipulent ; `ProjectDossier` est ce qui
survit. Les deux se ressemblent assez pour que la conversion soit ennuyeuse, et
assez peu pour qu'elle merite d'etre au meme endroit plutot que dispersee.

Deux ecarts assumes entre les deux formes :

* `validation_history` n'est pas stockee. Chaque etape de validateur porte deja
  son verdict ; la dupliquer creerait deux verites qui finiraient par diverger.
* Un constat resolu n'est pas supprime mais date. Savoir qu'un blocage a existe,
  et quand il a ete leve, fait partie de l'histoire du dossier — et c'est ce
  qu'un comite demande quand il rouvre un projet.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.contracts import Finding, ModificationTrace, ProjectState, TrackedFact
from app.agents.orchestrator import PipelineRun
from app.models.agents import (
    AgentRun,
    AgentStep,
    DossierFinding,
    DossierModification,
    ProjectDossier,
)
from app.models.enums import JobStatus

#: Sections du dossier portees a l'identique de part et d'autre.
SECTIONS = (
    "project_identity",
    "concept",
    "synopsis",
    "characters",
    "screenplay",
    "director_vision",
    "production_plan",
    "budget",
    "financing_plan",
    "cultural_analysis",
    "impact_analysis",
    "final_documents",
)


class DossierService:
    """Charge, enregistre et relit le dossier d'un projet."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    def get_or_create(self, project_id: str) -> ProjectDossier:
        dossier = self.db.scalar(
            select(ProjectDossier).where(ProjectDossier.project_id == project_id)
        )
        if dossier is None:
            dossier = ProjectDossier(project_id=project_id)
            self.db.add(dossier)
            self.db.flush()
        return dossier

    # ------------------------------------------------------------------
    def load_state(self, project_id: str) -> ProjectState:
        """Etat de la chaine tel qu'il a ete laisse au dernier passage."""
        dossier = self.get_or_create(project_id)
        state = ProjectState(
            project_id=project_id,
            **{section: getattr(dossier, section) or _empty(section) for section in SECTIONS},
        )
        if dossier.logline:
            state.logline = TrackedFact.model_validate(dossier.logline)

        state.unresolved_issues = [
            Finding(
                severity=row.severity,
                element=row.element,
                description=row.description,
                owner=row.owner,
                suggested_correction=row.suggested_correction,
            )
            for row in self._open_findings(dossier.id)
        ]
        state.modifications_history = [
            ModificationTrace(
                agent=row.agent,
                element=row.element,
                previous_value=row.previous_value,
                new_value=row.new_value,
                reason=row.reason,
                impact=row.impact,
                validation_status=row.validation_status,
                version=row.version,
                recorded_at=row.created_at,
            )
            for row in dossier.modifications
        ]
        # Reconstituee depuis les etapes plutot que stockee : une seule verite.
        state.validation_history = self.verdict_history(dossier.id)
        return state

    # ------------------------------------------------------------------
    def save_run(self, project_id: str, run: PipelineRun) -> AgentRun:
        """Enregistre un passage complet : dossier, etapes, constats, traces."""
        dossier = self.get_or_create(project_id)

        for section in SECTIONS:
            setattr(dossier, section, getattr(run.state, section))
        dossier.logline = run.state.logline.model_dump(mode="json") if run.state.logline else None

        record = AgentRun(
            dossier_id=dossier.id,
            # La colonne existait deja pour cela : un passage arrete a la
            # demande n'a pas reussi, il a ete interrompu. L'export s'en sert
            # pour ne pas dire que « les controles ont releve des points »
            # alors qu'ils n'ont pas tourne.
            status=JobStatus.CANCELLED if run.cancelled else JobStatus.SUCCEEDED,
            verdict=run.verdict,
            rounds=run.rounds,
            exhausted=run.exhausted,
            stalled=run.stalled,
            finished_at=datetime.now(UTC),
        )
        self.db.add(record)
        self.db.flush()

        for index, output in enumerate(run.outputs, 1):
            self.db.add(
                AgentStep(
                    run_id=record.id,
                    sequence=index,
                    agent=output.agent,
                    agent_version=output.version,
                    analysis=output.analysis,
                    rationale=output.rationale,
                    next_agent_instructions=output.next_agent_instructions,
                    verdict=output.verdict,
                    changeset=output.modifications.model_dump(mode="json"),
                    decisions=[d.model_dump(mode="json") for d in output.decisions],
                    provider=output.telemetry.provider,
                    model=output.telemetry.model,
                    input_tokens=output.telemetry.input_tokens,
                    output_tokens=output.telemetry.output_tokens,
                    latency_ms=output.telemetry.latency_ms,
                )
            )

        self._replace_findings(dossier, record, run.state.unresolved_issues)
        self._append_modifications(dossier, record, run.state.modifications_history)
        self.db.flush()
        return record

    # ------------------------------------------------------------------
    def _replace_findings(
        self, dossier: ProjectDossier, run: AgentRun, findings: list[Finding]
    ) -> None:
        """Aligne les constats ouverts sur ce que le passage a laisse.

        Ce qui n'y est plus a ete leve : on le date au lieu de l'effacer. Un
        constat qui disparait sans trace empeche de savoir si le probleme a ete
        corrige ou simplement oublie.
        """
        still_open = {(f.severity, f.element, f.description) for f in findings}
        existing = self._open_findings(dossier.id)
        known = {(row.severity, row.element, row.description) for row in existing}

        resolved_at = datetime.now(UTC)
        for row in existing:
            if (row.severity, row.element, row.description) not in still_open:
                row.resolved_at = resolved_at

        for finding in findings:
            if (finding.severity, finding.element, finding.description) in known:
                continue
            self.db.add(
                DossierFinding(
                    dossier_id=dossier.id,
                    run_id=run.id,
                    severity=finding.severity,
                    element=finding.element,
                    description=finding.description,
                    owner=finding.owner,
                    suggested_correction=finding.suggested_correction,
                )
            )

    # ------------------------------------------------------------------
    def _append_modifications(
        self, dossier: ProjectDossier, run: AgentRun, traces: list[ModificationTrace]
    ) -> None:
        """N'enregistre que les traces nouvelles.

        `load_state` a rempli l'historique depuis la base ; le reecrire en
        entier dupliquerait chaque passage precedent.
        """
        already = len(dossier.modifications)
        for trace in traces[already:]:
            self.db.add(
                DossierModification(
                    dossier_id=dossier.id,
                    run_id=run.id,
                    agent=trace.agent,
                    element=trace.element,
                    previous_value=trace.previous_value,
                    new_value=trace.new_value,
                    reason=trace.reason,
                    impact=trace.impact,
                    validation_status=trace.validation_status,
                    version=trace.version,
                )
            )

    # ------------------------------------------------------------------
    def _open_findings(self, dossier_id: str) -> list[DossierFinding]:
        return list(
            self.db.scalars(
                select(DossierFinding).where(
                    DossierFinding.dossier_id == dossier_id,
                    DossierFinding.resolved_at.is_(None),
                )
            )
        )

    # ------------------------------------------------------------------
    def verdict_history(self, dossier_id: str) -> list:
        """Verdicts rendus, du plus ancien au plus recent."""
        return list(
            self.db.scalars(
                select(AgentStep.verdict)
                .join(AgentRun, AgentStep.run_id == AgentRun.id)
                .where(AgentRun.dossier_id == dossier_id, AgentStep.verdict.is_not(None))
                .order_by(AgentRun.created_at, AgentStep.sequence)
            )
        )


def _empty(section: str):
    """Valeur vide correspondant au type de la section."""
    return [] if section in ("characters", "final_documents") else {}
