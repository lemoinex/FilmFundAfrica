"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Alert, Spinner } from "@/components/ui";
import { ApiError, projectApi } from "@/lib/api";
import { classNames } from "@/lib/format";
import { useI18n, type MessageKey } from "@/lib/i18n";
import { DURATION_PRESETS, PROJECT_TYPES } from "@/lib/labels";
import type { ProjectType } from "@/lib/types";

interface DraftCharacter {
  name: string;
  role: string;
  age: string;
  description: string;
  arc: string;
}

const STEPS: { title: MessageKey; hint: MessageKey }[] = [
  { title: "newProject.step.general", hint: "newProject.step.generalHint" },
  { title: "newProject.step.concept", hint: "newProject.step.conceptHint" },
  { title: "newProject.step.characters", hint: "newProject.step.charactersHint" },
  { title: "newProject.step.stakes", hint: "newProject.step.stakesHint" },
  { title: "newProject.step.vision", hint: "newProject.step.visionHint" },
  { title: "newProject.step.objectives", hint: "newProject.step.objectivesHint" },
  { title: "newProject.step.audience", hint: "newProject.step.audienceHint" },
];

const EMPTY_CHARACTER: DraftCharacter = {
  name: "",
  role: "",
  age: "",
  description: "",
  arc: "",
};

