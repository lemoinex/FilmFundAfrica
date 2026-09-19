"""Orchestrateur : deroule la chaine, puis la reprend tant qu'il le faut.

La chaine n'est pas lineaire. Les six premiers agents construisent, les deux
derniers statuent, et un verdict negatif renvoie le dossier a l'agent capable
de le corriger — puis a tous ceux qui en dependent.

Deux garde-fous, pour des raisons opposees :

* **Un nombre de tours borne.** Deux validateurs qui ne s'accordent pas
  boucleraient jusqu'a epuisement du budget. Au-dela de la limite, on rend la
  main avec le dernier verdict connu plutot que de continuer a payer.
* **Aucun export force.** Arriver au bout des tours ne vaut pas validation. Un
  dossier qui sort de la boucle sans `PASS` reste non exportable.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from app.agents import (
    AGENT_PIPELINE,
    BUILDER_AGENTS,
    VALIDATOR_AGENTS,
    correction_route,
    get_agent,
)
from app.agents.contracts import AgentInput, AgentOutput, Finding, ProjectState
from app.agents.runner import AgentRunner, owner_or_default
from app.models.enums import AgentRole, ValidationVerdict

logger = logging.getLogger("filmfund.agents")

#: Tours de correction au-dela du premier passage.
#:
#: Trois suffisent a absorber les allers-retours utiles ; au-dela, le probleme
#: n'est plus une incoherence mais un desaccord que seul un humain tranchera.
DEFAULT_MAX_CORRECTION_ROUNDS = 3


@dataclass(slots=True)
class PipelineRun:
    """Resultat d'un passage complet, exportable ou non."""

    state: ProjectState
    outputs: list[AgentOutput] = field(default_factory=list)
    verdict: ValidationVerdict | None = None
    rounds: int = 0
    #: Vrai quand la boucle s'est arretee sur sa limite, pas sur un verdict.
    exhausted: bool = False
    #: Vrai quand un tour n'a rien change aux constats ouverts.
    stalled: bool = False
    #: Signal d'avancement, appele apres chaque agent.
    _on_step: Callable[[int, int], None] | None = None

    @property
    def is_exportable(self) -> bool:
        from app.agents import is_exportable

        return self.verdict is not None and is_exportable(self.verdict)

    def blocking_findings(self) -> list[Finding]:
        return self.state.blocking_issues()


class Orchestrator:
    """Enchaine les agents et pilote la boucle de correction."""

    def __init__(
        self,
        runner: AgentRunner | None = None,
        *,
        max_correction_rounds: int = DEFAULT_MAX_CORRECTION_ROUNDS,
    ) -> None:
        self.runner = runner or AgentRunner()
        self.max_correction_rounds = max_correction_rounds

    # ------------------------------------------------------------------
    def run(
        self,
        state: ProjectState,
        *,
        funding_requirements: dict | None = None,
        project_context: dict | None = None,
        on_step: Callable[[int, int], None] | None = None,
    ) -> PipelineRun:
        """Deroule la chaine, puis la reprend tant qu'il le faut.

        `on_step` est appele apres chaque agent. Ce n'est pas un confort
        d'affichage : un passage complet peut depasser le delai au-dela duquel
        une tache est declaree interrompue, et sans signe de vie regulier le
        surveillant tuerait une chaine qui travaille.
        """
        run = PipelineRun(state=state, _on_step=on_step)

        self._run_sequence(
            run, BUILDER_AGENTS + VALIDATOR_AGENTS, funding_requirements, project_context
        )

        while not run.is_exportable and run.rounds < self.max_correction_rounds:
            target = self._correction_target(run)
            if target is None:
                # Verdict negatif sans destinataire : rejouer a l'identique
                # redonnerait le meme resultat. On s'arrete et on le dit.
                break
            before = self._issue_signature(run)
            run.rounds += 1
            logger.info(
                "reprise de la chaîne",
                extra={
                    "event": "agent_correction_round",
                    "round": run.rounds,
                    "from_agent": target,
                    "verdict": run.verdict,
                },
            )
            self._run_sequence(
                run, correction_route(target), funding_requirements, project_context
            )

            if self._issue_signature(run) == before:
                # Un tour qui ne change rien ne changera rien au suivant : le
                # rejouer coute huit appels au fournisseur pour le meme
                # resultat. On s'arrete et on le signale plutot que d'epuiser
                # la limite en silence.
                run.stalled = True
                logger.info(
                    "reprise sans effet, arrêt de la boucle",
                    extra={"event": "agent_correction_stalled", "round": run.rounds},
                )
                break

        run.exhausted = (
            not run.is_exportable and not run.stalled and run.rounds >= self.max_correction_rounds
        )
        return run

    # ------------------------------------------------------------------
    @staticmethod
    def _issue_signature(run: PipelineRun) -> frozenset[tuple[str, str, str]]:
        """Empreinte des constats ouverts, pour reperer un tour sans effet."""
        return frozenset(
            (issue.severity.value, issue.element, issue.description)
            for issue in run.state.unresolved_issues
        )

    # ------------------------------------------------------------------
    def _run_sequence(
        self,
        run: PipelineRun,
        sequence: tuple[AgentRole, ...],
        funding_requirements: dict | None,
        project_context: dict | None,
    ) -> None:
        for role in sequence:
            definition = get_agent(role)
            payload = AgentInput(
                project_state=run.state,
                previous_agent_outputs=run.outputs,
                current_agent_role=role,
                funding_requirements=funding_requirements or {},
                project_context=project_context or {},
            )
            output = self.runner.run(definition, payload)
            run.outputs.append(output)
            if output.updated_state is not None:
                run.state = output.updated_state
            if role in VALIDATOR_AGENTS and output.verdict is not None:
                run.verdict = output.verdict
            if run._on_step is not None:
                # Le total annonce est celui d'un passage propre : une reprise
                # le depasse, et c'est a l'appelant de le borner s'il l'affiche.
                run._on_step(len(run.outputs), len(AGENT_PIPELINE))

    # ------------------------------------------------------------------
    @staticmethod
    def _correction_target(run: PipelineRun) -> AgentRole | None:
        """Agent par lequel reprendre : le plus en amont des constats ouverts.

        Reprendre au plus amont plutot qu'au plus grave : corriger le budget
        avant le scenario laisserait le budget a refaire une fois le scenario
        modifie. L'ordre du pipeline est deja l'ordre des dependances.
        """
        open_issues = [
            issue for issue in run.state.unresolved_issues if issue.severity.name != "PASS"
        ]
        if not open_issues:
            return None
        owners = {
            owner_or_default(issue, AgentRole.DEVELOPMENT)
            for issue in open_issues
            # Un constat que seul un validateur peut lever ne relance rien :
            # il n'a personne a qui rendre le dossier.
            if owner_or_default(issue, AgentRole.DEVELOPMENT) in BUILDER_AGENTS
        }
        if not owners:
            return None
        return min(owners, key=BUILDER_AGENTS.index)
