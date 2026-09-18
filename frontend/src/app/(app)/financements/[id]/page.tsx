"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DeadlineBadge, StatusBadge } from "@/components/funding";
import { Alert, Badge, SectionHeading, SkeletonCard } from "@/components/ui";
import { ApiError, fundingApi } from "@/lib/api";
import { formatDate } from "@/lib/format";
import {
  DOCUMENT_TYPE_LABELS,
  FUNDING_CATEGORY_LABELS,
  PROJECT_TYPE_LABELS,
} from "@/lib/labels";
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
  const { id } = useParams<{ id: string }>();
  const [opportunity, setOpportunity] = useState<Opportunity | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setOpportunity(await fundingApi.get(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chargement impossible.");
    }
  }, [id]);

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
  const amount =
    opportunity.minimum_budget && opportunity.maximum_budget
      ? `${opportunity.minimum_budget.toLocaleString("fr-FR")} – ${opportunity.maximum_budget.toLocaleString("fr-FR")} ${opportunity.currency}`
      : opportunity.maximum_budget
        ? `jusqu'à ${opportunity.maximum_budget.toLocaleString("fr-FR")} ${opportunity.currency}`
        : opportunity.minimum_budget
          ? `à partir de ${opportunity.minimum_budget.toLocaleString("fr-FR")} ${opportunity.currency}`
          : null;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/financements" className="text-sm text-slatey-400 hover:text-slatey-200">
          ← Financements
        </Link>

        <h1 className="mt-3 font-display text-3xl text-slatey-100">{opportunity.name}</h1>
        <p className="mt-1 text-sm text-slatey-400">{opportunity.organization}</p>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Badge tone="brass">{FUNDING_CATEGORY_LABELS[opportunity.category]}</Badge>
          {opportunity.country ? <Badge tone="neutral">{opportunity.country}</Badge> : null}
          <DeadlineBadge opportunity={summary} />
          <StatusBadge opportunity={summary} />
        </div>
      </div>

      {opportunity.is_demo ? (
        <Alert tone="warning" title="Donnée de démonstration">
          Ce dispositif est fictif (<code>DEMO DATA — NOT REAL</code>). Il sert uniquement à
          illustrer le fonctionnement de la plateforme et ne correspond à aucun financement réel.
        </Alert>
      ) : null}

      {opportunity.status === "UNVERIFIED" ? (
        <Alert tone="warning" title="Fiche non vérifiée">
          Les informations ci-dessous n&apos;ont pas encore été contrôlées par l&apos;équipe.
          Vérifiez-les sur le site de l&apos;organisme avant de préparer votre candidature.
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
        <SectionHeading title="Critères" />
        <dl className="grid gap-4 sm:grid-cols-2">
          <Field label="Montant" value={amount} />
          <Field
            label="Date limite"
            value={opportunity.deadline ? formatDate(opportunity.deadline) : null}
          />
          <Field
            label="Ouverture des candidatures"
            value={opportunity.opening_date ? formatDate(opportunity.opening_date) : null}
          />
          <Field
            label="Pays éligibles"
            value={
              opportunity.eligible_countries.length
                ? opportunity.eligible_countries.join(", ")
                : "Tous les pays"
            }
          />
          <Field
            label="Types de projet"
            value={
              opportunity.project_types.length
                ? opportunity.project_types
                    .map((type) => PROJECT_TYPE_LABELS[type as ProjectType] ?? type)
                    .join(", ")
                : "Tous les types"
            }
          />
          <Field
            label="Genres"
            value={opportunity.genres.length ? opportunity.genres.join(", ") : "Tous les genres"}
          />
          <Field
            label="Langues"
            value={
              opportunity.languages.length ? opportunity.languages.join(", ") : "Toutes les langues"
            }
          />
        </dl>
      </div>

      {/* Pièces à fournir */}
      <div className="card p-6">
        <SectionHeading
          title="Pièces à fournir"
          description="Les documents marqués sont générables depuis l'AI Writer."
        />
        {opportunity.requirement_items.length === 0 && !opportunity.requirements ? (
          <p className="text-sm text-slatey-400">
            Information non fournie. Consultez le règlement sur le site de l&apos;organisme.
          </p>
        ) : (
          <>
            {opportunity.requirement_items.length > 0 ? (
              <ul className="space-y-2">
                {opportunity.requirement_items.map((requirement) => (
                  <li key={requirement.id} className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="text-brass-400">·</span>
                    <span className="text-slatey-200">{requirement.label}</span>
                    {requirement.is_mandatory ? null : (
                      <Badge tone="neutral">facultatif</Badge>
                    )}
                    {requirement.required_document_type ? (
                      <Badge tone="brass">
                        {DOCUMENT_TYPE_LABELS[
                          requirement.required_document_type as DocumentType
                        ] ?? requirement.required_document_type}
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
        <SectionHeading title="Source et candidature" />
        <dl className="grid gap-4 sm:grid-cols-2">
          <Field label="Source de l'information" value={opportunity.source_name} />
          <Field
            label="Dernière vérification"
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
              Candidater sur le site de l&apos;organisme
            </a>
          ) : null}
          {opportunity.source_url ? (
            <a
              href={opportunity.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary"
            >
              Consulter la source
            </a>
          ) : null}
          {opportunity.website ? (
            <a
              href={opportunity.website}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-ghost"
            >
              Site de l&apos;organisme
            </a>
          ) : null}
        </div>

        <p className="mt-4 text-xs leading-relaxed text-slatey-500">
          Les conditions officielles publiées par l&apos;organisme font foi. Vérifiez-les avant
          de déposer votre dossier : une fiche peut avoir été modifiée depuis sa dernière
          vérification.
        </p>
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slatey-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-slatey-200">
        {value || <span className="text-slatey-500">Information non fournie.</span>}
      </dd>
    </div>
  );
}
