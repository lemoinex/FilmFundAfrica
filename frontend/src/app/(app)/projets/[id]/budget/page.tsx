"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Alert, Badge, SectionHeading, SkeletonCard, Spinner } from "@/components/ui";
import { ApiError, budgetApi, downloadExport, projectApi } from "@/lib/api";
import {
  BUDGET_CATEGORY_LABELS,
  BUDGET_CATEGORY_ORDER,
  FUNDING_SOURCE_LABELS,
} from "@/lib/labels";
import type {
  Budget,
  BudgetCategory,
  FundingPlan,
  FundingSourceType,
  Project,
  SchedulePhase,
} from "@/lib/types";

/** Montant lisible : les budgets se comptent en centaines de milliers de FCFA. */
function money(amount: number, currency: string): string {
  return `${new Intl.NumberFormat("fr-FR").format(Math.round(amount))} ${currency}`;
}

export default function BudgetPage() {
  const { id } = useParams<{ id: string }>();

  const [project, setProject] = useState<Project | null>(null);
  const [budget, setBudget] = useState<Budget | null>(null);
  const [plan, setPlan] = useState<FundingPlan | null>(null);
  const [schedule, setSchedule] = useState<SchedulePhase[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [projectData, budgetData, planData, scheduleData] = await Promise.all([
        projectApi.get(id),
        budgetApi.get(id),
        budgetApi.plan(id),
        budgetApi.schedule(id),
      ]);
      setProject(projectData);
      setBudget(budgetData);
      setPlan(planData);
      setSchedule(scheduleData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chargement impossible.");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  /** Recharge budget et plan ensemble : le plan suit toujours le budget. */
  const refresh = useCallback(async () => {
    const [budgetData, planData] = await Promise.all([budgetApi.get(id), budgetApi.plan(id)]);
    setBudget(budgetData);
    setPlan(planData);
  }, [id]);

  async function run(action: () => Promise<unknown>) {
    setError(null);
    setBusy(true);
    try {
      await action();
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action impossible.");
    } finally {
      setBusy(false);
    }
  }

  const currency = budget?.currency ?? "XAF";
  const itemsByCategory = useMemo(() => {
    const grouped = new Map<BudgetCategory, Budget["items"]>();
    for (const category of BUDGET_CATEGORY_ORDER) grouped.set(category, []);
    for (const item of budget?.items ?? []) {
      grouped.set(item.category, [...(grouped.get(item.category) ?? []), item]);
    }
    return grouped;
  }, [budget]);

  if (error && !project) return <Alert tone="danger">{error}</Alert>;
  if (!project || !budget) {
    return (
      <div className="space-y-5">
        <div className="skeleton h-9 w-64 rounded" />
        <SkeletonCard lines={6} />
      </div>
    );
  }

  const empty = budget.items.length === 0;

  return (
    <div className="space-y-7">
      <div>
        <Link href={`/projets/${id}`} className="text-sm text-slatey-400 hover:text-slatey-200">
          ← {project.title}
        </Link>
        <h1 className="mt-3 font-display text-3xl text-slatey-100">Budget et financement</h1>
        <p className="mt-1.5 text-sm text-slatey-400">
          La trame propose les postes qu&apos;un comité de lecture attend. Les montants, eux,
          ne sont jamais devinés : vous les renseignez.
        </p>
      </div>

      {error ? <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert> : null}

      {/* ---------------------------------------------------------------- */}
      <div className="card p-6">
        <SectionHeading
          title="Budget prévisionnel"
          description={`${budget.items.length} poste(s) · total ${money(budget.total_amount, currency)}`}
          action={
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary"
                disabled={busy}
                onClick={() => run(() => budgetApi.generate(id))}
              >
                {busy ? <Spinner /> : null}
                {empty ? "Installer la trame" : "Compléter la trame"}
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() =>
                  downloadExport(
                    `/api/v1/projects/${id}/export/xlsx`,
                    `${project.title}_budget.xlsx`,
                  ).catch((err) =>
                    setError(err instanceof ApiError ? err.message : "Export impossible."),
                  )
                }
              >
                Exporter en tableur
              </button>
            </div>
          }
        />

        {empty ? (
          <Alert tone="info" title="Budget vide">
            Installez la trame : elle propose les postes attendus pour un projet de type{" "}
            {project.project_type}, à chiffrer ensuite ligne par ligne.
          </Alert>
        ) : (
          <div className="space-y-6">
            {BUDGET_CATEGORY_ORDER.map((category) => {
              const items = itemsByCategory.get(category) ?? [];
              if (items.length === 0) return null;
              const subtotal = budget.totals_by_category.find((t) => t.category === category);
              return (
                <div key={category}>
                  <div className="mb-2 flex items-baseline justify-between border-b border-ink-700 pb-1.5">
                    <h3 className="text-sm font-medium text-brass-200">
                      {BUDGET_CATEGORY_LABELS[category]}
                    </h3>
                    <span className="text-xs text-slatey-400">
                      {money(subtotal?.amount ?? 0, currency)}
                      {subtotal && subtotal.share > 0 ? ` · ${subtotal.share} %` : ""}
                    </span>
                  </div>

                  <div className="space-y-1">
                    {items.map((item) => (
                      <div
                        key={item.id}
                        className="grid grid-cols-[1fr_70px_80px_110px_110px_32px] items-center gap-2 rounded px-1.5 py-1 text-sm hover:bg-ink-800"
                      >
                        <span className="truncate text-slatey-200" title={item.label}>
                          {item.label}
                        </span>
                        <input
                          type="number"
                          min={0}
                          className="field py-1 text-right text-xs"
                          defaultValue={item.quantity}
                          aria-label={`Quantité — ${item.label}`}
                          onBlur={(event) => {
                            const quantity = Number(event.target.value);
                            if (quantity !== item.quantity) {
                              void run(() =>
                                budgetApi.updateItem(id, item.id, { quantity }),
                              );
                            }
                          }}
                        />
                        <span className="text-xs text-slatey-500">{item.unit ?? "—"}</span>
                        <input
                          type="number"
                          min={0}
                          className="field py-1 text-right text-xs"
                          defaultValue={item.unit_price}
                          aria-label={`Prix unitaire — ${item.label}`}
                          onBlur={(event) => {
                            const unit_price = Number(event.target.value);
                            if (unit_price !== item.unit_price) {
                              void run(() =>
                                budgetApi.updateItem(id, item.id, { unit_price }),
                              );
                            }
                          }}
                        />
                        {/* Le montant n'est jamais saisi : il vient du serveur. */}
                        <span className="text-right text-xs text-slatey-300">
                          {money(item.amount, currency)}
                        </span>
                        <button
                          type="button"
                          className="text-xs text-slatey-500 hover:text-signal-danger"
                          aria-label={`Supprimer ${item.label}`}
                          onClick={() => void run(() => budgetApi.deleteItem(id, item.id))}
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}

            <div className="flex items-baseline justify-between border-t border-ink-700 pt-3">
              <span className="font-display text-lg text-slatey-100">Total</span>
              <span className="font-display text-lg text-brass-200">
                {money(budget.total_amount, currency)}
              </span>
            </div>
          </div>
        )}

        <AddItemForm
          disabled={busy}
          onAdd={(payload) => run(() => budgetApi.addItem(id, payload))}
        />
      </div>

      {/* ---------------------------------------------------------------- */}
      <div className="card p-6">
        <SectionHeading
          title="Plan de financement"
          description="« Acquis » veut dire acquis : une source espérée reste dans le recherché."
        />

        {plan ? (
          <>
            <div className="mb-5 grid gap-3 sm:grid-cols-4">
              {[
                ["Budget total", plan.total_budget],
                ["Acquis", plan.secured_amount],
                ["Identifié", plan.identified_amount],
                ["Reste à financer", plan.sought_amount],
              ].map(([label, value]) => (
                <div key={label as string} className="rounded-lg border border-ink-700 p-3">
                  <p className="text-xs uppercase tracking-wide text-slatey-500">{label}</p>
                  <p className="mt-1 text-sm text-slatey-100">
                    {money(value as number, plan.currency)}
                  </p>
                </div>
              ))}
            </div>

            <div
              className="h-2 overflow-hidden rounded-full bg-ink-700"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(plan.funded_percentage)}
            >
              <div
                className="h-full bg-brass-500"
                style={{ width: `${Math.min(plan.funded_percentage, 100)}%` }}
              />
            </div>
            <p className="mt-1.5 text-xs text-slatey-400">
              {plan.funded_percentage} % du budget est acquis.
              {plan.uncovered_amount > 0
                ? ` ${money(plan.uncovered_amount, plan.currency)} ne sont couverts par aucune source, même espérée.`
                : ""}
            </p>

            <div className="mt-5 space-y-1">
              {plan.lines.map((line) => (
                <div
                  key={line.id}
                  className="flex flex-wrap items-center gap-3 rounded px-1.5 py-1.5 text-sm hover:bg-ink-800"
                >
                  <span className="text-slatey-200">
                    {line.source_name || FUNDING_SOURCE_LABELS[line.source_type]}
                  </span>
                  <Badge tone="neutral">{FUNDING_SOURCE_LABELS[line.source_type]}</Badge>
                  <span className="text-xs text-slatey-400">
                    {money(line.amount, plan.currency)}
                  </span>
                  <label className="flex items-center gap-1.5 text-xs text-slatey-400">
                    <input
                      type="checkbox"
                      checked={line.is_secured}
                      onChange={(event) =>
                        void run(() =>
                          budgetApi.updatePlanLine(id, line.id, {
                            is_secured: event.target.checked,
                          }),
                        )
                      }
                    />
                    Acquis
                  </label>
                  <button
                    type="button"
                    className="ml-auto text-xs text-slatey-500 hover:text-signal-danger"
                    onClick={() => void run(() => budgetApi.deletePlanLine(id, line.id))}
                  >
                    Retirer
                  </button>
                </div>
              ))}
              {plan.lines.length === 0 ? (
                <p className="text-sm text-slatey-400">
                  Aucune source listée. Ajoutez les fonds, préachats et apports envisagés.
                </p>
              ) : null}
            </div>

            <AddSourceForm
              disabled={busy}
              onAdd={(payload) => run(() => budgetApi.addPlanLine(id, payload))}
            />
          </>
        ) : null}
      </div>

      {/* ---------------------------------------------------------------- */}
      <div className="card p-6">
        <SectionHeading
          title="Calendrier de production"
          description="Une ligne par phase : les dates que les financeurs demandent."
        />
        <div className="space-y-2">
          {BUDGET_CATEGORY_ORDER.map((phase) => {
            const row = schedule.find((item) => item.phase === phase);
            return (
              <div key={phase} className="grid gap-2 sm:grid-cols-[1fr_140px_140px]">
                <span className="self-center text-sm text-slatey-200">
                  {BUDGET_CATEGORY_LABELS[phase]}
                </span>
                {(["start_date", "end_date"] as const).map((field) => (
                  <input
                    key={field}
                    type="date"
                    className="field py-1 text-xs"
                    aria-label={`${field === "start_date" ? "Début" : "Fin"} — ${BUDGET_CATEGORY_LABELS[phase]}`}
                    defaultValue={row?.[field] ?? ""}
                    onBlur={async (event) => {
                      const value = event.target.value || null;
                      if (value === (row?.[field] ?? null)) return;
                      try {
                        await budgetApi.setPhase(id, {
                          phase,
                          start_date: field === "start_date" ? value : (row?.start_date ?? null),
                          end_date: field === "end_date" ? value : (row?.end_date ?? null),
                        });
                        setSchedule(await budgetApi.schedule(id));
                      } catch (err) {
                        setError(
                          err instanceof ApiError ? err.message : "Enregistrement impossible.",
                        );
                      }
                    }}
                  />
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
function AddItemForm({
  disabled,
  onAdd,
}: {
  disabled: boolean;
  onAdd: (payload: {
    category: BudgetCategory;
    label: string;
    quantity: number;
    unit: string | null;
    unit_price: number;
  }) => void;
}) {
  const [label, setLabel] = useState("");
  const [category, setCategory] = useState<BudgetCategory>("PRODUCTION");

  return (
    <form
      className="mt-6 flex flex-wrap items-end gap-2 border-t border-ink-700 pt-5"
      onSubmit={(event) => {
        event.preventDefault();
        if (!label.trim()) return;
        onAdd({ category, label: label.trim(), quantity: 1, unit: null, unit_price: 0 });
        setLabel("");
      }}
    >
      <div className="min-w-[200px] flex-1">
        <label className="label" htmlFor="new-item">Ajouter un poste</label>
        <input
          id="new-item"
          className="field"
          placeholder="Ex. Location de caméra"
          value={label}
          onChange={(event) => setLabel(event.target.value)}
        />
      </div>
      <select
        className="field w-48"
        aria-label="Phase du poste"
        value={category}
        onChange={(event) => setCategory(event.target.value as BudgetCategory)}
      >
        {BUDGET_CATEGORY_ORDER.map((value) => (
          <option key={value} value={value}>
            {BUDGET_CATEGORY_LABELS[value]}
          </option>
        ))}
      </select>
      <button type="submit" className="btn-secondary" disabled={disabled || !label.trim()}>
        Ajouter
      </button>
    </form>
  );
}

function AddSourceForm({
  disabled,
  onAdd,
}: {
  disabled: boolean;
  onAdd: (payload: {
    source_type: FundingSourceType;
    source_name: string;
    amount: number;
    is_secured: boolean;
  }) => void;
}) {
  const [name, setName] = useState("");
  const [type, setType] = useState<FundingSourceType>("PUBLIC_FUND");
  const [amount, setAmount] = useState("");

  return (
    <form
      className="mt-6 flex flex-wrap items-end gap-2 border-t border-ink-700 pt-5"
      onSubmit={(event) => {
        event.preventDefault();
        if (!name.trim()) return;
        onAdd({
          source_type: type,
          source_name: name.trim(),
          amount: Number(amount) || 0,
          is_secured: false,
        });
        setName("");
        setAmount("");
      }}
    >
      <div className="min-w-[180px] flex-1">
        <label className="label" htmlFor="new-source">Ajouter une source</label>
        <input
          id="new-source"
          className="field"
          placeholder="Ex. Fonds de soutien national"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </div>
      <select
        className="field w-52"
        aria-label="Type de source"
        value={type}
        onChange={(event) => setType(event.target.value as FundingSourceType)}
      >
        {(Object.keys(FUNDING_SOURCE_LABELS) as FundingSourceType[]).map((value) => (
          <option key={value} value={value}>
            {FUNDING_SOURCE_LABELS[value]}
          </option>
        ))}
      </select>
      <input
        type="number"
        min={0}
        className="field w-36"
        placeholder="Montant"
        aria-label="Montant de la source"
        value={amount}
        onChange={(event) => setAmount(event.target.value)}
      />
      <button type="submit" className="btn-secondary" disabled={disabled || !name.trim()}>
        Ajouter
      </button>
    </form>
  );
}
