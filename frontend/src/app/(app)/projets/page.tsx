"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Alert, Badge, EmptyState, ScoreRing, SectionHeading, SkeletonCard } from "@/components/ui";
import { ApiError, projectApi } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { ProjectSummary } from "@/lib/types";

export default function ProjectsPage() {
  const { t, tn, formatRelative } = useI18n();
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (term: string) => {
    try {
      setProjects(await projectApi.list(term || undefined));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("load.failed"));
    }
  }, [t]);

  useEffect(() => {
    const timer = setTimeout(() => void load(search), search ? 300 : 0);
    return () => clearTimeout(timer);
  }, [search, load]);

  return (
    <>
      <SectionHeading
        title={t("projects.title")}
        description={t("projects.subtitle")}
        action={
          <Link href="/projets/nouveau" className="btn-primary">
            {t("nav.newProject")}
          </Link>
        }
      />

      <input
        type="search"
        className="field mb-5"
        placeholder={t("projects.searchPlaceholder")}
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />

      {error ? <Alert tone="danger">{error}</Alert> : null}

      {!projects ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <SkeletonCard lines={3} />
          <SkeletonCard lines={3} />
        </div>
      ) : projects.length === 0 ? (
        <EmptyState
          title={search ? t("projects.noResult") : t("projects.empty")}
          description={
            search ? t("projects.noResultDescription") : t("projects.emptyShort")
          }
          action={
            search ? null : (
              <Link href="/projets/nouveau" className="btn-primary">
                {t("projects.create")}
              </Link>
            )
          }
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {projects.map((project) => (
            <Link
              key={project.id}
              href={`/projets/${project.id}`}
              className="card flex items-start gap-4 p-5 transition-colors hover:border-brass-500/40"
            >
              <ScoreRing value={project.readiness_score} />
              <div className="min-w-0 flex-1">
                <h3 className="truncate font-display text-base text-slatey-100">{project.title}</h3>
                <p className="mt-0.5 truncate text-xs text-slatey-400">
                  {t(`projectType.${project.project_type}`)}
                  {project.genre ? ` · ${project.genre}` : ""}
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <Badge tone="neutral">{t(`projectStatus.${project.status}`)}</Badge>
                  <Badge tone="neutral">
                    {tn("projects.documentCount", project.document_count)}
                  </Badge>
                </div>
                <p className="mt-2.5 text-xs text-slatey-500">
                  {t("projects.updated", { when: formatRelative(project.updated_at) })}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
