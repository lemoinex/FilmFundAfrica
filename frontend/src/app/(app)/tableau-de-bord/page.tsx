"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Badge,
  EmptyState,
  ScoreRing,
  SectionHeading,
  SkeletonCard,
  StatTile,
} from "@/components/ui";
import { ApiError, dashboardApi } from "@/lib/api";
import { formatDate, formatRelative } from "@/lib/format";
import { PROJECT_STATUS_LABELS, PROJECT_TYPE_LABELS } from "@/lib/labels";
import type { DashboardResponse } from "@/lib/types";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await dashboardApi.get());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chargement impossible.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) return <Alert tone="danger">{error}</Alert>;

  if (!data) {
    return (
      <div className="space-y-6">
        <div className="skeleton h-8 w-64 rounded" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <SkeletonCard key={index} lines={1} />
          ))}
        </div>
        <SkeletonCard lines={4} />
      </div>
    );
  }

  return (
    <div className="space-y-9">
      <div>
        <h1 className="font-display text-3xl text-slatey-100">
          Bienvenue, {data.welcome_name}
        </h1>
        <p className="mt-1.5 text-sm text-slatey-400">
          Voici l&apos;état de vos projets et de vos échéances.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Mes projets" value={data.stats.projects} href="/projets" />
        <StatTile label="Documents générés" value={data.stats.documents_generated} />
        <StatTile
          label="Opportunités compatibles"
          value={data.stats.compatible_opportunities}
          hint="Module Phase 3"
        />
        <StatTile
          label="Échéances prochaines"
          value={data.stats.upcoming_deadlines}
          hint="45 prochains jours"
        />
      </div>

      {data.notifications.filter((item) => !item.is_read).length > 0 ? (
        <div className="space-y-2">
          {data.notifications
            .filter((item) => !item.is_read)
            .slice(0, 3)
            .map((notification) => (
              <Alert key={notification.id} tone="info" title={notification.title}>
                {notification.body}
              </Alert>
            ))}
        </div>
      ) : null}

      <section>
        <SectionHeading
          title="Mes projets"
          action={
            <Link href="/projets/nouveau" className="btn-secondary">
              Nouveau projet
            </Link>
          }
        />

        {data.projects.length === 0 ? (
          <EmptyState
            title="Aucun projet pour l'instant"
            description="Créez votre premier projet : l'assistant vous guide en sept étapes, de l'idée au public visé."
            action={
              <Link href="/projets/nouveau" className="btn-primary">
                Créer mon projet
              </Link>
            }
          />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {data.projects.map((project) => (
              <Link
                key={project.id}
                href={`/projets/${project.id}`}
                className="card flex items-start gap-4 p-5 transition-colors hover:border-brass-500/40"
              >
                <ScoreRing value={project.readiness_score} />
                <div className="min-w-0 flex-1">
                  <h3 className="truncate font-display text-base text-slatey-100">
                    {project.title}
                  </h3>
                  <p className="mt-0.5 truncate text-xs text-slatey-400">
                    {PROJECT_TYPE_LABELS[project.project_type]}
                    {project.genre ? ` · ${project.genre}` : ""}
                  </p>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <Badge tone="neutral">{PROJECT_STATUS_LABELS[project.status]}</Badge>
                    <Badge tone="neutral">
                      {project.document_count} document{project.document_count > 1 ? "s" : ""}
                    </Badge>
                  </div>
                  <p className="mt-2.5 text-xs text-slatey-500">
                    Modifié {formatRelative(project.updated_at)}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionHeading
          title="Opportunités recommandées"
          description="Chaque opportunité est affichée avec sa source et sa date de dernière vérification."
        />

        {data.recommended_opportunities.length === 0 ? (
          <div className="card p-6 text-sm text-slatey-400">
            Aucune recommandation pour l&apos;instant. Le module Funding Intelligence, qui
            alimente cette section, arrive en Phase 3.
          </div>
        ) : (
          <div className="space-y-2.5">
            {data.recommended_opportunities.map((opportunity) => (
              <div key={opportunity.id} className="card p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-display text-base text-slatey-100">
                        {opportunity.name}
                      </h3>
                      {opportunity.is_demo ? (
                        <Badge tone="warning">DEMO DATA — NOT REAL</Badge>
                      ) : null}
                    </div>
                    <p className="mt-0.5 text-xs text-slatey-400">{opportunity.organization}</p>
                  </div>
                  <span className="shrink-0 text-sm font-semibold tabular-nums text-brass-200">
                    {opportunity.compatibility}%
                  </span>
                </div>

                <dl className="mt-4 grid gap-3 text-xs text-slatey-400 sm:grid-cols-3">
                  <div>
                    <dt className="text-slatey-500">Montant</dt>
                    <dd className="text-slatey-200">{opportunity.amount_label ?? "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-slatey-500">Date limite</dt>
                    <dd className="text-slatey-200">{formatDate(opportunity.deadline)}</dd>
                  </div>
                  <div>
                    <dt className="text-slatey-500">Vérifié le</dt>
                    <dd className="text-slatey-200">
                      {formatDate(opportunity.last_verified_at)}
                      {opportunity.source_name ? ` · ${opportunity.source_name}` : ""}
                    </dd>
                  </div>
                </dl>
              </div>
            ))}
            <p className="px-1 pt-1 text-xs text-slatey-500">
              Le score de compatibilité est un indicateur d&apos;aide à la décision et ne
              garantit en aucun cas l&apos;obtention d&apos;un financement.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
