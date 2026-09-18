"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Badge,
  EmptyState,
  ScoreRing,
  SectionHeading,
  SkeletonCard,
  Spinner,
} from "@/components/ui";
import { ApiError, documentApi, downloadExport, projectApi } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { DocumentSummary, Project, ReadinessScore } from "@/lib/types";

export default function ProjectDetailPage() {
  const { t, formatRelative, formatPages } = useI18n();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [project, setProject] = useState<Project | null>(null);
  const [score, setScore] = useState<ReadinessScore | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [projectData, documentsData, scoreData] = await Promise.all([
        projectApi.get(id),
        documentApi.list(id),
        projectApi.score(id),
      ]);
      setProject(projectData);
      setDocuments(documentsData);
      setScore(scoreData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("load.failed"));
    }
  }, [id, t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleExport(kind: "pdf" | "zip") {
    setBusy(kind);
    setError(null);
    try {
      await downloadExport(
        `/api/v1/projects/${id}/export/${kind}`,
        `${project?.title ?? t("project.defaultExportName")}.${kind}`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("project.exportFailed"));
    } finally {
      setBusy(null);
    }
  }

  async function handleDelete() {
    if (!window.confirm(t("project.deleteConfirm"))) return;
    setBusy("delete");
    try {
      await projectApi.remove(id);
      router.push("/projets");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("project.deleteFailed"));
      setBusy(null);
    }
  }

  if (error && !project) return <Alert tone="danger">{error}</Alert>;

  if (!project) {
    return (
      <div className="space-y-5">
        <div className="skeleton h-9 w-72 rounded" />
        <SkeletonCard lines={4} />
        <SkeletonCard lines={3} />
      </div>
    );
  }

  return (
    <div className="space-y-9">
      {error ? <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert> : null}

      {/* En-tête */}
      <div>
        <Link href="/projets" className="text-sm text-slatey-400 hover:text-slatey-200">
          {t("newProject.back")}
        </Link>

        <div className="mt-3 flex flex-wrap items-start justify-between gap-5">
          <div className="min-w-0">
            <h1 className="font-display text-3xl text-slatey-100">{project.title}</h1>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <Badge tone="brass">{t(`projectType.${project.project_type}`)}</Badge>
              <Badge tone="neutral">{t(`projectStatus.${project.status}`)}</Badge>
              {project.genre ? <Badge tone="neutral">{project.genre}</Badge> : null}
              {project.country ? <Badge tone="neutral">{project.country}</Badge> : null}
              {project.duration ? <Badge tone="neutral">{project.duration} min</Badge> : null}
            </div>
            {project.logline ? (
              <p className="mt-4 max-w-2xl text-sm leading-relaxed text-slatey-300">
                {project.logline}
              </p>
            ) : null}
          </div>

          <div className="flex shrink-0 items-center gap-4">
            <div className="text-center">
              <ScoreRing value={project.readiness_score} size={72} />
              <p className="mt-1.5 text-xs text-slatey-400">{t("project.readiness")}</p>
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-2.5">
          <Link href={`/projets/${id}/ai-writer`} className="btn-primary">
            {t("project.openWriter")}
          </Link>
          <Link href={`/projets/${id}/financements`} className="btn-secondary">
            {t("project.matchingFunding")}
          </Link>
          <Link href={`/projets/${id}/budget`} className="btn-secondary">
            {t("project.budget")}
          </Link>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => handleExport("pdf")}
            disabled={busy === "pdf"}
          >
            {busy === "pdf" ? <Spinner /> : null}
            {t("project.exportPdf")}
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => handleExport("zip")}
            disabled={busy === "zip"}
          >
            {busy === "zip" ? <Spinner /> : null}
            {t("project.exportZip")}
          </button>
          <button
            type="button"
            className="btn-danger ml-auto"
            onClick={handleDelete}
            disabled={busy === "delete"}
          >
            {t("common.delete")}
          </button>
        </div>
      </div>

      {/* Score détaillé */}
      {score ? (
        <section>
          <SectionHeading
            title={t("project.readinessTitle", { score: score.total })}
            description={t("project.readinessHint")}
          />

          <div className="grid gap-4 lg:grid-cols-5">
            <div className="card p-5 lg:col-span-3">
              <div className="space-y-2.5">
                {score.criteria.map((criterion) => (
                  <div key={criterion.key}>
                    <div className="flex items-baseline justify-between gap-3 text-sm">
                      <span className="text-slatey-200">{criterion.label}</span>
                      <span className="tabular-nums text-slatey-400">
                        {criterion.earned}/{criterion.weight}
                      </span>
                    </div>
                    <div className="mt-1 h-1 overflow-hidden rounded-full bg-ink-700">
                      <div
                        className="h-full rounded-full bg-brass-400"
                        style={{ width: `${(criterion.earned / criterion.weight) * 100}%` }}
                      />
                    </div>
                    <p className="mt-1 text-xs text-slatey-500">{criterion.detail}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="card p-5 lg:col-span-2">
              <h3 className="mb-3 text-sm font-semibold text-slatey-100">{t("project.toImprove")}</h3>
              {score.improvements.length === 0 ? (
                <p className="text-sm text-slatey-400">{t("project.nothingToImprove")}</p>
              ) : (
                <ul className="space-y-2 text-sm text-slatey-300">
                  {score.improvements.map((item) => (
                    <li key={item} className="flex gap-2.5">
                      <span className="text-signal-warning">•</span>
                      {item}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </section>
      ) : null}

      {/* Documents */}
      <section>
        <SectionHeading
          title={t("project.documents")}
          action={
            <Link href={`/projets/${id}/ai-writer`} className="btn-secondary">
              {t("project.generateDocument")}
            </Link>
          }
        />

        {documents.length === 0 ? (
          <EmptyState
            title={t("project.noDocument")}
            description={t("project.noDocumentHint")}
            action={
              <Link href={`/projets/${id}/ai-writer`} className="btn-primary">
                {t("project.openWriter")}
              </Link>
            }
          />
        ) : (
          <div className="space-y-2.5">
            {documents.map((document) => (
              <Link
                key={document.id}
                href={`/projets/${id}/documents/${document.id}`}
                className="card flex flex-wrap items-center justify-between gap-4 p-4 transition-colors hover:border-brass-500/40"
              >
                <div className="min-w-0">
                  <p className="font-medium text-slatey-100">
                    {t(`documentType.${document.document_type}`)}
                  </p>
                  <p className="mt-0.5 text-xs text-slatey-400">
                    {t("project.documentMeta", {
                      words: document.word_count,
                      pages: formatPages(document.word_count),
                      version: document.current_version,
                      when: formatRelative(document.updated_at),
                    })}
                  </p>
                </div>
                <Badge tone={document.status === "FINAL" ? "success" : "neutral"}>
                  {t(`documentStatus.${document.status}`)}
                </Badge>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Personnages */}
      <section>
        <SectionHeading
          title={t("project.characters")}
          description={t("project.charactersHint")}
        />
        {project.characters.length === 0 ? (
          <div className="card p-6 text-sm text-slatey-400">
            {t("project.noCharacter")}
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {project.characters.map((character) => (
              <div key={character.id} className="card p-5">
                <div className="flex items-baseline justify-between gap-3">
                  <h3 className="font-display text-base text-slatey-100">{character.name}</h3>
                  {character.age ? (
                    <span className="text-xs text-slatey-500">{character.age}</span>
                  ) : null}
                </div>
                {character.role ? (
                  <p className="mt-0.5 text-xs uppercase tracking-wide text-brass-300">
                    {character.role}
                  </p>
                ) : null}
                {character.description ? (
                  <p className="mt-2.5 text-sm leading-relaxed text-slatey-300">
                    {character.description}
                  </p>
                ) : null}
                {character.arc ? (
                  <p className="mt-2.5 border-t border-ink-700 pt-2.5 text-sm text-slatey-400">
                    <span className="text-slatey-500">{t("project.arc")}</span>
                    {character.arc}
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
