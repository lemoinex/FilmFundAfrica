"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { DeadlineBadge, StatusBadge } from "@/components/funding";
import { Alert, Badge, EmptyState, SectionHeading, SkeletonCard, Spinner } from "@/components/ui";
import { ApiError, adminFundingApi } from "@/lib/api";
import { formatDate } from "@/lib/format";
import {
  DOCUMENT_TYPE_LABELS,
  FUNDING_CATEGORY_LABELS,
  PROJECT_TYPE_LABELS,
} from "@/lib/labels";
import type {
  DocumentType,
  FundingCategory,
  Opportunity,
  OpportunityPage,
  ProjectType,
} from "@/lib/types";

interface RequirementDraft {
  label: string;
  is_mandatory: boolean;
  required_document_type: string;
}

const EMPTY_FORM = {
  name: "",
  organization: "",
  description: "",
  website: "",
  country: "",
  eligible_countries: "",
  project_types: [] as ProjectType[],
  genres: "",
  languages: "Français",
  category: "FUND" as FundingCategory,
  minimum_budget: "",
  maximum_budget: "",
  currency: "EUR",
  deadline: "",
  opening_date: "",
  application_url: "",
  requirements: "",
  source_name: "",
  source_url: "",
  status: "UNVERIFIED",
};

function splitList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function AdminFundingPage() {
  const [data, setData] = useState<OpportunityPage | null>(null);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Opportunity | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async (query: string) => {
    try {
      setData(await adminFundingApi.list(query || undefined));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chargement impossible.");
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => void load(search), search ? 300 : 0);
    return () => clearTimeout(timer);
  }, [search, load]);

  async function handleVerify(id: string) {
    try {
      await adminFundingApi.verify(id, "OPEN");
      setNotice("Dispositif vérifié et publié.");
      await load(search);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Vérification impossible.");
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!window.confirm(`Supprimer définitivement « ${name} » ?`)) return;
    try {
      await adminFundingApi.remove(id);
      setNotice("Dispositif supprimé.");
      await load(search);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Suppression impossible.");
    }
  }

  async function openEditor(id: string) {
    try {
      setEditing(await adminFundingApi.get(id));
      setShowForm(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chargement impossible.");
    }
  }

  return (
    <div className="space-y-5">
      <SectionHeading
        title="Base des financements"
        description="Chaque dispositif exige une source consultable : sans elle, il ne peut pas être publié comme ouvert."
        action={
          <button
            type="button"
            className="btn-primary"
            onClick={() => {
              setEditing(null);
              setShowForm(true);
            }}
          >
            Ajouter un dispositif
          </button>
        }
      />

      {error ? <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert> : null}
      {notice ? <Alert tone="success" onDismiss={() => setNotice(null)}>{notice}</Alert> : null}

      {showForm ? (
        <OpportunityForm
          opportunity={editing}
          onCancel={() => {
            setShowForm(false);
            setEditing(null);
          }}
          onSaved={async (message) => {
            setShowForm(false);
            setEditing(null);
            setNotice(message);
            await load(search);
          }}
        />
      ) : null}

      <input
        type="search"
        className="field"
        placeholder="Rechercher un dispositif…"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />

      {!data ? (
        <SkeletonCard lines={4} />
      ) : data.total === 0 ? (
        <EmptyState
          title="Aucun dispositif"
          description="La base est vide. Ajoutez un premier dispositif : il apparaîtra ensuite dans la recherche et dans les analyses de compatibilité des projets."
        />
      ) : (
        <div className="space-y-2.5">
          {data.items.map((opportunity) => (
            <div key={opportunity.id} className="card p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-medium text-slatey-100">{opportunity.name}</p>
                  <p className="mt-0.5 text-xs text-slatey-400">{opportunity.organization}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="brass">{FUNDING_CATEGORY_LABELS[opportunity.category]}</Badge>
                  <DeadlineBadge opportunity={opportunity} />
                  <StatusBadge opportunity={opportunity} />
                </div>
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-ink-800 pt-3">
                <button
                  type="button"
                  className="btn-secondary px-3 py-1.5 text-xs"
                  onClick={() => openEditor(opportunity.id)}
                >
                  Modifier
                </button>
                {opportunity.status !== "OPEN" ? (
                  <button
                    type="button"
                    className="btn-secondary px-3 py-1.5 text-xs"
                    onClick={() => handleVerify(opportunity.id)}
                  >
                    Vérifier et publier
                  </button>
                ) : null}
                <button
                  type="button"
                  className="btn-danger px-3 py-1.5 text-xs"
                  onClick={() => handleDelete(opportunity.id, opportunity.name)}
                >
                  Supprimer
                </button>
                <span className="ml-auto text-xs text-slatey-500">
                  {opportunity.last_verified_at
                    ? `Vérifié le ${formatDate(opportunity.last_verified_at)}`
                    : "Jamais vérifié"}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Formulaire                                                          */
/* ------------------------------------------------------------------ */
function OpportunityForm({
  opportunity,
  onCancel,
  onSaved,
}: {
  opportunity: Opportunity | null;
  onCancel: () => void;
  onSaved: (message: string) => void | Promise<void>;
}) {
  const [form, setForm] = useState(() =>
    opportunity
      ? {
          name: opportunity.name,
          organization: opportunity.organization,
          description: opportunity.description,
          website: opportunity.website ?? "",
          country: opportunity.country ?? "",
          eligible_countries: opportunity.eligible_countries.join(", "),
          project_types: opportunity.project_types as ProjectType[],
          genres: opportunity.genres.join(", "),
          languages: opportunity.languages.join(", "),
          category: opportunity.category,
          minimum_budget: opportunity.minimum_budget?.toString() ?? "",
          maximum_budget: opportunity.maximum_budget?.toString() ?? "",
          currency: opportunity.currency,
          deadline: opportunity.deadline ?? "",
          opening_date: opportunity.opening_date ?? "",
          application_url: opportunity.application_url ?? "",
          requirements: opportunity.requirements,
          source_name: opportunity.source_name ?? "",
          source_url: opportunity.source_url ?? "",
          status: opportunity.status,
        }
      : { ...EMPTY_FORM },
  );
  const [requirements, setRequirements] = useState<RequirementDraft[]>(
    opportunity
      ? opportunity.requirement_items.map((item) => ({
          label: item.label,
          is_mandatory: item.is_mandatory,
          required_document_type: item.required_document_type ?? "",
        }))
      : [],
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function update(field: keyof typeof form, value: unknown) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function toggleProjectType(type: ProjectType) {
    setForm((current) => ({
      ...current,
      project_types: current.project_types.includes(type)
        ? current.project_types.filter((item) => item !== type)
        : [...current.project_types, type],
    }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSaving(true);

    const payload: Record<string, unknown> = {
      name: form.name.trim(),
      organization: form.organization.trim(),
      description: form.description,
      website: form.website || null,
      country: form.country || null,
      eligible_countries: splitList(form.eligible_countries),
      project_types: form.project_types,
      genres: splitList(form.genres),
      languages: splitList(form.languages),
      category: form.category,
      minimum_budget: form.minimum_budget ? Number(form.minimum_budget) : null,
      maximum_budget: form.maximum_budget ? Number(form.maximum_budget) : null,
      currency: form.currency,
      deadline: form.deadline || null,
      opening_date: form.opening_date || null,
      application_url: form.application_url || null,
      requirements: form.requirements,
      source_name: form.source_name.trim(),
      source_url: form.source_url.trim(),
      status: form.status,
    };

    try {
      if (opportunity) {
        await adminFundingApi.update(opportunity.id, payload);
        await onSaved("Dispositif mis à jour.");
      } else {
        payload.requirement_items = requirements
          .filter((item) => item.label.trim())
          .map((item) => ({
            label: item.label.trim(),
            is_mandatory: item.is_mandatory,
            required_document_type: item.required_document_type || null,
          }));
        await adminFundingApi.create(payload);
        await onSaved("Dispositif ajouté.");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Enregistrement impossible.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card space-y-5 p-6">
      <h3 className="font-display text-lg text-slatey-100">
        {opportunity ? "Modifier le dispositif" : "Nouveau dispositif"}
      </h3>

      {error ? <Alert tone="danger">{error}</Alert> : null}

      {/* Identité */}
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="label" htmlFor="name">Nom du dispositif *</label>
          <input
            id="name"
            className="field"
            required
            value={form.name}
            onChange={(event) => update("name", event.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="organization">Organisme *</label>
          <input
            id="organization"
            className="field"
            required
            value={form.organization}
            onChange={(event) => update("organization", event.target.value)}
          />
        </div>
      </div>

      <div>
        <label className="label" htmlFor="description">Description</label>
        <textarea
          id="description"
          className="field"
          rows={3}
          value={form.description}
          onChange={(event) => update("description", event.target.value)}
        />
      </div>

      {/* Traçabilité — en évidence, car c'est la condition de publication */}
      <fieldset className="rounded-lg border border-brass-500/30 bg-brass-500/[0.04] p-4">
        <legend className="px-2 text-xs uppercase tracking-wide text-brass-300">
          Traçabilité (obligatoire)
        </legend>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="source_name">Nom de la source *</label>
            <input
              id="source_name"
              className="field"
              required
              placeholder="Site officiel de l'organisme, appel à projets…"
              value={form.source_name}
              onChange={(event) => update("source_name", event.target.value)}
            />
          </div>
          <div>
            <label className="label" htmlFor="source_url">URL de la source *</label>
            <input
              id="source_url"
              type="url"
              className="field"
              required
              placeholder="https://…"
              value={form.source_url}
              onChange={(event) => update("source_url", event.target.value)}
            />
          </div>
        </div>
        <p className="hint">
          Un dispositif ne peut pas être publié comme ouvert sans son URL source. Elle est
          affichée aux utilisateurs avec la date de dernière vérification.
        </p>
      </fieldset>

      {/* Éligibilité */}
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="label" htmlFor="category">Type de financement</label>
          <select
            id="category"
            className="field"
            value={form.category}
            onChange={(event) => update("category", event.target.value)}
          >
            {(Object.keys(FUNDING_CATEGORY_LABELS) as FundingCategory[]).map((category) => (
              <option key={category} value={category}>
                {FUNDING_CATEGORY_LABELS[category]}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="country">Pays de l&apos;organisme</label>
          <input
            id="country"
            className="field"
            value={form.country}
            onChange={(event) => update("country", event.target.value)}
          />
        </div>
      </div>

      <div>
        <label className="label" htmlFor="eligible_countries">
          Pays éligibles (séparés par des virgules)
        </label>
        <input
          id="eligible_countries"
          className="field"
          placeholder="Sénégal, Cameroun, Côte d'Ivoire — laisser vide si ouvert à tous"
          value={form.eligible_countries}
          onChange={(event) => update("eligible_countries", event.target.value)}
        />
        <p className="hint">
          Vide = ouvert à tous les pays. Un projet dont le pays n&apos;y figure pas est marqué
          inéligible, avec la raison.
        </p>
      </div>

      <div>
        <span className="label">Types de projet acceptés</span>
        <div className="flex flex-wrap gap-2">
          {(Object.keys(PROJECT_TYPE_LABELS) as ProjectType[]).map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => toggleProjectType(type)}
              className={
                form.project_types.includes(type)
                  ? "btn-primary px-3 py-1.5 text-xs"
                  : "btn-secondary px-3 py-1.5 text-xs"
              }
            >
              {PROJECT_TYPE_LABELS[type]}
            </button>
          ))}
        </div>
        <p className="hint">Aucune sélection = ouvert à tous les types.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="label" htmlFor="genres">Genres (virgules)</label>
          <input
            id="genres"
            className="field"
            value={form.genres}
            onChange={(event) => update("genres", event.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="languages">Langues (virgules)</label>
          <input
            id="languages"
            className="field"
            value={form.languages}
            onChange={(event) => update("languages", event.target.value)}
          />
        </div>
      </div>

      {/* Montants et dates */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div>
          <label className="label" htmlFor="minimum_budget">Montant minimum</label>
          <input
            id="minimum_budget"
            type="number"
            min={0}
            className="field"
            value={form.minimum_budget}
            onChange={(event) => update("minimum_budget", event.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="maximum_budget">Montant maximum</label>
          <input
            id="maximum_budget"
            type="number"
            min={0}
            className="field"
            value={form.maximum_budget}
            onChange={(event) => update("maximum_budget", event.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="currency">Devise</label>
          <input
            id="currency"
            className="field"
            maxLength={10}
            value={form.currency}
            onChange={(event) => update("currency", event.target.value)}
          />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="label" htmlFor="opening_date">Ouverture des candidatures</label>
          <input
            id="opening_date"
            type="date"
            className="field"
            value={form.opening_date}
            onChange={(event) => update("opening_date", event.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="deadline">Date limite</label>
          <input
            id="deadline"
            type="date"
            className="field"
            value={form.deadline}
            onChange={(event) => update("deadline", event.target.value)}
          />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="label" htmlFor="application_url">Lien de candidature</label>
          <input
            id="application_url"
            type="url"
            className="field"
            value={form.application_url}
            onChange={(event) => update("application_url", event.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="website">Site de l&apos;organisme</label>
          <input
            id="website"
            type="url"
            className="field"
            value={form.website}
            onChange={(event) => update("website", event.target.value)}
          />
        </div>
      </div>

      <div>
        <label className="label" htmlFor="requirements">Pièces à fournir (texte libre)</label>
        <textarea
          id="requirements"
          className="field"
          rows={2}
          value={form.requirements}
          onChange={(event) => update("requirements", event.target.value)}
        />
      </div>

      {/* Pièces exigées, à la création */}
      {!opportunity ? (
        <div>
          <span className="label">Documents exigés</span>
          <p className="hint mb-2">
            Un document rattaché à un type permet au matching de dire à l&apos;auteur ce qui
            manque à son dossier.
          </p>
          <div className="space-y-2">
            {requirements.map((requirement, index) => (
              <div key={index} className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
                <input
                  className="field py-1.5 text-sm"
                  placeholder="Intitulé (Synopsis, Budget…)"
                  value={requirement.label}
                  onChange={(event) =>
                    setRequirements((current) =>
                      current.map((item, i) =>
                        i === index ? { ...item, label: event.target.value } : item,
                      ),
                    )
                  }
                />
                <select
                  className="field py-1.5 text-sm"
                  value={requirement.required_document_type}
                  onChange={(event) =>
                    setRequirements((current) =>
                      current.map((item, i) =>
                        i === index
                          ? { ...item, required_document_type: event.target.value }
                          : item,
                      ),
                    )
                  }
                >
                  <option value="">Aucun type rattaché</option>
                  {(Object.keys(DOCUMENT_TYPE_LABELS) as DocumentType[]).map((type) => (
                    <option key={type} value={type}>{DOCUMENT_TYPE_LABELS[type]}</option>
                  ))}
                </select>
                <button
                  type="button"
                  className="btn-ghost px-3 text-xs"
                  onClick={() =>
                    setRequirements((current) => current.filter((_, i) => i !== index))
                  }
                >
                  Retirer
                </button>
              </div>
            ))}
          </div>
          <button
            type="button"
            className="btn-secondary mt-2 px-3 py-1.5 text-xs"
            onClick={() =>
              setRequirements((current) => [
                ...current,
                { label: "", is_mandatory: true, required_document_type: "" },
              ])
            }
          >
            Ajouter une pièce
          </button>
        </div>
      ) : null}

      <div>
        <label className="label" htmlFor="status">Statut</label>
        <select
          id="status"
          className="field"
          value={form.status}
          onChange={(event) => update("status", event.target.value)}
        >
          <option value="UNVERIFIED">Non vérifié — non présenté comme actif</option>
          <option value="OPEN">Ouvert — vérifié et publié</option>
          <option value="UPCOMING">À venir</option>
          <option value="CLOSED">Clos</option>
        </select>
      </div>

      <div className="flex gap-2 border-t border-ink-700 pt-5">
        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? <Spinner /> : null}
          {opportunity ? "Enregistrer" : "Ajouter le dispositif"}
        </button>
        <button type="button" className="btn-ghost" onClick={onCancel}>
          Annuler
        </button>
      </div>
    </form>
  );
}
