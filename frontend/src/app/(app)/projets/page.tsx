"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Alert, Badge, EmptyState, ScoreRing, SectionHeading, SkeletonCard } from "@/components/ui";
import { ApiError, projectApi } from "@/lib/api";
import { formatRelative } from "@/lib/format";
import { PROJECT_STATUS_LABELS, PROJECT_TYPE_LABELS } from "@/lib/labels";
import type { ProjectSummary } from "@/lib/types";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (term: string) => {
    try {
      setProjects(await projectApi.list(term || undefined));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chargement impossible.");
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => void load(search), search ? 300 : 0);
    return () => clearTimeout(timer);
  }, [search, load]);

  return (
    <>
      <SectionHeading
        title="Mes projets"
        description="Chaque projet regroupe ses documents, ses versions et son score de maturité."
        action={<Link href="/projets/nouveau" className="btn-primary">Nouveau projet</Link>}
      />

      <input
        type="search"
        className="field mb-5"
        placeholder="Rechercher un projet par titre…"
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
          title={search ? "Aucun résultat" : "Aucun projet pour l'instant"}
          description={
            search
              ? "Aucun projet ne correspond à cette recherche."
              : "Créez votre premier projet : l'assistant vous guide en sept étapes."
          }
          action={
            search ? null : (
              <Link href="/projets/nouveau" className="btn-primary">Créer mon projet</Link>
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
    </>
  );
}