export default function NewProjectPage() {
  const { t } = useI18n();
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
        err instanceof ApiError ? err.message : t("newProject.failed"),
      );
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-7">
        <Link href="/projets" className="text-sm text-slatey-400 hover:text-slatey-200">
          {t("newProject.back")}
        </Link>
        <h1 className="mt-3 font-display text-3xl text-slatey-100">{t("newProject.title")}</h1>
        <p className="mt-1.5 text-sm text-slatey-400">{t("newProject.subtitle")}</p>
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
              aria-label={t("newProject.stepAria", {
                number: index + 1,
                title: t(item.title),
              })}
            />
          </li>
        ))}
      </ol>

      <div className="card p-6 sm:p-8">
        <p className="eyebrow mb-1.5">
          {t("newProject.stepCounter", { number: step + 1, total: STEPS.length })}
        </p>
        <h2 className="font-display text-xl text-slatey-100">{t(STEPS[step].title)}</h2>
        <p className="mt-1 text-sm text-slatey-400">{t(STEPS[step].hint)}</p>

        <div className="mt-6 space-y-4">
          {error ? <Alert tone="danger">{error}</Alert> : null}

          {step === 0 ? (
            <>
              <div>
                <label className="label" htmlFor="title">{t("newProject.titleField")}</label>
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
                  <label className="label" htmlFor="project_type">{t("search.projectType")}</label>
                  <select
                    id="project_type"
                    className="field"
                    value={form.project_type}
                    onChange={(event) => update("project_type", event.target.value)}
                  >
                    {PROJECT_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {t(`projectType.${type}`)}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label" htmlFor="genre">{t("search.genre")}</label>
                  <input
                    id="genre"
                    className="field"
                    placeholder={t("newProject.genrePlaceholder")}
                    value={form.genre}
                    onChange={(event) => update("genre", event.target.value)}
                  />
                </div>
                <div>
                  <label className="label" htmlFor="country">{t("register.country")}</label>
                  <input
                    id="country"
                    className="field"
                    value={form.country}
                    onChange={(event) => update("country", event.target.value)}
                  />
                </div>
                <div>
                  <label className="label" htmlFor="duration">{t("newProject.duration")}</label>
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
                  <p className="hint">{t("newProject.durationHint")}</p>
                </div>
              </div>
            </>
          ) : null}

          {step === 1 ? (
            <>
              <div>
                <label className="label" htmlFor="logline">{t("newProject.logline")}</label>
                <textarea
                  id="logline"
                  className="field"
                  rows={2}
                  placeholder={t("newProject.loglinePlaceholder")}
                  value={form.logline}
                  onChange={(event) => update("logline", event.target.value)}
                />
              </div>
              <div>
                <label className="label" htmlFor="concept">{t("newProject.concept")}</label>
                <textarea
                  id="concept"
                  className="field"
                  rows={5}
                  placeholder={t("newProject.conceptPlaceholder")}
                  value={form.concept}
                  onChange={(event) => update("concept", event.target.value)}
                />
              </div>
              <div>
                <label className="label" htmlFor="theme">{t("newProject.theme")}</label>
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
                      {t("newProject.character", { number: index + 1 })}
                    </span>
                    {characters.length > 1 ? (
                      <button
                        type="button"
                        className="text-xs text-signal-danger hover:underline"
                        onClick={() =>
                          setCharacters((current) => current.filter((_, i) => i !== index))
                        }
                      >
                        {t("newProject.removeCharacter")}
                      </button>
                    ) : null}
                  </div>
                  <div className="grid gap-3 sm:grid-cols-3">
                    <input
                      className="field"
                      placeholder={t("newProject.characterName")}
                      value={character.name}
                      onChange={(event) => updateCharacter(index, "name", event.target.value)}
                    />
                    <input
                      className="field"
                      placeholder={t("newProject.characterRole")}
                      value={character.role}
                      onChange={(event) => updateCharacter(index, "role", event.target.value)}
                    />
                    <input
                      className="field"
                      placeholder={t("newProject.characterAge")}
                      value={character.age}
                      onChange={(event) => updateCharacter(index, "age", event.target.value)}
                    />
                  </div>
                  <textarea
                    className="field mt-3"
                    rows={2}
                    placeholder={t("newProject.characterDescription")}
                    value={character.description}
                    onChange={(event) => updateCharacter(index, "description", event.target.value)}
                  />
                  <textarea
                    className="field mt-3"
                    rows={2}
                    placeholder={t("newProject.characterArc")}
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
                {t("newProject.addCharacter")}
              </button>
              <p className="hint">
                {t("newProject.charactersHint")}
              </p>
            </div>
          ) : null}

          {step === 3 ? (
            <div>
              <label className="label" htmlFor="stakes">{t("newProject.stakes")}</label>
              <textarea
                id="stakes"
                className="field"
                rows={6}
                placeholder={t("newProject.stakesPlaceholder")}
                value={form.stakes}
                onChange={(event) => update("stakes", event.target.value)}
              />
            </div>
          ) : null}

          {step === 4 ? (
            <div>
              <label className="label" htmlFor="director_vision">{t("newProject.vision")}</label>
              <textarea
                id="director_vision"
                className="field"
                rows={6}
                placeholder={t("newProject.visionPlaceholder")}
                value={form.director_vision}
                onChange={(event) => update("director_vision", event.target.value)}
              />
              <p className="hint">{t("newProject.visionHint")}</p>
            </div>
          ) : null}

          {step === 5 ? (
            <div>
              <label className="label" htmlFor="objectives">{t("newProject.objectives")}</label>
              <textarea
                id="objectives"
                className="field"
                rows={6}
                placeholder={t("newProject.objectivesPlaceholder")}
                value={form.objectives}
                onChange={(event) => update("objectives", event.target.value)}
              />
            </div>
          ) : null}

          {step === 6 ? (
            <div>
              <label className="label" htmlFor="target_audience">{t("newProject.audience")}</label>
              <textarea
                id="target_audience"
                className="field"
                rows={6}
                placeholder={t("newProject.audiencePlaceholder")}
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
            {t("search.previous")}
          </button>

          {step < STEPS.length - 1 ? (
            <button
              type="button"
              className="btn-primary"
              onClick={() => setStep((current) => current + 1)}
              disabled={!canContinue}
            >
              {t("common.continue")}
            </button>
          ) : (
            <button
              type="button"
              className="btn-primary"
              onClick={handleSubmit}
              disabled={submitting || !form.title.trim()}
            >
              {submitting ? <Spinner /> : null}
              {t("projects.create")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
