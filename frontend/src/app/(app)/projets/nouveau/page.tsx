"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Alert, Spinner } from "@/components/ui";
import { ApiError, projectApi } from "@/lib/api";
import { classNames } from "@/lib/format";
import { DURATION_PRESETS, PROJECT_TYPE_LABELS } from "@/lib/labels";
import type { ProjectType } from "@/lib/types";

interface DraftCharacter {
  name: string;
  role: string;
  age: string;
  description: string;
  arc: string;
}

const STEPS = [
  { title: "Informations générales", hint: "Ce que le projet est, formellement." },
  { title: "Concept", hint: "L'idée, en quelques phrases tenables." },
  { title: "Personnages", hint: "Qui porte le récit — et contre qui." },
  { title: "Enjeux", hint: "Ce qui se perd si rien ne change." },
  { title: "Vision du réalisateur", hint: "Comment le film sera fait, et pourquoi ainsi." },
  { title: "Objectifs", hint: "Ce que vous attendez du projet." },
  { title: "Public cible", hint: "À qui le film s'adresse." },
];

const EMPTY_CHARACTER: DraftCharacter = {
  name: "",
  role: "",
  age: "",
  description: "",
  arc: "",
};

export default function NewProjectPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [form, setForm] = useState({
    title: "",
    project_type: "DOCUMENTARY" as ProjectType,
    genre: "",
    country: "",
    language: "Français",
    duration: "",
    concept: "",
    logline: "",
    theme: "",
    stakes: "",
    director_vision: "",
    objectives: "",
    target_audience: "",
  });
  const [characters, setCharacters] = useState<DraftCharacter[]>([{ ...EMPTY_CHARACTER }]);

  function update(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateCharacter(index: number, field: keyof DraftCharacter, value: string) {
    setCharacters((current) =>
      current.map((character, position) =>
        position === index ? { ...character, [field]: value } : character,
      ),
    );
  }

  const canContinue = step !== 0 || form.title.trim().length > 0;

  async function handleSubmit() {
    setError(null);
    setSubmitting(true);
    try {
      const project = await projectApi.create({
        title: form.title.trim(),
        project_type: form.project_type,
        genre: form.genre || null,
        country: form.country || null,
        language: form.language || "Français",
        duration: form.duration ? Number(form.duration) : null,
        concept: form.concept || null,
        logline: form.logline || null,
        theme: form.theme || null,
        stakes: form.stakes || null,
        director_vision: form.director_vision || null,
        objectives: form.objectives || null,
        target_audience: form.target_audience || null,
        characters: characters
          .filter((character) => character.name.trim())
          .map((character, index) => ({
            name: character.name.trim(),
            role: character.role || null,
            age: character.age || null,
            description: character.description || null,
            arc: character.arc || null,
            sort_order: index,
          })),
      });
      router.push(`/projets/${project.id}`);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Création impossible pour le moment.",
      );
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-7">
        <Link href="/projets" className="text-sm text-slatey-400 hover:text-slatey-200">
          ← Mes projets
        </Link>
        <h1 className="mt-3 font-display text-3xl text-slatey-100">Nouveau projet</h1>
        <p className="mt-1.5 text-sm text-slatey-400">
          Seul le titre est obligatoire. Tout le reste peut être complété plus tard — mais plus
          vous renseignez, meilleurs seront les documents générés.
        </p>
      </div>

      {/* Progression */}
      <ol className="mb-7 flex flex-wrap gap-1.5">
        {STEPS.map((item, index) => (
          <li key={item.title} className="flex-1 basis-16">
            <button
              type="button"
              onClick={() => setStep(index)}
              className={classNames(
                "h-1 w-full rounded-full transition-colors",
                index <= step ? "bg-brass-400" : "bg-ink-700",
              )}
              aria-label={`Étape ${index + 1} : ${item.title}`}
            />
          </li>
        ))}
      </ol>

      <div className="card p-6 sm:p-8">
        <p className="eyebrow mb-1.5">Étape {step + 1} sur {STEPS.length}</p>
        <h2 className="font-display text-xl text-slatey-100">{STEPS[step].title}</h2>
        <p className="mt-1 text-sm text-slatey-400">{STEPS[step].hint}</p>

        <div className="mt-6 space-y-4">
          {error ? <Alert tone="danger">{error}</Alert> : null}

          {step === 0 ? (
            <>
              <div>
                <label className="label" htmlFor="title">Titre du projet *</label>
                <input
                  id="title"
                  className="field"
                  required
                  value={form.title}
                  onChange={(event) => update("title", event.target.value)}
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="label" htmlFor="project_type">Type de projet</label>
                  <select
                    id="project_type"
                    className="field"
                    value={form.project_type}
                    onChange={(event) => update("project_type", event.target.value)}
                  >
                    {(Object.keys(PROJECT_TYPE_LABELS) as ProjectType[]).map((type) => (
                      <option key={type} value={type}>{PROJECT_TYPE_LABELS[type]}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label" htmlFor="genre">Genre</label>
                  <input
                    id="genre"
                    className="field"
                    placeholder="Documentaire de création, drame…"
                    value={form.genre}
                    onChange={(event) => update("genre", event.target.value)}
                  />
                </div>
                <div>
                  <label className="label" htmlFor="country">Pays</label>
                  <input
                    id="country"
                    className="field"
                    value={form.country}
                    onChange={(event) => update("country", event.target.value)}
                  />
                </div>
                <div>
                  <label className="label" htmlFor="duration">Durée cible (minutes)</label>
                  <input
                    id="duration"
                    type="number"
                    min={1}
                    max={1200}
                    className="field"
                    list="durations"
                    value={form.duration}
                    onChange={(event) => update("duration", event.target.value)}
                  />
                  <datalist id="durations">
                    {DURATION_PRESETS.map((value) => (
                      <option key={value} value={value} />
                    ))}
                  </datalist>
                  <p className="hint">Détermine la longueur du scénario : 1 page ≈ 1 minute.</p>
                </div>
              </div>
            </>
          ) : null}

          {step === 1 ? (
            <>
              <div>
                <label className="label" htmlFor="logline">Logline</label>
                <textarea
                  id="logline"
                  className="field"
                  rows={2}
                  placeholder="Une à deux phrases : qui, ce qu'il veut, ce qui l'en empêche."
                  value={form.logline}
                  onChange={(event) => update("logline", event.target.value)}
                />
              </div>
              <div>
                <label className="label" htmlFor="concept">Concept</label>
                <textarea
                  id="concept"
                  className="field"
                  rows={5}
                  placeholder="De quoi parle le film, et par quel dispositif ?"
                  value={form.concept}
                  onChange={(event) => update("concept", event.target.value)}
                />
              </div>
              <div>
                <label className="label" htmlFor="theme">Thème</label>
                <textarea
                  id="theme"
                  className="field"
                  rows={2}
                  value={form.theme}
                  onChange={(event) => update("theme", event.target.value)}
                />
              </div>
            </>
          ) : null}

          {step === 2 ? (
            <div className="space-y-4">
              {characters.map((character, index) => (
                <div key={index} className="rounded-lg border border-ink-700 p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <span className="text-xs uppercase tracking-wide text-slatey-400">
                      Personnage {index + 1}
                    </span>
                    {characters.length > 1 ? (
                      <button
                        type="button"
                        className="text-xs text-signal-danger hover:underline"
                        onClick={() =>
                          setCharacters((current) => current.filter((_, i) => i !== index))
                        }
                      >
                        Retirer
                      </button>
                    ) : null}
                  </div>
                  <div className="grid gap-3 sm:grid-cols-3">
                    <input
                      className="field"
                      placeholder="Nom"
                      value={character.name}
                      onChange={(event) => updateCharacter(index, "name", event.target.value)}
                    />
                    <input
                      className="field"
                      placeholder="Rôle (protagoniste…)"
                      value={character.role}
                      onChange={(event) => updateCharacter(index, "role", event.target.value)}
                    />
                    <input
                      className="field"
                      placeholder="Âge"
                      value={character.age}
                      onChange={(event) => updateCharacter(index, "age", event.target.value)}
                    />
                  </div>
                  <textarea
                    className="field mt-3"
                    rows={2}
                    placeholder="Description : situation, désir, contradiction."
                    value={character.description}
                    onChange={(event) => updateCharacter(index, "description", event.target.value)}
                  />
                  <textarea
                    className="field mt-3"
                    rows={2}
                    placeholder="Arc : ce qui change en lui du début à la fin."
                    value={character.arc}
                    onChange={(event) => updateCharacter(index, "arc", event.target.value)}
                  />
                </div>
              ))}
              <button
                type="button"
                className="btn-secondary w-full"
                onClick={() => setCharacters((current) => [...current, { ...EMPTY_CHARACTER }])}
              >
                Ajouter un personnage
              </button>
              <p className="hint">
                L&apos;IA n&apos;invente jamais de personnage : elle n&apos;utilise que ceux
                saisis ici.
              </p>
            </div>
          ) : null}

          {step === 3 ? (
            <div>
              <label className="label" htmlFor="stakes">Enjeux</label>
              <textarea
                id="stakes"
                className="field"
                rows={6}
                placeholder="Qu'est-ce qui est en jeu ? Que perd le protagoniste s'il échoue ?"
                value={form.stakes}
                onChange={(event) => update("stakes", event.target.value)}
              />
            </div>
          ) : null}

          {step === 4 ? (
            <div>
              <label className="label" htmlFor="director_vision">Vision du réalisateur</label>
              <textarea
                id="director_vision"
                className="field"
                rows={6}
                placeholder="Parti pris de mise en scène : image, son, montage, rapport aux personnes filmées."
                value={form.director_vision}
                onChange={(event) => update("director_vision", event.target.value)}
              />
              <p className="hint">Ce champ nourrit directement la note de réalisation.</p>
            </div>
          ) : null}

          {step === 5 ? (
            <div>
              <label className="label" htmlFor="objectives">Objectifs</label>
              <textarea
                id="objectives"
                className="field"
                rows={6}
                placeholder="Festivals visés, diffusion envisagée, partenaires recherchés…"
                value={form.objectives}
                onChange={(event) => update("objectives", event.target.value)}
              />
            </div>
          ) : null}

          {step === 6 ? (
            <div>
              <label className="label" htmlFor="target_audience">Public cible</label>
              <textarea
                id="target_audience"
                className="field"
                rows={6}
                placeholder="Qui regarde ce film, où, et pourquoi ?"
                value={form.target_audience}
                onChange={(event) => update("target_audience", event.target.value)}
              />
            </div>
          ) : null}
        </div>

        <div className="mt-8 flex items-center justify-between gap-3 border-t border-ink-700 pt-6">
          <button
            type="button"
            className="btn-ghost"
            onClick={() => setStep((current) => Math.max(0, current - 1))}
            disabled={step === 0}
          >
            Précédent
          </button>

          {step < STEPS.length - 1 ? (
            <button
              type="button"
              className="btn-primary"
              onClick={() => setStep((current) => current + 1)}
              disabled={!canContinue}
            >
              Continuer
            </button>
          ) : (
            <button
              type="button"
              className="btn-primary"
              onClick={handleSubmit}
              disabled={submitting || !form.title.trim()}
            >
              {submitting ? <Spinner /> : null}
              Créer mon projet
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
