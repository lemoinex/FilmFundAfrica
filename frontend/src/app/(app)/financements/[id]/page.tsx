"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DeadlineBadge, StatusBadge } from "@/components/funding";
import { Alert, Badge, SectionHeading, SkeletonCard } from "@/components/ui";
import { ApiError, fundingApi } from "@/lib/api";
import { useI18n, type Translate } from "@/lib/i18n";
import { DOCUMENT_TYPES, PROJECT_TYPES } from "@/lib/labels";
import type { DocumentType, Opportunity, OpportunitySummary, ProjectType } from "@/lib/types";

/** Reconstruit le résumé attendu par les badges à partir de la fiche complète. */
function toSummary(opportunity: Opportunity): OpportunitySummary {
  const days =
    opportunity.deadline != null
      ? Math.ceil(
          (new Date(opportunity.deadline).getTime() - Date.now()) / (1000 * 60 * 60 * 24),
        )
      : null;
  return { ...opportunity, days_left: days, amount_label: null };
}

export default function OpportunityDetailPage() {
  const { t, formatDate, formatNumber } = useI18n();
  const { id } = useParams<{ id: string }>();
  const [opportunity, setOpportunity] = useState<Opportunity | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setOpportunity(await fundingApi.get(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("load.failed"));
    }
  }, [id, t]);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) return <Alert tone="danger">{error}</Alert>;
  if (!opportunity) {
    return (
      <div className="space-y-5">
        <div className="skeleton h-9 w-80 rounded" />
        <SkeletonCard lines={6} />
      </div>
    );
  }

  const summary = toSummary(opportunity);
  const currency = opportunity.currency;
  const amount =
    opportunity.minimum_budget && opportunity.maximum_budget
      ? t("opportunity.amountRange", {
          min: formatNumber(opportunity.minimum_budget),
          max: formatNumber(opportunity.maximum_budget),
          currency,
        })
      : opportunity.maximum_budget
        ? t("opportunity.amountUpTo", {
            max: formatNumber(opportunity.maximum_budget),
            currency,
          })
        : opportunity.minimum_budget
          ? t("opportunity.amountFrom", {
              min: formatNumber(opportunity.minimum_budget),
              currency,
            })
          : null;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/financements" className="text-sm text-slatey-400 hover:text-slatey-200">
          {t("opportunity.backToList")}
        </Link>

        <h1 className="mt-3 font-display text-3xl text-slatey-100">{opportunity.name}</h1>
        <p className="mt-1 text-sm text-slatey-400">{opportunity.organization}</p>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Badge tone="brass">{t(`fundingCategory.${opportunity.category}`)}</Badge>
          {opportunity.country ? <Badge tone="neutral">{opportunity.country}</Badge> : null}
          <DeadlineBadge opportunity={summary} />
          <StatusBadge opportunity={summary} />
        </div>
      </div>

      {opportunity.is_demo ? (
        <Alert tone="warning" title={t("opportunity.demoTitle")}>
          <code>{t("funding.demoData")}</code> — {t("opportunity.demoBody")}
        </Alert>
      ) : null}

      {opportunity.status === "UNVERIFIED" ? (
        <Alert tone="warning" title={t("opportunity.unverifiedTitle")}>
          {t("opportunity.unverifiedBody")}
        </Alert>
      ) : null}

      {opportunity.description ? (
        <div className="card p-6">
          <p className="whitespace-pre-line text-sm leading-relaxed text-slatey-300">
            {opportunity.description}
          </p>
        </div>
      ) : null}

      {/* Critères d'éligibilité */}
      <div className="card p-6">
        <SectionHeading title={t("opportunity.criteria")} />
        <dl className="grid gap-4 sm:grid-cols-2">
          <Field t={t} label={t("opportunity.amount")} value={amount} />
          <Field
            t={t}
            label={t("opportunity.deadline")}
            value={opportunity.deadline ? formatDate(opportunity.deadline) : null}
          />
          <Field
            t={t}
            label={t("opportunity.opening")}
            value={opportunity.opening_date ? formatDate(opportunity.opening_date) : null}
          />
          <Field
            t={t}
            label={t("opportunity.eligibleCountries")}
            value={
              opportunity.eligible_countries.length
                ? opportunity.eligible_countries.join(", ")
                : t("opportunity.allCountries")
            }
          />
          <Field
            t={t}
            label={t("opportunity.projectTypes")}
            value={
              opportunity.project_types.length
                ? opportunity.project_types
                    .map((type) =>
                      PROJECT_TYPES.includes(type as ProjectType)
                        ? t(`projectType.${type as ProjectType}`)
                        : type,
                    )
                    .join(", ")
                : t("opportunity.allTypes")
            }
          />
          <Field
            t={t}
            label={t("opportunity.genres")}
            value={
              opportunity.genres.length
                ? opportunity.genres.join(", ")
                : t("opportunity.allGenres")
            }
          />
          <Field
            t={t}
            label={t("opportunity.languages")}
            value={
              opportunity.languages.length
                ? opportunity.languages.join(", ")
                : t("opportunity.allLanguages")
            }
          />
        </dl>
      </div>

      {/* Pièces à fournir */}
      <div className="card p-6">
        <SectionHeading
          title={t("opportunity.requirements")}
          description={t("opportunity.requirementsHint")}
        />
        {opportunity.requirement_items.length === 0 && !opportunity.requirements ? (
          <p className="text-sm text-slatey-400">{t("opportunity.requirementsMissing")}</p>
        ) : (
          <>
            {opportunity.requirement_items.length > 0 ? (
              <ul className="space-y-2">
                {opportunity.requirement_items.map((requirement) => (
                  <li key={requirement.id} className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="text-brass-400">·</span>
                    <span className="text-slatey-200">{requirement.label}</span>
                    {requirement.is_mandatory ? null : (
                      <Badge tone="neutral">{t("opportunity.requirementOptional")}</Badge>
                    )}
                    {requirement.required_document_type ? (
                      <Badge tone="brass">
                        {DOCUMENT_TYPES.includes(
                          requirement.required_document_type as DocumentType,
                        )
                          ? t(`documentType.${requirement.required_document_type as DocumentType}`)
                          : requirement.required_document_type}
                      </Badge>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : null}
            {opportunity.requirements ? (
              <p className="mt-4 whitespace-pre-line border-t border-ink-800 pt-4 text-sm text-slatey-400">
                {opportunity.requirements}
              </p>
            ) : null}
          </>
        )}
      </div>

      {/* Traçabilité et candidature */}
      <div className="card p-6">
        <SectionHeading title={t("opportunity.sourceSection")} />
        <dl className="grid gap-4 sm:grid-cols-2">
          <Field t={t} label={t("opportunity.sourceName")} value={opportunity.source_name} />
          <Field
            t={t}
            label={t("opportunity.lastCheck")}
            value={
              opportunity.last_verified_at ? formatDate(opportunity.last_verified_at) : null
            }
          />
        </dl>

        <div className="mt-5 flex flex-wrap gap-2.5 border-t border-ink-800 pt-5">
          {opportunity.application_url ? (
            <a
              href={opportunity.application_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary"
            >
              {t("opportunity.apply")}
            </a>
          ) : null}
          {opportunity.source_url ? (
            <a
              href={opportunity.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary"
            >
              {t("opportunity.openSource")}
            </a>
          ) : null}
          {opportunity.website ? (
            <a
              href={opportunity.website}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-ghost"
            >
              {t("opportunity.website")}
            </a>
          ) : null}
        </div>

        <p className="mt-4 text-xs leading-relaxed text-slatey-500">
          {t("opportunity.officialTerms")}
        </p>
      </div>
    </div>
  );
}

function Field({ t, label, value }: { t: Translate; label: string; value?: string | null }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slatey-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-slatey-200">
        {value || <span className="text-slatey-500">{t("opportunity.notProvided")}</span>}
      </dd>
    </div>
  );
}
