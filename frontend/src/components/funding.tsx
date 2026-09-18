"use client";

import Link from "next/link";

import { Badge } from "@/components/ui";
import { useI18n } from "@/lib/i18n";
import type { MatchCriterion, MatchState, OpportunitySummary } from "@/lib/types";

/**
 * Traçabilité affichée sous chaque opportunité.
 *
 * Règle produit : aucune opportunité n'est présentée comme active sans sa
 * source ni sa date de dernière vérification. Quand l'une manque, on le dit
 * explicitement plutôt que de laisser croire que la fiche est à jour.
 */
export function SourceLine({ opportunity }: { opportunity: OpportunitySummary }) {
  const { t, formatDate } = useI18n();
  const verified = opportunity.last_verified_at;

  return (
    <p className="text-xs text-slatey-500">
      {opportunity.source_url ? (
        <a
          href={opportunity.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-slatey-400 underline decoration-ink-600 underline-offset-2 hover:text-brass-300"
        >
          {opportunity.source_name || t("funding.source")}
        </a>
      ) : (
        <span className="text-signal-warning">{t("funding.sourceMissing")}</span>
      )}
      {" · "}
      {verified ? (
        <>{t("funding.verifiedOn", { date: formatDate(verified) })}</>
      ) : (
        <span className="text-signal-warning">{t("funding.neverVerified")}</span>
      )}
    </p>
  );
}

export function DeadlineBadge({ opportunity }: { opportunity: OpportunitySummary }) {
  const { t, tn, formatDate } = useI18n();
  const days = opportunity.days_left;

  if (opportunity.deadline == null) {
    return <Badge tone="neutral">{t("funding.noDeadline")}</Badge>;
  }
  if (days != null && days < 0) {
    return <Badge tone="danger">{t("funding.deadlinePassed")}</Badge>;
  }
  if (days != null && days <= 14) {
    return <Badge tone="warning">{tn("funding.daysLeft", days)}</Badge>;
  }
  return <Badge tone="neutral">{formatDate(opportunity.deadline)}</Badge>;
}

export function StatusBadge({ opportunity }: { opportunity: OpportunitySummary }) {
  const { t } = useI18n();
  // La mention de démonstration a la même valeur dans les deux catalogues :
  // elle doit rester reconnaissable telle quelle, quelle que soit la langue.
  if (opportunity.is_demo) return <Badge tone="warning">{t("funding.demoData")}</Badge>;

  const tone =
    opportunity.status === "OPEN"
      ? "success"
      : opportunity.status === "UNVERIFIED"
        ? "warning"
        : "neutral";
  return <Badge tone={tone}>{t(`fundingStatus.${opportunity.status}`)}</Badge>;
}

/** Barre de compatibilité, teintée selon le niveau. */
export function CompatibilityBar({
  value,
  eligible = true,
}: {
  value: number;
  eligible?: boolean;
}) {
  const color = !eligible
    ? "bg-slatey-500"
    : value >= 70
      ? "bg-signal-success"
      : value >= 40
        ? "bg-brass-400"
        : "bg-signal-danger";

  return (
    <div className="flex items-center gap-3">
      <div className="h-1.5 w-28 overflow-hidden rounded-full bg-ink-700">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${value}%` }} />
      </div>
      <span className="w-10 text-right text-sm font-semibold tabular-nums text-slatey-200">
        {value}%
      </span>
    </div>
  );
}

const STATE_MARKS: Record<MatchState, { mark: string; className: string }> = {
  met: { mark: "✓", className: "text-signal-success" },
  unmet: { mark: "✕", className: "text-signal-danger" },
  unknown: { mark: "?", className: "text-slatey-500" },
};

export function CriterionRow({ criterion }: { criterion: MatchCriterion }) {
  const { t } = useI18n();
  const { mark, className } = STATE_MARKS[criterion.state];

  return (
    <li className="flex gap-3 py-1.5 text-sm">
      <span className={`mt-0.5 w-3 shrink-0 font-semibold ${className}`}>{mark}</span>
      <span className="flex-1 text-slatey-300">
        <span className="text-slatey-200">{criterion.label}</span>
        {criterion.blocking && criterion.state === "unmet" ? (
          <span className="ml-2 text-xs uppercase tracking-wide text-signal-danger">
            {t("funding.blocking")}
          </span>
        ) : null}
        <br />
        <span className="text-slatey-400">{criterion.detail}</span>
      </span>
      <span className="shrink-0 text-xs tabular-nums text-slatey-500">
        {criterion.state === "unknown" ? "—" : `${criterion.earned}/${criterion.weight}`}
      </span>
    </li>
  );
}

export function OpportunityCard({
  opportunity,
  href,
  trailing,
}: {
  opportunity: OpportunitySummary;
  href?: string;
  trailing?: React.ReactNode;
}) {
  const { t } = useI18n();
  const body = (
    <div className="card p-5 transition-colors hover:border-brass-500/40">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="font-display text-base text-slatey-100">{opportunity.name}</h3>
          <p className="mt-0.5 text-xs text-slatey-400">{opportunity.organization}</p>
        </div>
        {trailing}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Badge tone="brass">{t(`fundingCategory.${opportunity.category}`)}</Badge>
        {opportunity.country ? <Badge tone="neutral">{opportunity.country}</Badge> : null}
        {opportunity.amount_label ? (
          <Badge tone="neutral">{opportunity.amount_label}</Badge>
        ) : null}
        <DeadlineBadge opportunity={opportunity} />
        <StatusBadge opportunity={opportunity} />
      </div>

      <div className="mt-3 border-t border-ink-800 pt-2.5">
        <SourceLine opportunity={opportunity} />
      </div>
    </div>
  );

  return href ? (
    <Link href={href} className="block">
      {body}
    </Link>
  ) : (
    body
  );
}

/** Rappel obligatoire affiché avec tout score de compatibilité. */
export function ScoreDisclaimer({ children }: { children?: React.ReactNode }) {
  const { t } = useI18n();
  return (
    <p className="rounded-lg border border-ink-700 bg-ink-900/60 px-4 py-3 text-xs leading-relaxed text-slatey-400">
      {children ?? t("funding.scoreDisclaimer")}
    </p>
  );
}
