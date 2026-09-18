"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { Markdown } from "@/components/markdown";
import { Alert, Badge, SectionHeading, SkeletonCard, Spinner } from "@/components/ui";
import { ApiError, documentApi, downloadExport, waitForJob } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useI18n, type MessageKey } from "@/lib/i18n";
import type { DocumentStatus, DocumentVersion, ProjectDocument, RefineAction } from "@/lib/types";

const AUTOSAVE_DELAY_MS = 2500;

const DOCUMENT_STATUSES: DocumentStatus[] = ["DRAFT", "IN_REVIEW", "FINAL"];

/** Origines connues d'une version. Une origine inconnue s'affiche telle quelle
 *  plutôt que sous forme de clé : le serveur peut en introduire de nouvelles. */
const ORIGINS = [
  "MANUAL",
  "AI_GENERATE",
  "AI_IMPROVE",
  "AI_SHORTEN",
  "AI_EXPAND",
  "AI_CORRECT",
  "RESTORE",
] as const;

const REFINE_ACTIONS: { action: RefineAction; label: MessageKey }[] = [
  { action: "IMPROVE", label: "editor.refine.IMPROVE" },
  { action: "SHORTEN", label: "editor.refine.SHORTEN" },
  { action: "EXPAND", label: "editor.refine.EXPAND" },
  { action: "CORRECT", label: "editor.refine.CORRECT" },
];

type SaveState = "idle" | "dirty" | "saving" | "saved" | "error";

