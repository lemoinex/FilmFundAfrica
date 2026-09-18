"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { Markdown } from "@/components/markdown";
import { Alert, Badge, SectionHeading, SkeletonCard, Spinner } from "@/components/ui";
import { ApiError, documentApi, downloadExport } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { estimatePages, formatDateTime } from "@/lib/format";
import { DOCUMENT_STATUS_LABELS, DOCUMENT_TYPE_LABELS, ORIGIN_LABELS } from "@/lib/labels";
import type { DocumentStatus, DocumentVersion, ProjectDocument, RefineAction } from "@/lib/types";

const AUTOSAVE_DELAY_MS = 2500;

const REFINE_ACTIONS: { action: RefineAction; label: string }[] = [
  { action: "IMPROVE", label: "Améliorer" },
  { action: "SHORTEN", label: "Raccourcir" },
  { action: "EXPAND", label: "Développer" },
  { action: "CORRECT", label: "Corriger" },
];

type SaveState = "idle" | "dirty" | "saving" | "saved" | "error";

export default function DocumentEditorPage() {
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
      setError(err instanceof ApiError ? err.message : "Chargement impossible.");
    }
  }, [id, documentId]);

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
        setError(err instanceof ApiError ? err.message : "Sauvegarde impossible.");
        setSaveState("error");
      }
    },
    [id, documentId],
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
      const result = await documentApi.refine(id, documentId, action);
      setDocument(result.document);
      setContent(result.document.content);
      savedContent.current = result.document.content;
      setCredits(result.credits_remaining);
      setVersions(await documentApi.versions(id, documentId));
      setNotice(
        `${REFINE_ACTIONS.find((item) => item.action === action)?.label} — version ${result.document.current_version} créée.`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action impossible.");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleRestore(versionNumber: number) {
    if (!window.confirm(`Restaurer la version ${versionNumber} ? Le texte actuel est conservé comme version précédente.`)) {
      return;
    }
    try {
      const restored = await documentApi.restore(id, documentId, versionNumber);
      setDocument(restored);
      setContent(restored.content);
      savedContent.current = restored.content;
      setVersions(await documentApi.versions(id, documentId));
      setNotice(`Version ${versionNumber} restaurée.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Restauration impossible.");
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
          ← AI Writer
        </Link>

        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl text-slatey-100">
              {DOCUMENT_TYPE_LABELS[document.document_type]}
            </h1>
            <p className="mt-1 text-xs text-slatey-400">
              Version {document.current_version} · {document.word_count} mots ·{" "}
              {estimatePages(document.word_count)}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              className="field py-1.5 text-sm"
              value={document.status}
              onChange={(event) => void handleStatus(event.target.value as DocumentStatus)}
              aria-label="Statut du document"
            >
              {(Object.keys(DOCUMENT_STATUS_LABELS) as DocumentStatus[]).map((status) => (
                <option key={status} value={status}>{DOCUMENT_STATUS_LABELS[status]}</option>
              ))}
            </select>
            <button
              type="button"
              className="btn-secondary"
              onClick={() =>
                downloadExport(
                  `/api/v1/projects/${id}/export/docx/${documentId}`,
                  `${document.title}.docx`,
                ).catch(() => setError("Export impossible."))
              }
            >
              Exporter en Word
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
            Aperçu
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
            Éditer
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
            {item.label}
          </button>
        ))}

        <span className="ml-auto text-xs text-slatey-400">
          {saveState === "saving"
            ? "Enregistrement…"
            : dirty
              ? "Modifications non enregistrées"
              : saveState === "error"
                ? "Échec de l'enregistrement"
                : "Enregistré"}
        </span>

        {dirty ? (
          <button
            type="button"
            className="btn-primary px-3 py-1.5 text-xs"
            onClick={() => void save(content)}
          >
            Enregistrer
          </button>
        ) : null}
      </div>

      {/* Éditeur / aperçu */}
      <div className="card p-6 sm:p-8">
        {mode === "edit" ? (
          <textarea
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
            Ce document est vide. Passez en mode Édition ou régénérez-le depuis l&apos;AI Writer.
          </p>
        )}
      </div>

      {/* Historique des versions */}
      <div className="card p-6">
        <SectionHeading
          title="Historique des versions"
          description="Chaque génération, chaque sauvegarde manuelle et chaque restauration crée une version."
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
                    Version {version.version_number}
                  </span>
                  {version.version_number === document.current_version ? (
                    <Badge tone="brass">actuelle</Badge>
                  ) : null}
                  <Badge tone="neutral">
                    {ORIGIN_LABELS[version.origin] ?? version.origin}
                  </Badge>
                </div>
                <p className="mt-0.5 text-xs text-slatey-500">
                  {formatDateTime(version.created_at)} · {version.word_count} mots
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
                  Restaurer
                </button>
              ) : null}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
