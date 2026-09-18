"use client";

import { useCallback, useEffect, useState } from "react";

import { Alert, Badge, SectionHeading, SkeletonCard, Spinner } from "@/components/ui";
import { ApiError, candidateApi } from "@/lib/api";
import { useI18n, type MessageKey } from "@/lib/i18n";
import type { CandidateStatus, OpportunityCandidate } from "@/lib/types";

const STATUSES: CandidateStatus[] = ["PENDING", "APPROVED", "REJECTED"];

/** Champs que la relecture peut corriger avant publication. */
const EDITABLE: { key: string; label: MessageKey }[] = [
  { key: "organization", label: "watch.field.organization" },
  { key: "country", label: "watch.field.country" },
  { key: "deadline", label: "watch.field.deadline" },
  { key: "application_url", label: "watch.field.application_url" },
];

export default function VeillePage() {
  const { t, formatDate } = useI18n();
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
      setError(err instanceof ApiError ? err.message : t("load.failed"));
    } finally {
      setLoading(false);
    }
  }, [filter, t]);

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
        setNotice(t("watch.rejected"));
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("watch.actionFailed"));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-7">
      <div>
        <h1 className="font-display text-3xl text-slatey-100">{t("watch.title")}</h1>
        <p className="mt-1.5 text-sm text-slatey-400">{t("watch.subtitle")}</p>
      </div>

      {error ? <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert> : null}
      {notice ? <Alert tone="info" onDismiss={() => setNotice(null)}>{notice}</Alert> : null}

      <div className="flex flex-wrap gap-2">
        {STATUSES.map((status) => (
          <button
            key={status}
            type="button"
            className={filter === status ? "btn-primary px-3 py-1.5 text-xs" : "btn-secondary px-3 py-1.5 text-xs"}
            onClick={() => setFilter(status)}
          >
            {t(`candidateStatus.${status}`)}
          </button>
        ))}
      </div>

      {loading ? (
        <SkeletonCard lines={4} />
      ) : candidates.length === 0 ? (
        <div className="card p-6">
          <p className="text-sm text-slatey-400">
            {t(filter === "PENDING" ? "watch.emptyPending" : "watch.emptyOther")}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {candidates.map((candidate) => (
            <div key={candidate.id} className="card p-6">
              <SectionHeading
                title={candidate.name}
                description={t("watch.candidateMeta", {
                  source: candidate.source_name,
                  date: formatDate(candidate.created_at),
                })}
                action={
                  <Badge tone="neutral">{t(`candidateStatus.${candidate.status}`)}</Badge>
                }
              />

              <a
                href={candidate.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-brass-300 hover:text-brass-200"
              >
                {t("watch.openSource")}
              </a>

              <div className="mt-4">
                <p className="mb-1.5 text-xs uppercase tracking-wide text-slatey-500">
                  {t("watch.extractedFields")}
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
                  <p className="text-sm text-slatey-400">{t("watch.noField")}</p>
                ) : null}
              </div>

              {candidate.status === "PENDING" ? (
                <>
                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    {EDITABLE.map((field) => (
                      <div key={field.key}>
                        <label className="label" htmlFor={`${candidate.id}-${field.key}`}>
                          {t(field.label)}
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
                  <p className="hint">{t("watch.editHint")}</p>

                  <div className="mt-5 flex flex-wrap gap-3 border-t border-ink-700 pt-5">
                    <button
                      type="button"
                      className="btn-primary"
                      disabled={busy === candidate.id}
                      onClick={() => act(candidate, true)}
                    >
                      {busy === candidate.id ? <Spinner /> : null}
                      {t("watch.publish")}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      disabled={busy === candidate.id}
                      onClick={() => act(candidate, false)}
                    >
                      {t("watch.reject")}
                    </button>
                    <input
                      className="field max-w-xs"
                      placeholder={t("watch.reasonPlaceholder")}
                      aria-label={t("watch.reasonLabel", { name: candidate.name })}
                      value={corrections[candidate.id]?.note ?? ""}
                      onChange={(event) => correct(candidate.id, "note", event.target.value)}
                    />
                  </div>
                </>
              ) : candidate.review_note ? (
                <p className="mt-4 text-sm text-slatey-400">
                  {t("watch.reason", { note: candidate.review_note })}
                </p>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