export default function DocumentEditorPage() {
  const { t, formatDateTime, formatPages } = useI18n();
  const { id, documentId } = useParams<{ id: string; documentId: string }>();
  const { setCredits } = useAuth();

  const [document, setDocument] = useState<ProjectDocument | null>(null);
  const [content, setContent] = useState("");
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [mode, setMode] = useState<"edit" | "preview">("preview");
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [busyAction, setBusyAction] = useState<RefineAction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const savedContent = useRef("");

  const load = useCallback(async () => {
    try {
      const [documentData, versionsData] = await Promise.all([
        documentApi.get(id, documentId),
        documentApi.versions(id, documentId),
      ]);
      setDocument(documentData);
      setContent(documentData.content);
      savedContent.current = documentData.content;
      setVersions(versionsData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("load.failed"));
    }
  }, [id, documentId, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const save = useCallback(
    async (nextContent: string, status?: DocumentStatus, note?: string) => {
      setSaveState("saving");
      try {
        const updated = await documentApi.save(id, documentId, {
          content: nextContent,
          status,
          note,
        });
        setDocument(updated);
        savedContent.current = updated.content;
        setVersions(await documentApi.versions(id, documentId));
        setSaveState("saved");
      } catch (err) {
        setError(err instanceof ApiError ? err.message : t("editor.saveFailed"));
        setSaveState("error");
      }
    },
    [id, documentId, t],
  );

  // Sauvegarde automatique après une pause de frappe.
  useEffect(() => {
    if (saveState !== "dirty") return;
    const timer = setTimeout(() => void save(content), AUTOSAVE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [content, saveState, save]);

  // Avertit avant de quitter avec des modifications non enregistrées.
  useEffect(() => {
    function handler(event: BeforeUnloadEvent) {
      if (savedContent.current !== content) event.preventDefault();
    }
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [content]);

  async function handleRefine(action: RefineAction) {
    setError(null);
    setNotice(null);
    setBusyAction(action);
    try {
      if (savedContent.current !== content) await save(content);
      // Le retravail suit le même chemin que la génération : une tâche, puis
      // son résultat.
      const job = await documentApi.refine(id, documentId, action);
      const result = await waitForJob(job);
      setDocument(result.document);
      setContent(result.document.content);
      savedContent.current = result.document.content;
      setCredits(result.credits_remaining);
      setVersions(await documentApi.versions(id, documentId));
      const label = REFINE_ACTIONS.find((item) => item.action === action)?.label;
      setNotice(
        t("editor.refineDone", {
          action: label ? t(label) : action,
          version: result.document.current_version,
        }),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("editor.actionFailed"));
    } finally {
      setBusyAction(null);
    }
  }

  async function handleRestore(versionNumber: number) {
    if (!window.confirm(t("editor.restoreConfirm", { number: versionNumber }))) {
      return;
    }
    try {
      const restored = await documentApi.restore(id, documentId, versionNumber);
      setDocument(restored);
      setContent(restored.content);
      savedContent.current = restored.content;
      setVersions(await documentApi.versions(id, documentId));
      setNotice(t("editor.restored", { number: versionNumber }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("editor.restoreFailed"));
    }
  }

  async function handleStatus(status: DocumentStatus) {
    await save(content, status);
  }

  if (error && !document) return <Alert tone="danger">{error}</Alert>;
  if (!document) {
    return (
      <div className="space-y-5">
        <div className="skeleton h-9 w-72 rounded" />
        <SkeletonCard lines={8} />
      </div>
    );
  }

  const dirty = savedContent.current !== content;

  return (
    <div className="space-y-5">
      <div>
        <Link
          href={`/projets/${id}/ai-writer`}
          className="text-sm text-slatey-400 hover:text-slatey-200"
        >
          {t("editor.back")}
        </Link>

        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl text-slatey-100">
              {t(`documentType.${document.document_type}`)}
            </h1>
            <p className="mt-1 text-xs text-slatey-400">
              {t("editor.meta", {
                version: document.current_version,
                words: document.word_count,
                pages: formatPages(document.word_count),
              })}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              className="field py-1.5 text-sm"
              value={document.status}
              onChange={(event) => void handleStatus(event.target.value as DocumentStatus)}
              aria-label={t("editor.statusLabel")}
            >
              {DOCUMENT_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {t(`documentStatus.${status}`)}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn-secondary"
              onClick={() =>
                downloadExport(
                  `/api/v1/projects/${id}/export/docx/${documentId}`,
                  `${document.title}.docx`,
                ).catch(() => setError(t("project.exportFailed")))
              }
            >
              {t("editor.exportWord")}
            </button>
          </div>
        </div>
      </div>

      {error ? <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert> : null}
      {notice ? <Alert tone="success" onDismiss={() => setNotice(null)}>{notice}</Alert> : null}

      {/* Barre d'outils */}
      <div className="card flex flex-wrap items-center gap-2 p-3">
        <div className="flex rounded-lg border border-ink-700 p-0.5">
          <button
            type="button"
            onClick={() => setMode("preview")}
            className={
              mode === "preview"
                ? "rounded-md bg-ink-700 px-3 py-1.5 text-xs text-slatey-100"
                : "px-3 py-1.5 text-xs text-slatey-400 hover:text-slatey-200"
            }
          >
            {t("editor.preview")}
          </button>
          <button
            type="button"
            onClick={() => setMode("edit")}
            className={
              mode === "edit"
                ? "rounded-md bg-ink-700 px-3 py-1.5 text-xs text-slatey-100"
                : "px-3 py-1.5 text-xs text-slatey-400 hover:text-slatey-200"
            }
          >
            {t("common.edit")}
          </button>
        </div>

        <span className="mx-1 h-5 w-px bg-ink-700" />

        {REFINE_ACTIONS.map((item) => (
          <button
            key={item.action}
            type="button"
            className="btn-secondary px-3 py-1.5 text-xs"
            onClick={() => handleRefine(item.action)}
            disabled={busyAction !== null}
          >
            {busyAction === item.action ? <Spinner className="h-3 w-3" /> : null}
            {t(item.label)}
          </button>
        ))}

        <span className="ml-auto text-xs text-slatey-400">
          {saveState === "saving"
            ? t("common.saving")
            : dirty
              ? t("editor.unsaved")
              : saveState === "error"
                ? t("editor.saveError")
                : t("editor.saved")}
        </span>

        {dirty ? (
          <button
            type="button"
            className="btn-primary px-3 py-1.5 text-xs"
            onClick={() => void save(content)}
          >
            {t("common.save")}
          </button>
        ) : null}
      </div>

      {/* Éditeur / aperçu */}
      <div className="card p-6 sm:p-8">
        {mode === "edit" ? (
          <textarea
            aria-label={t("editor.contentLabel")}
            className="field min-h-[60vh] w-full resize-y font-mono text-[13.5px] leading-relaxed"
            value={content}
            onChange={(event) => {
              setContent(event.target.value);
              setSaveState("dirty");
            }}
            spellCheck
          />
        ) : content.trim() ? (
          <Markdown content={content} />
        ) : (
          <p className="text-sm text-slatey-400">
            {t("editor.emptyDocument")}
          </p>
        )}
      </div>

      {/* Historique des versions */}
      <div className="card p-6">
        <SectionHeading
          title={t("editor.history")}
          description={t("editor.historyHint")}
        />

        <div className="space-y-1.5">
          {versions.map((version) => (
            <div
              key={version.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-ink-800 px-4 py-2.5"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-slatey-100">
                    {t("editor.version", { number: version.version_number })}
                  </span>
                  {version.version_number === document.current_version ? (
                    <Badge tone="brass">{t("editor.currentVersion")}</Badge>
                  ) : null}
                  <Badge tone="neutral">
                    {(ORIGINS as readonly string[]).includes(version.origin)
                      ? t(`origin.${version.origin as (typeof ORIGINS)[number]}`)
                      : version.origin}
                  </Badge>
                </div>
                <p className="mt-0.5 text-xs text-slatey-500">
                  {t("editor.versionMeta", {
                    date: formatDateTime(version.created_at),
                    words: version.word_count,
                  })}
                  {version.prompt_version ? ` · prompt v${version.prompt_version}` : ""}
                  {version.note ? ` · ${version.note}` : ""}
                </p>
              </div>

              {version.version_number !== document.current_version ? (
                <button
                  type="button"
                  className="btn-ghost px-3 py-1.5 text-xs"
                  onClick={() => handleRestore(version.version_number)}
                >
                  {t("editor.restore")}
                </button>
              ) : null}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
