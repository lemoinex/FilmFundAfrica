"use client";

import Link from "next/link";

import { Badge } from "@/components/ui";
import { formatDate } from "@/lib/format";
import { FUNDING_CATEGORY_LABELS, FUNDING_STATUS_LABELS } from "@/lib/labels";
import type { MatchCriterion, MatchState, OpportunitySummary } from "@/lib/types";

/**
 * Traçabilité affichée sous chaque opportunité.
 *
 * Règle produit : aucune opportunité n'est présentée comme active sans sa
 * source ni sa date de dernière vérification. Quand l'une manque, on le dit
 * explicitement plutôt que de laisser croire que la fiche est à jour.
 */
export function SourceLine({ opportunity }: { opportunity: OpportunitySummary }) {
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
          {opportunity.source_name || "Source"}
        </a>
      ) : (
        <span className="text-signal-warning">Source non renseignée</span>
      )}
      {" · "}
      {verified ? (
        <>Vérifié le {formatDate(verified)}</>
      ) : (
        <span className="text-signal-warning">jamais vérifié</span>
      )}
    </p>
  );
}

export function DeadlineBadge({ opportunity }: { opportunity: OpportunitySummary }) {
  const days = opportunity.days_left;

  if (opportunity.deadline == null) {
    return <Badge tone="neutral">Sans date limite</Badge>;
  }
  if (days != null && days < 0) {
    return <Badge tone="danger">Échéance dépassée</Badge>;
  }
  if (days != null && days <= 14) {
    return <Badge tone="warning">J-{days}</Badge>;
  }
  return <Badge tone="neutral">{formatDate(opportunity.deadline)}</Badge>;
}

export function StatusBadge({ opportunity }: { opportunity: OpportunitySummary }) {
  if (opportunity.is_demo) return <Badge tone="warning">DEMO DATA — NOT REAL</Badge>;
  if (opportunity.status === "UNVERIFIED") return <Badge tone="warning">Non vérifié</Badge>;
  if (opportunity.status === "CLOSED") return <Badge tone="neutral">Clos</Badge>;
  if (opportunity.status === "UPCOMING") return <Badge tone="neutral">À venir</Badge>;
  return <Badge tone="success">{FUNDING_STATUS_LABELS[opportunity.status]}</Badge>;
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
  const { mark, className } = STATE_MARKS[criterion.state];

  return (
    <li className="flex gap-3 py-1.5 text-sm">
      <span className={`mt-0.5 w-3 shrink-0 font-semibold ${className}`}>{mark}</span>
      <span className="flex-1 text-slatey-300">
        <span className="text-slatey-200">{criterion.label}</span>
        {criterion.blocking && criterion.state === "unmet" ? (
          <span className="ml-2 text-xs uppercase tracking-wide text-signal-danger">
            bloquant
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
        <Badge tone="brass">{FUNDING_CATEGORY_LABELS[opportunity.category]}</Badge>
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
  return (
    <p className="rounded-lg border border-ink-700 bg-ink-900/60 px-4 py-3 text-xs leading-relaxed text-slatey-400">
      {children ??
        "Le score de compatibilité est un indicateur d'aide à la décision. Il ne garantit en aucun cas l'obtention d'un financement : les conditions officielles de l'organisme font foi et doivent être vérifiées sur son site."}
    </p>
  );
}
