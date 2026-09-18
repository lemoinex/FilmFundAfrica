"use client";

import { useCallback, useEffect, useState } from "react";

import { Alert, Badge, SectionHeading, SkeletonCard, Spinner } from "@/components/ui";
import { ApiError, candidateApi } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { CandidateStatus, OpportunityCandidate } from "@/lib/types";

const STATUS_LABELS: Record<CandidateStatus, string> = {
  PENDING: "À relire",
  APPROVED: "Publié",
  REJECTED: "Écarté",
};

/** Champs que la relecture peut corriger avant publication. */
const EDITABLE = [
  { key: "organization", label: "Organisme *" },
  { key: "country", label: "Pays" },
  { key: "deadline", label: "Date limite (AAAA-MM-JJ)" },
  { key: "application_url", label: "Lien de candidature" },
] as const;

export default function VeillePage() {
  const [candidates, setCandidates] = useState<OpportunityCandidate[]>([]);
  const [filter, setFilter] = useState<CandidateStatus>("PENDING");
  const [corrections, setCorrections] = useState<Record<string, Record<string, string>>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setCandidates(await candidateApi.list(filter));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chargement impossible.");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    void load();
  }, [load]);

  function correct(id: string, field: string, value: string) {
    setCorrections((current) => ({ ...current, [id]: { ...current[id], [field]: value } }));
  }

  async function act(candidate: OpportunityCandidate, approve: boolean) {
    setError(null);
    setNotice(null);
    setBusy(candidate.id);
    try {
      if (approve) {
        const edits = Object.fromEntries(
          Object.entries(corrections[candidate.id] ?? {}).filter(([, value]) => value.trim()),
        );
        const { detail } = await candidateApi.approve(candidate.id, edits);
        setNotice(detail);
      } else {
        await candidateApi.reject(candidate.id, corrections[candidate.id]?.note);
        setNotice("Candidat écarté.");
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action impossible.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-7">
      <div>
        <h1 className="font-display text-3xl text-slatey-100">Veille — file de validation</h1>
        <p className="mt-1.5 text-sm text-slatey-400">
          La veille automatisée dépose ici ce qu&apos;elle trouve. Rien n&apos;est proposé aux
          auteurs avant votre relecture : un dispositif inexact engage leur dossier de
          financement.
        </p>
      </div>

      {error ? <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert> : null}
      {notice ? <Alert tone="info" onDismiss={() => setNotice(null)}>{notice}</Alert> : null}

      <div className="flex flex-wrap gap-2">
        {(Object.keys(STATUS_LABELS) as CandidateStatus[]).map((status) => (
          <button
            key={status}
            type="button"
            className={filter === status ? "btn-primary px-3 py-1.5 text-xs" : "btn-secondary px-3 py-1.5 text-xs"}
            onClick={() => setFilter(status)}
          >
            {STATUS_LABELS[status]}
          </button>
        ))}
      </div>

      {loading ? (
        <SkeletonCard lines={4} />
      ) : candidates.length === 0 ? (
        <div className="card p-6">
          <p className="text-sm text-slatey-400">
            {filter === "PENDING"
              ? "Aucun candidat à relire. La veille n'a rien déposé depuis sa dernière exécution."
              : "Aucun candidat dans cet état."}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {candidates.map((candidate) => (
            <div key={candidate.id} className="card p-6">
              <SectionHeading
                title={candidate.name}
                description={`Source : ${candidate.source_name} · déposé le ${formatDate(candidate.created_at)}`}
                action={<Badge tone="neutral">{STATUS_LABELS[candidate.status]}</Badge>}
              />

              <a
                href={candidate.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-brass-300 hover:text-brass-200"
              >
                Ouvrir la source ↗
              </a>

              <div className="mt-4">
                <p className="mb-1.5 text-xs uppercase tracking-wide text-slatey-500">
                  Champs extraits
                </p>
                <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
                  {Object.entries(candidate.payload).map(([key, value]) => (
                    <div key={key} className="flex gap-2">
                      <dt className="text-slatey-500">{key}</dt>
                      <dd className="truncate text-slatey-200">{String(value)}</dd>
                    </div>
                  ))}
                </dl>
                {Object.keys(candidate.payload).length === 0 ? (
                  <p className="text-sm text-slatey-400">
                    Aucun champ extrait : tout est à saisir.
                  </p>
                ) : null}
              </div>

              {candidate.status === "PENDING" ? (
                <>
                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    {EDITABLE.map((field) => (
                      <div key={field.key}>
                        <label className="label" htmlFor={`${candidate.id}-${field.key}`}>
                          {field.label}
                        </label>
                        <input
                          id={`${candidate.id}-${field.key}`}
                          className="field"
                          placeholder={String(candidate.payload[field.key] ?? "")}
                          value={corrections[candidate.id]?.[field.key] ?? ""}
                          onChange={(event) =>
                            correct(candidate.id, field.key, event.target.value)
                          }
                        />
                      </div>
                    ))}
                  </div>
                  <p className="hint">
                    Ce que vous saisissez l&apos;emporte sur l&apos;extraction : c&apos;est vous
                    qui avez lu la source. Laissez vide un champ absent de la source plutôt que
                    de le deviner.
                  </p>

                  <div className="mt-5 flex flex-wrap gap-3 border-t border-ink-700 pt-5">
                    <button
                      type="button"
                      className="btn-primary"
                      disabled={busy === candidate.id}
                      onClick={() => act(candidate, true)}
                    >
                      {busy === candidate.id ? <Spinner /> : null}
                      Publier le dispositif
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      disabled={busy === candidate.id}
                      onClick={() => act(candidate, false)}
                    >
                      Écarter
                    </button>
                    <input
                      className="field max-w-xs"
                      placeholder="Motif (si écarté)"
                      aria-label={`Motif — ${candidate.name}`}
                      value={corrections[candidate.id]?.note ?? ""}
                      onChange={(event) => correct(candidate.id, "note", event.target.value)}
                    />
                  </div>
                </>
              ) : candidate.review_note ? (
                <p className="mt-4 text-sm text-slatey-400">Motif : {candidate.review_note}</p>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
