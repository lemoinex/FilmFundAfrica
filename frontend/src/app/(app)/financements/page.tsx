"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { OpportunityCard } from "@/components/funding";
import { Alert, EmptyState, SectionHeading, SkeletonCard } from "@/components/ui";
import { ApiError, fundingApi, type FundingSearchParams } from "@/lib/api";
import { FUNDING_CATEGORY_LABELS, PROJECT_TYPE_LABELS } from "@/lib/labels";
import type { FundingCategory, OpportunityPage, ProjectType } from "@/lib/types";

const SORT_OPTIONS = [
  { value: "deadline", label: "Échéance la plus proche" },
  { value: "recent", label: "Ajout le plus récent" },
  { value: "amount", label: "Montant le plus élevé" },
  { value: "name", label: "Ordre alphabétique" },
];

const EMPTY_FILTERS: FundingSearchParams = {
  query: "",
  country: "",
  project_type: "",
  genre: "",
  language: "",
  category: "",
  min_amount: undefined,
  include_closed: false,
  sort: "deadline",
  page: 1,
};

export default function FundingSearchPage() {
  const [filters, setFilters] = useState<FundingSearchParams>(EMPTY_FILTERS);
  const [data, setData] = useState<OpportunityPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (params: FundingSearchParams) => {
    setLoading(true);
    try {
      setData(await fundingApi.search(params));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Recherche impossible.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => void load(filters), filters.query ? 300 : 0);
    return () => clearTimeout(timer);
  }, [filters, load]);

  function update(patch: Partial<FundingSearchParams>) {
    setFilters((current) => ({ ...current, ...patch, page: patch.page ?? 1 }));
  }

  const facets = data?.facets ?? {};
  const activeFilterCount = useMemo(
    () =>
      [
        filters.country,
        filters.project_type,
        filters.genre,
        filters.language,
        filters.category,
        filters.min_amount,
        filters.include_closed || undefined,
      ].filter(Boolean).length,
    [filters],
  );

  const pageCount = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Funding Intelligence"
        title="Financements"
        description="Fonds, bourses, résidences, laboratoires, festivals et forums de coproduction."
      />

      {/* Recherche et filtres */}
      <div className="card space-y-4 p-5">
        <input
          type="search"
          className="field"
          placeholder="Rechercher un fonds, un organisme, un mot-clé…"
          value={filters.query ?? ""}
          onChange={(event) => update({ query: event.target.value })}
        />

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="label text-xs" htmlFor="country">Pays</label>
            <select
              id="country"
              className="field py-1.5 text-sm"
              value={filters.country ?? ""}
              onChange={(event) => update({ country: event.target.value })}
            >
              <option value="">Tous les pays</option>
              {(facets.countries ?? []).map((country) => (
                <option key={country} value={country}>{country}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="label text-xs" htmlFor="project_type">Type de projet</label>
            <select
              id="project_type"
              className="field py-1.5 text-sm"
              value={filters.project_type ?? ""}
              onChange={(event) => update({ project_type: event.target.value })}
            >
              <option value="">Tous les types</option>
              {(Object.keys(PROJECT_TYPE_LABELS) as ProjectType[]).map((type) => (
                <option key={type} value={type}>{PROJECT_TYPE_LABELS[type]}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="label text-xs" htmlFor="category">Type de financement</label>
            <select
              id="category"
              className="field py-1.5 text-sm"
              value={filters.category ?? ""}
              onChange={(event) => update({ category: event.target.value })}
            >
              <option value="">Tous les dispositifs</option>
              {(Object.keys(FUNDING_CATEGORY_LABELS) as FundingCategory[]).map((category) => (
                <option key={category} value={category}>
                  {FUNDING_CATEGORY_LABELS[category]}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label text-xs" htmlFor="genre">Genre</label>
            <select
              id="genre"
              className="field py-1.5 text-sm"
              value={filters.genre ?? ""}
              onChange={(event) => update({ genre: event.target.value })}
            >
              <option value="">Tous les genres</option>
              {(facets.genres ?? []).map((genre) => (
                <option key={genre} value={genre}>{genre}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="label text-xs" htmlFor="language">Langue</label>
            <select
              id="language"
              className="field py-1.5 text-sm"
              value={filters.language ?? ""}
              onChange={(event) => update({ language: event.target.value })}
            >
              <option value="">Toutes les langues</option>
              {(facets.languages ?? []).map((language) => (
                <option key={language} value={language}>{language}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="label text-xs" htmlFor="min_amount">Montant minimum</label>
            <input
              id="min_amount"
              type="number"
              min={0}
              step={1000}
              className="field py-1.5 text-sm"
              placeholder="Aucun minimum"
              value={filters.min_amount ?? ""}
              onChange={(event) =>
                update({ min_amount: event.target.value ? Number(event.target.value) : undefined })
              }
            />
          </div>

          <div>
            <label className="label text-xs" htmlFor="sort">Trier par</label>
            <select
              id="sort"
              className="field py-1.5 text-sm"
              value={filters.sort}
              onChange={(event) => update({ sort: event.target.value })}
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>

          <div className="flex items-end pb-1">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-slatey-300">
              <input
                type="checkbox"
                className="h-4 w-4 accent-brass-400"
                checked={filters.include_closed ?? false}
                onChange={(event) => update({ include_closed: event.target.checked })}
              />
              Inclure les dispositifs clos
            </label>
          </div>
        </div>

        {activeFilterCount > 0 ? (
          <div className="flex items-center justify-between border-t border-ink-800 pt-3">
            <span className="text-xs text-slatey-400">
              {activeFilterCount} filtre{activeFilterCount > 1 ? "s" : ""} actif
              {activeFilterCount > 1 ? "s" : ""}
            </span>
            <button
              type="button"
              className="btn-ghost px-3 py-1 text-xs"
              onClick={() => setFilters(EMPTY_FILTERS)}
            >
              Réinitialiser
            </button>
          </div>
        ) : null}
      </div>

      {error ? <Alert tone="danger">{error}</Alert> : null}

      {/* Résultats */}
      {loading && !data ? (
        <div className="space-y-3">
          <SkeletonCard lines={3} />
          <SkeletonCard lines={3} />
        </div>
      ) : !data || data.total === 0 ? (
        <EmptyState
          title="Aucun dispositif ne correspond"
          description={
            activeFilterCount > 0 || filters.query
              ? "Élargissez vos critères, ou incluez les dispositifs clos pour consulter les éditions passées."
              : "La base des financements est encore vide. Un administrateur peut y ajouter des dispositifs depuis l'espace d'administration."
          }
        />
      ) : (
        <>
          <p className="text-sm text-slatey-400">
            {data.total} dispositif{data.total > 1 ? "s" : ""} trouvé
            {data.total > 1 ? "s" : ""}
          </p>

          <div className="space-y-3">
            {data.items.map((opportunity) => (
              <OpportunityCard
                key={opportunity.id}
                opportunity={opportunity}
                href={`/financements/${opportunity.id}`}
              />
            ))}
          </div>

          {pageCount > 1 ? (
            <div className="flex items-center justify-between border-t border-ink-800 pt-4">
              <button
                type="button"
                className="btn-secondary"
                disabled={(filters.page ?? 1) <= 1}
                onClick={() => update({ page: (filters.page ?? 1) - 1 })}
              >
                Précédent
              </button>
              <span className="text-sm text-slatey-400">
                Page {filters.page ?? 1} sur {pageCount}
              </span>
              <button
                type="button"
                className="btn-secondary"
                disabled={(filters.page ?? 1) >= pageCount}
                onClick={() => update({ page: (filters.page ?? 1) + 1 })}
              >
                Suivant
              </button>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
