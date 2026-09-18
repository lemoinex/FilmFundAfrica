"use client";

import { useCallback, useEffect, useState } from "react";

import { Alert, Badge, SectionHeading, SkeletonCard, Spinner } from "@/components/ui";
import { ApiError, billingApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatDate } from "@/lib/format";
import type { Payment, Plan, SubscriptionState } from "@/lib/types";

function money(amount: number, currency: string): string {
  if (amount <= 0) return "Gratuit";
  return `${new Intl.NumberFormat("fr-FR").format(Math.round(amount))} ${currency} / mois`;
}

const PAYMENT_LABELS: Record<Payment["status"], string> = {
  PENDING: "En attente",
  SUCCEEDED: "Réglé",
  FAILED: "Échoué",
  CANCELLED: "Annulé",
  REFUNDED: "Remboursé",
};

export default function SubscriptionPage() {
  const { refreshUser } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionState | null>(null);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [phone, setPhone] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [plansData, subscriptionData, paymentsData] = await Promise.all([
        billingApi.plans(),
        billingApi.subscription(),
        billingApi.payments(),
      ]);
      setPlans(plansData);
      setSubscription(subscriptionData);
      setPayments(paymentsData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chargement impossible.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function subscribe(plan: Plan) {
    setError(null);
    setNotice(null);
    setBusy(plan.code);
    try {
      const { payment, instructions } = await billingApi.checkout(
        plan.code,
        phone.trim() || undefined,
      );
      if (payment.checkout_url) {
        // Le prestataire prend la main : on quitte l'application.
        window.location.href = payment.checkout_url;
        return;
      }
      setNotice(
        instructions ??
          `Paiement ouvert sous la référence ${payment.provider_reference}. ` +
            "Votre offre sera activée dès sa validation.",
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Souscription impossible.");
    } finally {
      setBusy(null);
    }
  }

  async function cancel() {
    if (!window.confirm("Résilier l'abonnement ? Il reste actif jusqu'à la fin de la période payée.")) {
      return;
    }
    setError(null);
    setBusy("cancel");
    try {
      const { detail } = await billingApi.cancel();
      setNotice(detail);
      await load();
      await refreshUser();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Résiliation impossible.");
    } finally {
      setBusy(null);
    }
  }

  if (error && !subscription) return <Alert tone="danger">{error}</Alert>;
  if (!subscription) {
    return (
      <div className="space-y-5">
        <div className="skeleton h-9 w-56 rounded" />
        <SkeletonCard lines={5} />
      </div>
    );
  }

  const current = subscription.plan;

  return (
    <div className="space-y-7">
      <div>
        <h1 className="font-display text-3xl text-slatey-100">Abonnement</h1>
        <p className="mt-1.5 text-sm text-slatey-400">
          Les prix et les quotas viennent du serveur : ils sont modifiables sans nouvelle
          version de l&apos;application.
        </p>
      </div>

      {error ? <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert> : null}
      {notice ? <Alert tone="info" onDismiss={() => setNotice(null)}>{notice}</Alert> : null}

      <div className="card p-6">
        <SectionHeading
          title={`Offre en cours : ${current.name}`}
          description={
            subscription.current_period_end
              ? subscription.is_renewing
                ? `Reconduction le ${formatDate(subscription.current_period_end)}.`
                : `Résilié : actif jusqu'au ${formatDate(subscription.current_period_end)}, sans reconduction.`
              : "Offre gratuite, sans échéance."
          }
          action={
            subscription.is_renewing && current.price_amount > 0 ? (
              <button
                type="button"
                className="btn-secondary"
                onClick={cancel}
                disabled={busy === "cancel"}
              >
                {busy === "cancel" ? <Spinner /> : null}
                Résilier
              </button>
            ) : null
          }
        />
        <p className="text-sm text-slatey-300">
          {subscription.ai_credits_remaining} crédit(s) IA restant(s) ·{" "}
          {current.max_projects === 0 ? "projets illimités" : `${current.max_projects} projet(s)`}
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {plans.map((plan) => {
          const isCurrent = plan.code === current.code;
          return (
            <div
              key={plan.id}
              className={
                isCurrent
                  ? "card border-brass-500/50 bg-brass-500/5 p-6"
                  : "card p-6"
              }
            >
              <div className="flex items-baseline justify-between">
                <h2 className="font-display text-xl text-slatey-100">{plan.name}</h2>
                {isCurrent ? <Badge tone="neutral">en cours</Badge> : null}
              </div>
              <p className="mt-1 text-sm text-brass-200">
                {money(plan.price_amount, plan.price_currency)}
              </p>
              <p className="mt-3 text-sm text-slatey-400">{plan.description}</p>

              <ul className="mt-4 space-y-1.5 text-sm text-slatey-300">
                <li>
                  {plan.max_projects === 0 ? "Projets illimités" : `${plan.max_projects} projet(s)`}
                </li>
                <li>{plan.monthly_ai_credits} crédits IA par mois</li>
                <li>{plan.allows_export ? "Export du dossier" : "Sans export"}</li>
                <li>{plan.allows_matching ? "Matching financements" : "Matching limité"}</li>
              </ul>

              {plan.price_amount > 0 && !isCurrent ? (
                <button
                  type="button"
                  className="btn-primary mt-5 w-full"
                  onClick={() => subscribe(plan)}
                  disabled={busy !== null}
                >
                  {busy === plan.code ? <Spinner /> : null}
                  Souscrire
                </button>
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="card p-6">
        <SectionHeading
          title="Paiement mobile money"
          description="Renseignez le numéro à débiter avant de souscrire, si votre prestataire le demande."
        />
        <label className="label" htmlFor="phone">Numéro de téléphone</label>
        <input
          id="phone"
          className="field max-w-xs"
          placeholder="+221 …"
          value={phone}
          onChange={(event) => setPhone(event.target.value)}
        />
      </div>

      {payments.length > 0 ? (
        <div className="card p-6">
          <SectionHeading title="Mes paiements" />
          <div className="space-y-1.5">
            {payments.map((payment) => (
              <div
                key={payment.id}
                className="flex flex-wrap items-center gap-3 rounded px-1.5 py-2 text-sm hover:bg-ink-800"
              >
                <span className="text-slatey-200">
                  {new Intl.NumberFormat("fr-FR").format(payment.amount)} {payment.currency}
                </span>
                <Badge tone={payment.status === "SUCCEEDED" ? "success" : "neutral"}>
                  {PAYMENT_LABELS[payment.status]}
                </Badge>
                <span className="text-xs text-slatey-500">{formatDate(payment.created_at)}</span>
                <span className="text-xs text-slatey-600">{payment.provider_reference}</span>
                {payment.failure_reason ? (
                  <span className="text-xs text-signal-danger">{payment.failure_reason}</span>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
