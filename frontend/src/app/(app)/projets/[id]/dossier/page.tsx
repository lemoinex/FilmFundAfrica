"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Alert, Badge, EmptyState, SectionHeading, SkeletonCard, Spinner } from "@/components/ui";
import {
  ApiError,
  authApi,
  dossierApi,
  downloadExport,
  projectApi,
  waitForJob,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useI18n } from "@/lib/i18n";
import type {
  AgentChainResult,
  AgentRun,
  AgentRunDetail,
  Dossier,
  DossierFinding,
  DossierModification,
  DossierStatus,
  GenerationJob,
  Project,
  Severity,
} from "@/lib/types";

/** Sections affichées, dans l'ordre où les agents les remplissent. */
const SECTIONS = [
  "concept",
  "screenplay",
  "director_vision",
  "production_plan",
  "financing_plan",
  "impact_analysis",
] as const;

/** Un passage propre : huit agents, donc huit crédits. */
const AGENT_COUNT = 8;

const SEVERITY_TONE: Record<Severity, "danger" | "warning" | "neutral" | "success"> = {
  CRITICAL: "danger",
  MAJOR: "warning",
  MINOR: "neutral",
  PASS: "success",
};

export default function DossierPage() {
  const { t, tn, formatRelative, formatDateTime } = useI18n();
  const { id } = useParams<{ id: string }>();
  const { setCredits } = useAuth();

  const [project, setProject] = useState<Project | null>(null);
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [status, setStatus] = useState<DossierStatus | null>(null);
  const [findings, setFindings] = useState<DossierFinding[]>([]);
  const [modifications, setModifications] = useState<DossierModification[]>([]);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [openRun, setOpenRun] = useState<AgentRunDetail | null>(null);

  const [showResolved, setShowResolved] = useState(false);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<GenerationJob | null>(null);
  const [outcome, setOutcome] = useState<AgentChainResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<"pdf" | "docx" | null>(null);

  const refresh = useCallback(
    async (withResolved: boolean) => {
      const [nextDossier, nextStatus, nextFindings, nextModifications, nextRuns] =
        await Promise.all([
          dossierApi.get(id),
          dossierApi.status(id),
          dossierApi.findings(id, withResolved),
          dossierApi.modifications(id),
          dossierApi.runs(id),
        ]);
      setDossier(nextDossier);
      setStatus(nextStatus);
      setFindings(nextFindings);
      setModifications(nextModifications);
      setRuns(nextRuns);
    },
    [id],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const loaded = await projectApi.get(id);
        if (!cancelled) setProject(loaded);
        await refresh(false);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : t("dossier.loadFailed"));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, refresh, t]);

  async function handleRun() {
    setError(null);
    setOutcome(null);
    setProgress(null);
    setRunning(true);
    try {
      // Le passage est une tâche : huit appels au fournisseur ne tiennent pas
      // dans une requête HTTP. On suit son avancement au lieu d'attendre.
      const job = await dossierApi.run(id);
      const result = await waitForJob<AgentChainResult>(job, { onProgress: setProgress });
      setOutcome(result);
      await refresh(showResolved);
      // Huit crédits viennent de partir : sans cette relecture, le compteur
      // de l'en-tête resterait sur sa valeur d'avant le passage.
      setCredits((await authApi.me()).ai_credits_remaining);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("dossier.runFailed"));
    } finally {
      setRunning(false);
      setProgress(null);
    }
  }

  async function handleExport(format: "pdf" | "docx") {
    setExporting(format);
    setError(null);
    try {
      // Le nom du fichier vient du serveur : c'est lui qui sait si le dossier
      // part en « brouillon », et ce mot ne doit pas se perdre en route.
      await downloadExport(
        `/api/v1/projects/${id}/export/dossier/${format}`,
        `${project?.title ?? t("dossier.title")}.${format}`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("dossier.exportFailed"));
    } finally {
      setExporting(null);
    }
  }

  async function toggleResolved() {
    const next = !showResolved;
    setShowResolved(next);
    setFindings(await dossierApi.findings(id, next));
  }

  async function openRunDetail(runId: string) {
    if (openRun?.id === runId) {
      setOpenRun(null);
      return;
    }
    setOpenRun(await dossierApi.run_detail(id, runId));
  }

  if (error && !project) return <Alert tone="danger">{error}</Alert>;
  if (!project || !status) {
    return (
      <div className="space-y-4">
        <SkeletonCard lines={2} />
        <SkeletonCard lines={4} />
      </div>
    );
  }

  const neverRan = status.runs === 0;

  return (
    <div className="space-y-8">
      <div>
        <Link
          href={`/projets/${id}`}
          className="text-sm text-slatey-400 transition-colors hover:text-slatey-200"
        >
          ← {project.title}
        </Link>
        <h1 className="mt-2 text-2xl font-semibold text-slatey-50">{t("dossier.title")}</h1>
        <p className="mt-1 max-w-2xl text-sm text-slatey-400">{t("dossier.subtitle")}</p>
      </div>

      {/* Verdict — la seule chose qui décide si le dossier peut partir. */}
      {!neverRan ? (
        <section
          className={
            status.exportable
              ? "card border-signal-success/40 p-5"
              : "card border-signal-warning/40 p-5"
          }
        >
          <div className="flex flex-wrap items-center gap-3">
            <Badge tone={status.exportable ? "success" : "warning"}>
              {status.exportable ? t("dossier.exportable") : t("dossier.notExportable")}
            </Badge>
            {status.verdict ? (
              <span className="text-sm text-slatey-300">
                {t(`dossier.verdict.${status.verdict}`)}
              </span>
            ) : null}
            {status.last_run_at ? (
              <span className="text-xs text-slatey-500">
                {t("dossier.lastRun", { when: formatRelative(status.last_run_at) })}
              </span>
            ) : null}
          </div>

          {status.open_findings > 0 ? (
            <p className="mt-3 text-sm text-slatey-300">
              {tn("dossier.openFindings", status.open_findings, {
                count: status.open_findings,
              })}
              {status.blocking_findings > 0
                ? `, ${tn("dossier.blockingFindings", status.blocking_findings, {
                    count: status.blocking_findings,
                  })}`
                : ""}
            </p>
          ) : null}

          {/* Une relecture humaine reste due : l'outil ne la remplace pas. */}
          {status.exportable ? (
            <p className="hint mt-2">{t("dossier.exportableHint")}</p>
          ) : null}
        </section>
      ) : null}

      {/* Lancer */}
      <section className="card p-5">
        {neverRan ? (
          <div className="mb-4">
            <p className="text-sm text-slatey-200">{t("dossier.neverRun")}</p>
            <p className="hint mt-1">{t("dossier.neverRunHint")}</p>
          </div>
        ) : null}

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            className="btn-primary"
            onClick={handleRun}
            disabled={running}
          >
            {running ? <Spinner /> : null}
            {neverRan ? t("dossier.run") : t("dossier.rerun")}
          </button>
          {!neverRan ? (
            <>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => handleExport("pdf")}
                disabled={exporting !== null}
              >
                {exporting === "pdf" ? <Spinner /> : null}
                {status.exportable ? t("dossier.exportPdf") : t("dossier.exportDraft")}
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => handleExport("docx")}
                disabled={exporting !== null}
              >
                {exporting === "docx" ? <Spinner /> : null}
                {t("dossier.exportDocx")}
              </button>
            </>
          ) : null}
          <span className="text-sm text-slatey-400">
            {tn("dossier.cost", AGENT_COUNT, { count: AGENT_COUNT })}
          </span>
          {status.runs > 0 ? (
            <span className="text-xs text-slatey-500">
              {tn("dossier.runsCount", status.runs, { count: status.runs })}
            </span>
          ) : null}
        </div>
        <p className="hint mt-2">{t("dossier.costHint")}</p>

        {running && progress ? (
          <div className="mt-4">
            <p className="text-sm text-slatey-300">
              {t("dossier.progress", {
                done: progress.completed_passes,
                total: Math.max(progress.total_passes, progress.completed_passes),
              })}
            </p>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-ink-700">
              <div
                className="h-full bg-brass-500 transition-all duration-500"
                style={{
                  width: `${Math.min(
                    100,
                    (progress.completed_passes /
                      Math.max(progress.total_passes, progress.completed_passes, 1)) *
                      100,
                  )}%`,
                }}
              />
            </div>
          </div>
        ) : null}

        {/* Une reprise sans effet ou une limite atteinte se dit : sinon on
            relancerait indéfiniment sans comprendre pourquoi rien ne bouge. */}
        {outcome?.stalled ? (
          <div className="mt-4">
            <Alert tone="warning">{t("dossier.stalled")}</Alert>
          </div>
        ) : null}
        {outcome?.exhausted ? (
          <div className="mt-4">
            <Alert tone="warning">{t("dossier.exhausted")}</Alert>
          </div>
        ) : null}

        {error ? (
          <div className="mt-4">
            <Alert tone="danger" onDismiss={() => setError(null)}>
              {error}
            </Alert>
          </div>
        ) : null}
      </section>

      {/* Constats — les plus graves d'abord, avec leur destinataire. */}
      <section>
        <SectionHeading
          title={t("dossier.findings")}
          action={
            <button type="button" className="btn-secondary text-xs" onClick={toggleResolved}>
              {showResolved ? t("dossier.hideResolved") : t("dossier.showResolved")}
            </button>
          }
        />
        {findings.length === 0 ? (
          <EmptyState
            title={t("dossier.noFinding")}
            description={t("dossier.noFindingHint")}
          />
        ) : (
          <div className="space-y-2.5">
            {findings.map((finding) => (
              <div
                key={finding.id}
                className={
                  finding.resolved_at ? "card p-4 opacity-60" : "card p-4"
                }
              >
                <div className="flex flex-wrap items-center gap-2.5">
                  <Badge tone={SEVERITY_TONE[finding.severity]}>
                    {t(`severity.${finding.severity}`)}
                  </Badge>
                  <span className="text-sm font-medium text-slatey-100">
                    {finding.element}
                  </span>
                  {finding.resolved_at ? (
                    <Badge tone="success">{t("dossier.resolved")}</Badge>
                  ) : null}
                </div>
                <p className="mt-2 text-sm text-slatey-300">{finding.description}</p>
                {finding.owner ? (
                  <p className="mt-2 text-xs text-slatey-500">
                    {t("dossier.toFix")} · {t(`agent.${finding.owner}`)}
                  </p>
                ) : null}
                {finding.suggested_correction ? (
                  <p className="mt-1 text-xs text-slatey-400">
                    {t("dossier.suggestion")} : {finding.suggested_correction}
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Le dossier lui-même */}
      <section>
        <SectionHeading title={t("dossier.sections")} />
        <div className="grid gap-3 sm:grid-cols-2">
          {SECTIONS.map((section) => {
            const content = dossier?.[section] ?? {};
            const entries = Object.entries(content);
            return (
              <div key={section} className="card p-4">
                <h3 className="text-sm font-semibold text-slatey-100">
                  {t(`dossier.section.${section}`)}
                </h3>
                {entries.length === 0 ? (
                  <p className="mt-2 text-sm text-slatey-500">{t("dossier.emptySection")}</p>
                ) : (
                  <dl className="mt-2 space-y-1.5 text-sm">
                    {entries.map(([key, value]) => (
                      <div key={key} className="flex gap-2">
                        <dt className="shrink-0 text-slatey-500">{key}</dt>
                        <dd className="text-slatey-200">
                          {typeof value === "object"
                            ? JSON.stringify(value)
                            : String(value)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* Traçabilité : qui a changé quoi, et pourquoi. */}
      <section>
        <SectionHeading title={t("dossier.history")} />
        {modifications.length === 0 ? (
          <EmptyState
            title={t("dossier.noHistory")}
            description={t("dossier.noHistoryHint")}
          />
        ) : (
          <div className="space-y-2">
            {modifications.map((row) => (
              <div key={row.id} className="card flex flex-wrap gap-3 p-3.5 text-sm">
                <Badge tone="neutral">{t(`agent.${row.agent}`)}</Badge>
                <span className="text-slatey-100">{row.element}</span>
                <span className="text-slatey-400">{row.reason}</span>
                <span className="ml-auto text-xs text-slatey-500">
                  {formatRelative(row.created_at)}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Passages */}
      {runs.length > 0 ? (
        <section>
          <SectionHeading title={t("dossier.runs")} />
          <div className="space-y-2">
            {runs.map((run) => (
              <div key={run.id} className="card p-4">
                <button
                  type="button"
                  className="flex w-full flex-wrap items-center gap-3 text-left"
                  onClick={() => openRunDetail(run.id)}
                  aria-expanded={openRun?.id === run.id}
                >
                  {run.verdict ? (
                    <Badge tone={run.verdict === "PASS" ? "success" : "warning"}>
                      {t(`dossier.verdict.${run.verdict}`)}
                    </Badge>
                  ) : null}
                  <span className="text-sm text-slatey-300">
                    {run.rounds === 0
                      ? t("dossier.noRound")
                      : tn("dossier.rounds", run.rounds, { count: run.rounds })}
                  </span>
                  <span className="ml-auto text-xs text-slatey-500">
                    {formatDateTime(run.created_at)}
                  </span>
                </button>

                {/* Un passage qui s'est arrêté faute de progrès le dit ici
                    aussi : après rechargement, `outcome` a disparu, et sans
                    cela on relancerait sans comprendre pourquoi rien ne bouge. */}
                {run.stalled ? (
                  <p className="mt-2 text-xs text-signal-warning">{t("dossier.stalled")}</p>
                ) : null}
                {run.exhausted ? (
                  <p className="mt-2 text-xs text-signal-warning">{t("dossier.exhausted")}</p>
                ) : null}

                {openRun?.id === run.id ? (
                  <ol className="mt-4 space-y-3 border-t border-ink-700 pt-4">
                    {openRun.steps.map((step) => (
                      <li key={step.id}>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-xs text-slatey-500">
                            {t("dossier.step", { n: step.sequence })}
                          </span>
                          <span className="text-sm font-medium text-slatey-100">
                            {t(`agent.${step.agent}`)}
                          </span>
                          {step.verdict ? (
                            <Badge tone={step.verdict === "PASS" ? "success" : "warning"}>
                              {t(`dossier.verdict.${step.verdict}`)}
                            </Badge>
                          ) : null}
                        </div>
                        {step.rationale ? (
                          <p className="mt-1 text-sm text-slatey-400">{step.rationale}</p>
                        ) : null}
                      </li>
                    ))}
                  </ol>
                ) : null}
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
