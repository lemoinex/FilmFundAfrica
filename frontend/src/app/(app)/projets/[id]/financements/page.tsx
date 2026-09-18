"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  CompatibilityBar,
  CriterionRow,
  DeadlineBadge,
  ScoreDisclaimer,
  SourceLine,
  StatusBadge,
} from "@/components/funding";
import { Markdown } from "@/components/markdown";
import { Alert, Badge, EmptyState, SectionHeading, SkeletonCard, Spinner } from "@/components/ui";
import { ApiError, fundingApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatRelative } from "@/lib/format";
import { FUNDING_CATEGORY_LABELS } from "@/lib/labels";
import type { MatchExplanation, MatchListResponse, MatchResult } from "@/lib/types";

export default function ProjectFundingPage() {
  const { id } = useParams<{ id: string }>();
  const { setCredits, user } = useAuth();

  const [data, setData] = useState<MatchListResponse | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [explanations, setExplanations] = useState<Record<string, MatchExplanation>>({});
  const [explaining, setExplaining] = useState<string | null>(null);
  const [analysing, setAnalysing] = useState(false);
  const [onlyEligible, setOnlyEligible] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await fundingApi.matches(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chargement impossible.");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleAnalyse() {
    setAnalysing(true);
    setError(null);
    try {
      setData(await fundingApi.computeMatches(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Analyse impossible.");
    } finally {
      setAnalysing(false);
    }
  }

  async function handleExplain(opportunityId: string) {
    setExplaining(opportunityId);
    setError(null);
    try {
      const explanation = await fundingApi.explain(id, opportunityId);
      setExplanations((current) => ({ ...current, [opportunityId]: explanation }));
      setCredits(explanation.credits_remaining);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Explication impossible.");
    } finally {
      setExplaining(null);
    }
  }

  const results = useMemo(() => {
    if (!data) return [];
    return onlyEligible ? data.results.filter((result) => result.eligible) : data.results;
  }, [data, onlyEligible]);

  const ineligibleCount = (data?.results.length ?? 0) - (data?.results.filter((r) => r.eligible).length ?? 0);

  if (error && !data) return <Alert tone="danger">{error}</Alert>;
  if (!data) {
    return (
      <div className="space-y-5">
        <div className="skeleton h-9 w-72 rounded" />
        <SkeletonCard lines={4} />
        <SkeletonCard lines={4} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <Link href={`/projets/${id}`} className="text-sm text-slatey-400 hover:text-slatey-200">
          ← {data.project_title}
        </Link>

        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl text-slatey-100">Financements compatibles</h1>
            <p className="mt-1.5 text-sm text-slatey-400">
              Analyse calculée par règles — aucun crédit IA consommé. Dernier calcul{" "}
              {formatRelative(data.computed_at)}.
            </p>
          </div>

          <button
            type="button"
            className="btn-primary"
            onClick={handleAnalyse}
            disabled={analysing}
          >
            {analysing ? <Spinner /> : null}
            Relancer l&apos;analyse
          </button>
        </div>
      </div>

      {error ? <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert> : null}

      {data.total === 0 ? (
        <EmptyState
          title="Aucun dispositif dans la base"
          description="La base des financements est encore vide. Un administrateur peut y ajouter des dispositifs ; l'analyse se relancera ensuite automatiquement."
          action={
            <Link href="/financements" className="btn-secondary">
              Voir les financements
            </Link>
          }
        />
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-slatey-300">
              <span className="font-semibold text-slatey-100">{results.length}</span>{" "}
              opportunité{results.length > 1 ? "s" : ""}
              {onlyEligible && ineligibleCount > 0
                ? ` · ${ineligibleCount} écartée${ineligibleCount > 1 ? "s" : ""} pour inéligibilité`
                : ""}
            </p>
            {ineligibleCount > 0 ? (
              <label className="flex cursor-pointer items-center gap-2 text-sm text-slatey-300">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-brass-400"
                  checked={!onlyEligible}
                  onChange={(event) => setOnlyEligible(!event.target.checked)}
                />
                Afficher les dispositifs inéligibles
              </label>
            ) : null}
          </div>

          <div className="space-y-3">
            {results.map((result) => (
              <MatchCard
                key={result.opportunity.id}
                projectId={id}
                result={result}
                open={expanded === result.opportunity.id}
                onToggle={() =>
                  setExpanded((current) =>
                    current === result.opportunity.id ? null : result.opportunity.id,
                  )
                }
                explanation={explanations[result.opportunity.id]}
                explaining={explaining === result.opportunity.id}
                onExplain={() => handleExplain(result.opportunity.id)}
                creditsLeft={user?.ai_credits_remaining ?? 0}
              />
            ))}
          </div>

          <ScoreDisclaimer>{data.disclaimer}</ScoreDisclaimer>
        </>
      )}
    </div>
  );
}

function MatchCard({
  projectId,
  result,
  open,
  onToggle,
  explanation,
  explaining,
  onExplain,
  creditsLeft,
}: {
  projectId: string;
  result: MatchResult;
  open: boolean;
  onToggle: () => void;
  explanation?: MatchExplanation;
  explaining: boolean;
  onExplain: () => void;
  creditsLeft: number;
}) {
  const { opportunity } = result;

  return (
    <div className={result.eligible ? "card p-5" : "card border-ink-800 p-5 opacity-75"}>
      {/* En-tête */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Link
              href={`/financements/${opportunity.id}`}
              className="font-display text-base text-slatey-100 hover:text-brass-200"
            >
              {opportunity.name}
            </Link>
            {!result.eligible ? <Badge tone="danger">Inéligible</Badge> : null}
          </div>
          <p className="mt-0.5 text-xs text-slatey-400">{opportunity.organization}</p>
        </div>
        <CompatibilityBar value={result.compatibility} eligible={result.eligible} />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Badge tone="brass">{FUNDING_CATEGORY_LABELS[opportunity.category]}</Badge>
        {opportunity.amount_label ? (
          <Badge tone="neutral">{opportunity.amount_label}</Badge>
        ) : null}
        <DeadlineBadge opportunity={opportunity} />
        <StatusBadge opportunity={opportunity} />
      </div>

      {/* Synthèse */}
      <div className="mt-4 grid gap-2 text-sm sm:grid-cols-3">
        <Summary tone="success" count={result.met_conditions.length} label="remplie" />
        <Summary tone="danger" count={result.missing_conditions.length} label="non remplie" />
        <Summary tone="neutral" count={result.unknown_conditions.length} label="à vérifier" />
      </div>

      {result.assessed_ratio < 100 ? (
        <p className="mt-3 text-xs text-slatey-500">
          Score calculé sur {result.assessed_ratio} % de la grille : complétez votre projet pour
          l&apos;affiner. Les critères non évaluables ne sont ni comptés pour, ni contre vous.
        </p>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-ink-800 pt-4">
        <button type="button" className="btn-secondary px-3 py-1.5 text-xs" onClick={onToggle}>
          {open ? "Masquer le détail" : "Voir le détail du score"}
        </button>

        {explanation ? null : (
          <button
            type="button"
            className="btn-secondary px-3 py-1.5 text-xs"
            onClick={onExplain}
            disabled={explaining || creditsLeft < 1}
            title={
              creditsLeft < 1
                ? "Crédits IA épuisés"
                : result.has_explanation
                  ? "Explication déjà rédigée : aucun crédit ne sera débité"
                  : "Consomme 1 crédit IA"
            }
          >
            {explaining ? <Spinner className="h-3 w-3" /> : null}
            {result.has_explanation ? "Afficher l'analyse" : "Analyser avec l'IA (1 crédit)"}
          </button>
        )}

        <Link
          href={`/financements/${opportunity.id}`}
          className="btn-ghost px-3 py-1.5 text-xs"
        >
          Fiche complète
        </Link>

        <div className="ml-auto">
          <SourceLine opportunity={opportunity} />
        </div>
      </div>

      {/* Détail du score */}
      {open ? (
        <div className="mt-4 space-y-4 border-t border-ink-800 pt-4">
          <div>
            <p className="mb-1 text-xs uppercase tracking-wide text-slatey-400">
              Détail des critères
            </p>
            <ul className="divide-y divide-ink-800">
              {result.criteria.map((criterion) => (
                <CriterionRow key={criterion.key} criterion={criterion} />
              ))}
            </ul>
          </div>

          {result.required_documents.length > 0 ? (
            <div>
              <p className="mb-2 text-xs uppercase tracking-wide text-slatey-400">
                Documents exigés
              </p>
              <div className="flex flex-wrap gap-2">
                {result.required_documents.map((document) => {
                  const missing = result.missing_documents.includes(document);
                  return (
                    <Badge key={document} tone={missing ? "danger" : "success"}>
                      {missing ? "✕" : "✓"} {document}
                    </Badge>
                  );
                })}
              </div>
              {result.missing_documents.length > 0 ? (
                <Link
                  href={`/projets/${projectId}/ai-writer`}
                  className="btn-secondary mt-3 px-3 py-1.5 text-xs"
                >
                  Générer les documents manquants
                </Link>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      {/* Explication IA */}
      {explanation ? (
        <div className="mt-4 rounded-lg border border-ink-700 bg-ink-800/40 p-5">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs uppercase tracking-wide text-brass-300">Analyse détaillée</p>
            <p className="text-xs text-slatey-500">
              {explanation.credits_consumed === 0
                ? "Analyse déjà produite — aucun crédit débité"
                : `${explanation.credits_consumed} crédit · ${explanation.provider}`}
            </p>
          </div>
          <Markdown content={explanation.explanation} />
        </div>
      ) : null}
    </div>
  );
}

function Summary({
  tone,
  count,
  label,
}: {
  tone: "success" | "danger" | "neutral";
  count: number;
  label: string;
}) {
  const colors = {
    success: "text-signal-success",
    danger: "text-signal-danger",
    neutral: "text-slatey-400",
  } as const;

  return (
    <p className="text-slatey-400">
      <span className={`font-semibold tabular-nums ${colors[tone]}`}>{count}</span> condition
      {count > 1 ? "s" : ""} {label}
      {count > 1 ? "s" : ""}
    </p>
  );
}
