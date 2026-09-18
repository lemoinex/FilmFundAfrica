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
import { useI18n, type PluralKey, type Translate, type TranslatePlural } from "@/lib/i18n";
import type { MatchExplanation, MatchListResponse, MatchResult } from "@/lib/types";

export default function ProjectFundingPage() {
  const { t, tn, formatRelative } = useI18n();
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
      setError(err instanceof ApiError ? err.message : t("load.failed"));
    }
  }, [id, t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleAnalyse() {
    setAnalysing(true);
    setError(null);
    try {
      setData(await fundingApi.computeMatches(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("match.failed"));
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
      setError(err instanceof ApiError ? err.message : t("match.explainFailed"));
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
            <h1 className="font-display text-3xl text-slatey-100">{t("match.title")}</h1>
            <p className="mt-1.5 text-sm text-slatey-400">
              {t("match.subtitle", { when: formatRelative(data.computed_at) })}
            </p>
          </div>

          <button
            type="button"
            className="btn-primary"
            onClick={handleAnalyse}
            disabled={analysing}
          >
            {analysing ? <Spinner /> : null}
            {t("match.rerun")}
          </button>
        </div>
      </div>

      {error ? <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert> : null}

      {data.total === 0 ? (
        <EmptyState
          title={t("match.emptyBase")}
          description={t("match.emptyBaseHint")}
          action={
            <Link href="/financements" className="btn-secondary">
              {t("match.seeFunding")}
            </Link>
          }
        />
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-slatey-300">
              {tn("match.count", results.length)}
              {onlyEligible && ineligibleCount > 0
                ? tn("match.excluded", ineligibleCount)
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
                {t("match.showIneligible")}
              </label>
            ) : null}
          </div>

          <div className="space-y-3">
            {results.map((result) => (
              <MatchCard
                key={result.opportunity.id}
                t={t}
                tn={tn}
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
  t,
  tn,
  projectId,
  result,
  open,
  onToggle,
  explanation,
  explaining,
  onExplain,
  creditsLeft,
}: {
  t: Translate;
  tn: TranslatePlural;
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
            {!result.eligible ? <Badge tone="danger">{t("match.ineligible")}</Badge> : null}
          </div>
          <p className="mt-0.5 text-xs text-slatey-400">{opportunity.organization}</p>
        </div>
        <CompatibilityBar value={result.compatibility} eligible={result.eligible} />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Badge tone="brass">{t(`fundingCategory.${opportunity.category}`)}</Badge>
        {opportunity.amount_label ? (
          <Badge tone="neutral">{opportunity.amount_label}</Badge>
        ) : null}
        <DeadlineBadge opportunity={opportunity} />
        <StatusBadge opportunity={opportunity} />
      </div>

      {/* Synthèse */}
      <div className="mt-4 grid gap-2 text-sm sm:grid-cols-3">
        <Summary
          tone="success"
          tn={tn}
          count={result.met_conditions.length}
          label="match.conditionsMet"
        />
        <Summary
          tone="danger"
          tn={tn}
          count={result.missing_conditions.length}
          label="match.conditionsUnmet"
        />
        <Summary
          tone="neutral"
          tn={tn}
          count={result.unknown_conditions.length}
          label="match.conditionsUnknown"
        />
      </div>

      {result.assessed_ratio < 100 ? (
        <p className="mt-3 text-xs text-slatey-500">
          {t("match.partialScore", { ratio: result.assessed_ratio })}
        </p>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-ink-800 pt-4">
        <button type="button" className="btn-secondary px-3 py-1.5 text-xs" onClick={onToggle}>
          {t(open ? "match.hideDetail" : "match.showDetail")}
        </button>

        {explanation ? null : (
          <button
            type="button"
            className="btn-secondary px-3 py-1.5 text-xs"
            onClick={onExplain}
            disabled={explaining || creditsLeft < 1}
            title={
              creditsLeft < 1
                ? t("match.noCredits")
                : result.has_explanation
                  ? t("match.alreadyExplained")
                  : t("match.costsOneCredit")
            }
          >
            {explaining ? <Spinner className="h-3 w-3" /> : null}
            {t(result.has_explanation ? "match.showExplanation" : "match.explainWithAi")}
          </button>
        )}

        <Link
          href={`/financements/${opportunity.id}`}
          className="btn-ghost px-3 py-1.5 text-xs"
        >
          {t("match.fullEntry")}
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
              {t("match.criteriaDetail")}
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
                {t("match.requiredDocuments")}
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
                  {t("match.generateMissing")}
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
            <p className="text-xs uppercase tracking-wide text-brass-300">
              {t("match.explanationTitle")}
            </p>
            <p className="text-xs text-slatey-500">
              {explanation.credits_consumed === 0
                ? t("match.explanationFree")
                : t("match.explanationCost", {
                    credits: explanation.credits_consumed,
                    provider: explanation.provider,
                  })}
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
  tn,
  count,
  label,
}: {
  tone: "success" | "danger" | "neutral";
  tn: TranslatePlural;
  count: number;
  label: PluralKey;
}) {
  const colors = {
    success: "text-signal-success",
    danger: "text-signal-danger",
    neutral: "text-slatey-400",
  } as const;

  return (
    <p className="text-slatey-400">
      <span className={`font-semibold tabular-nums ${colors[tone]}`}>{count}</span>{" "}
      {tn(label, count)}
    </p>
  );
}
