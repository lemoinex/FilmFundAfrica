"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Alert, Badge, SectionHeading, SkeletonCard, Spinner } from "@/components/ui";
import { ApiError, documentApi, projectApi, waitForJob } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatRelative } from "@/lib/format";
import { DOCUMENT_TYPE_LABELS, DURATION_PRESETS } from "@/lib/labels";
import type {
  DocumentSummary,
  DocumentType,
  DocumentTypeInfo,
  GenerationJob,
  GenerationResult,
  Project,
  ScreenplayCapacity,
} from "@/lib/types";

/** Ordre de travail conseillé : chaque document nourrit les suivants. */
const RECOMMENDED_ORDER: DocumentType[] = [
  "LOGLINE",
  "SHORT_SYNOPSIS",
  "LONG_SYNOPSIS",
  "CHARACTER_SHEET",
  "INTENT_NOTE",
  "DIRECTING_NOTE",
  "TREATMENT",
  "SCREENPLAY",
  "SERIES_BIBLE",
  "WRITTEN_PITCH",
  "ORAL_PITCH",
];

export default function AiWriterPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { setCredits, user } = useAuth();

  const [project, setProject] = useState<Project | null>(null);
  const [types, setTypes] = useState<DocumentTypeInfo[]>([]);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [capacity, setCapacity] = useState<ScreenplayCapacity | null>(null);
  const [selected, setSelected] = useState<DocumentType>("SHORT_SYNOPSIS");
  const [duration, setDuration] = useState<string>("");
  const [instructions, setInstructions] = useState("");
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState<GenerationJob | null>(null);
  const [result, setResult] = useState<GenerationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [projectData, typesData, documentsData, capacityData] = await Promise.all([
        projectApi.get(id),
        documentApi.types(),
        documentApi.list(id),
        documentApi.screenplayCapacity(),
      ]);
      setProject(projectData);
      setTypes(typesData);
      setDocuments(documentsData);
      setCapacity(capacityData);
      setDuration(projectData.duration ? String(projectData.duration) : "90");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chargement impossible.");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  const byType = useMemo(
    () => new Map(documents.map((document) => [document.document_type, document])),
    [documents],
  );
  const typeInfo = useMemo(
    () => types.find((type) => type.document_type === selected),
    [types, selected],
  );

  const ordered = useMemo(() => {
    const known = new Set(RECOMMENDED_ORDER);
    return [
      ...RECOMMENDED_ORDER.filter((type) => types.some((t) => t.document_type === type)),
      ...types.map((t) => t.document_type).filter((type) => !known.has(type)),
    ];
  }, [types]);

  const missingDependencies = useMemo(() => {
    if (!typeInfo) return [];
    return typeInfo.depends_on.filter((dependency) => !byType.has(dependency));
  }, [typeInfo, byType]);

  const isScreenplay = selected === "SCREENPLAY";
  // Le découpage est calculé par le serveur et exposé par l'API : le frontend
  // ne duplique aucune règle, il annonce simplement le coût avant génération.
  const estimatedPasses = useMemo(() => {
    if (!isScreenplay || !capacity) return 1;
    const minutes = Number(duration) || 90;
    return Math.max(1, Math.ceil(minutes / capacity.pages_per_pass));
  }, [isScreenplay, duration, capacity]);

  const availableDurations = useMemo(
    () => DURATION_PRESETS.filter((preset) => !capacity || preset <= capacity.max_minutes),
    [capacity],
  );

  async function handleGenerate() {
    setError(null);
    setResult(null);
    setProgress(null);
    setGenerating(true);
    try {
      // La génération est une tâche : l'API l'accepte, le serveur l'exécute,
      // et l'on suit son avancement au lieu de tenir une requête ouverte.
      const job = await documentApi.generate(id, selected, {
        target_duration_minutes: isScreenplay && duration ? Number(duration) : null,
        additional_instructions: instructions.trim() || null,
        overwrite: true,
      });
      const generated = await waitForJob(job, { onProgress: setProgress });
      setResult(generated);
      setCredits(generated.credits_remaining);
      setDocuments(await documentApi.list(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Génération impossible.");
    } finally {
      setGenerating(false);
      setProgress(null);
    }
  }

  if (error && !project) return <Alert tone="danger">{error}</Alert>;
  if (!project) {
    return (
      <div className="space-y-5">
        <div className="skeleton h-9 w-64 rounded" />
        <SkeletonCard lines={5} />
      </div>
    );
  }

  return (
    <div className="space-y-7">
      <div>
        <Link href={`/projets/${id}`} className="text-sm text-slatey-400 hover:text-slatey-200">
          ← {project.title}
        </Link>
        <h1 className="mt-3 font-display text-3xl text-slatey-100">AI Writer</h1>
        <p className="mt-1.5 text-sm text-slatey-400">
          Chaque document est écrit à partir du contexte du projet et des documents déjà
          rédigés, pour rester cohérent avec eux.
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-[280px_1fr]">
        {/* Colonne gauche : catalogue */}
        <aside className="space-y-1.5">
          {ordered.map((type) => {
            const existing = byType.get(type);
            const active = selected === type;
            return (
              <button
                key={type}
                type="button"
                onClick={() => setSelected(type)}
                className={
                  active
                    ? "w-full rounded-lg border border-brass-500/50 bg-brass-500/10 px-4 py-3 text-left"
                    : "w-full rounded-lg border border-ink-700 bg-ink-900 px-4 py-3 text-left transition-colors hover:border-ink-600"
                }
              >
                <span
                  className={
                    active
                      ? "block text-sm font-medium text-brass-100"
                      : "block text-sm text-slatey-200"
                  }
                >
                  {DOCUMENT_TYPE_LABELS[type]}
                </span>
                <span className="mt-0.5 block text-xs text-slatey-500">
                  {existing
                    ? `v${existing.current_version} · ${existing.word_count} mots`
                    : "Non généré"}
                </span>
              </button>
            );
          })}
        </aside>

        {/* Colonne droite : génération */}
        <div className="space-y-5">
          <div className="card p-6">
            <SectionHeading
              title={DOCUMENT_TYPE_LABELS[selected]}
              description={
                typeInfo?.target_pages
                  ? `Longueur cible : ${typeInfo.target_pages[0]} à ${typeInfo.target_pages[1]} page(s).`
                  : isScreenplay
                    ? "Longueur pilotée par la durée cible : 1 page ≈ 1 minute."
                    : undefined
              }
              action={
                typeInfo ? (
                  <Badge tone="neutral">prompt v{typeInfo.prompt_version}</Badge>
                ) : null
              }
            />

            {typeInfo ? (
              <div className="mb-5">
                <p className="mb-2 text-xs uppercase tracking-wide text-slatey-400">
                  Structure imposée
                </p>
                <ol className="grid gap-1 text-sm text-slatey-300 sm:grid-cols-2">
                  {typeInfo.outline.map((section, index) => (
                    <li key={section} className="flex gap-2">
                      <span className="text-brass-400">{index + 1}.</span>
                      {section}
                    </li>
                  ))}
                </ol>
              </div>
            ) : null}

            {missingDependencies.length > 0 ? (
              <Alert tone="warning" title="Documents recommandés avant celui-ci">
                {missingDependencies.map((d) => DOCUMENT_TYPE_LABELS[d]).join(", ")}. Vous pouvez
                générer quand même : les sections dépendantes indiqueront « Information non
                fournie. »
              </Alert>
            ) : null}

            {isScreenplay ? (
              <div className="mt-5">
                <label className="label" htmlFor="duration">Durée cible du scénario</label>
                <div className="flex flex-wrap gap-2">
                  {availableDurations.map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      onClick={() => setDuration(String(preset))}
                      className={
                        duration === String(preset)
                          ? "btn-primary px-3 py-1.5 text-xs"
                          : "btn-secondary px-3 py-1.5 text-xs"
                      }
                    >
                      {preset} min
                    </button>
                  ))}
                </div>
                <p className="hint">
                  Soit ~{duration || 90} pages. Un scénario long est écrit en{" "}
                  {estimatedPasses} passe{estimatedPasses > 1 ? "s" : ""} successive
                  {estimatedPasses > 1 ? "s" : ""}, chacune reprenant la continuité de la
                  précédente — et coûtant 1 crédit.
                  {capacity
                    ? ` Durée maximale avec la configuration actuelle du serveur : ${capacity.max_minutes} minutes.`
                    : ""}
                </p>
              </div>
            ) : null}

            <div className="mt-5">
              <label className="label" htmlFor="instructions">
                Consignes complémentaires (facultatif)
              </label>
              <textarea
                id="instructions"
                className="field"
                rows={3}
                placeholder="Ton, angle à privilégier, contrainte d'un fonds précis…"
                value={instructions}
                onChange={(event) => setInstructions(event.target.value)}
              />
            </div>

            {error ? (
              <div className="mt-5">
                <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert>
              </div>
            ) : null}

            <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-ink-700 pt-5">
              <button
                type="button"
                className="btn-primary"
                onClick={handleGenerate}
                disabled={generating}
              >
                {generating ? <Spinner /> : null}
                {byType.has(selected) ? "Régénérer" : "Générer"}
              </button>

              {byType.has(selected) ? (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() =>
                    router.push(`/projets/${id}/documents/${byType.get(selected)!.id}`)
                  }
                >
                  Ouvrir dans l&apos;éditeur
                </button>
              ) : null}

              <span className="ml-auto text-xs text-slatey-400">
                Coût : {isScreenplay ? estimatedPasses : 1} crédit
                {(isScreenplay ? estimatedPasses : 1) > 1 ? "s" : ""} · solde{" "}
                {user?.ai_credits_remaining ?? "—"}
              </span>
            </div>

            {generating ? (
              <div className="mt-4 space-y-2">
                <p className="text-xs text-slatey-400">
                  {progress?.status === "QUEUED"
                    ? "En file d'attente…"
                    : progress && progress.total_passes > 1
                      ? `Rédaction en cours — passe ${Math.min(progress.completed_passes + 1, progress.total_passes)} sur ${progress.total_passes}.`
                      : "Rédaction en cours…"}{" "}
                  {isScreenplay && estimatedPasses > 1
                    ? "Vous pouvez quitter cette page : la génération continue côté serveur."
                    : "Cela prend généralement moins d'une minute."}
                </p>
                {progress && progress.total_passes > 1 ? (
                  <div
                    className="h-1.5 overflow-hidden rounded-full bg-ink-700"
                    role="progressbar"
                    aria-valuemin={0}
                    aria-valuemax={progress.total_passes}
                    aria-valuenow={progress.completed_passes}
                  >
                    <div
                      className="h-full bg-brass-500 transition-all duration-500"
                      style={{
                        width: `${Math.round((progress.completed_passes / progress.total_passes) * 100)}%`,
                      }}
                    />
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>

          {result ? (
            <div className="card p-6">
              <SectionHeading
                title="Document généré"
                description={`${result.document.word_count} mots · version ${result.document.current_version} · ${result.passes} passe(s) · ${Math.round(result.latency_ms / 1000)} s`}
                action={
                  <Link
                    href={`/projets/${id}/documents/${result.document.id}`}
                    className="btn-primary"
                  >
                    Éditer
                  </Link>
                }
              />

              {result.provider === "mock" ? (
                <Alert tone="warning" title="Aucun fournisseur d'IA configuré">
                  Le serveur tourne avec <code>AI_PROVIDER=mock</code> : le document reprend vos
                  saisies et la structure attendue, sans rédaction. Renseignez{" "}
                  <code>AI_PROVIDER</code> et <code>AI_API_KEY</code> pour une génération réelle.
                </Alert>
              ) : null}

              {result.missing_information.length > 0 ? (
                <div className="mt-4">
                  <Alert tone="info" title="Informations à compléter">
                    <ul className="mt-1 list-disc space-y-1 pl-4">
                      {result.missing_information.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </Alert>
                </div>
              ) : null}

              <p className="mt-4 text-xs text-slatey-500">
                Généré avec {result.provider} · {result.model} · prompt v{result.prompt_version}
              </p>
            </div>
          ) : null}

          {documents.length > 0 ? (
            <div className="card p-6">
              <SectionHeading title="Documents du projet" />
              <div className="space-y-1.5">
                {documents.map((document) => (
                  <Link
                    key={document.id}
                    href={`/projets/${id}/documents/${document.id}`}
                    className="flex items-center justify-between gap-4 rounded-lg px-3 py-2.5 text-sm transition-colors hover:bg-ink-800"
                  >
                    <span className="text-slatey-200">
                      {DOCUMENT_TYPE_LABELS[document.document_type]}
                    </span>
                    <span className="text-xs text-slatey-500">
                      v{document.current_version} · {formatRelative(document.updated_at)}
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
