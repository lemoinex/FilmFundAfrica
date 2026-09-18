"use client";

import { useCallback, useEffect, useState } from "react";

import { Alert, Badge, SectionHeading, SkeletonCard, Spinner } from "@/components/ui";
import { ApiError, billingApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useI18n } from "@/lib/i18n";
import type { Payment, Plan, SubscriptionState } from "@/lib/types";

export default function SubscriptionPage() {
  const { refreshUser } = useAuth();
  const { t, tn, formatDate, formatNumber } = useI18n();

  /** Un prix nul n'est pas « 0 XOF / mois » mais l'offre gratuite. */
  const money = (amount: number, currency: string) =>
    amount <= 0
      ? t("billing.free")
      : t("billing.pricePerMonth", {
          amount: formatNumber(Math.round(amount)),
          currency,
        });

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
      setError(err instanceof ApiError ? err.message : t("load.failed"));
    }
  }, [t]);

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
          t("billing.checkoutOpened", { reference: payment.provider_reference }),
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("billing.subscribeFailed"));
    } finally {
      setBusy(null);
    }
  }

  async function cancel() {
    if (!window.confirm(t("billing.cancelConfirm"))) {
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
      setError(err instanceof ApiError ? err.message : t("billing.cancelFailed"));
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
        <h1 className="font-display text-3xl text-slatey-100">{t("billing.title")}</h1>
        <p className="mt-1.5 text-sm text-slatey-400">{t("billing.subtitle")}</p>
      </div>

      {error ? <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert> : null}
      {notice ? <Alert tone="info" onDismiss={() => setNotice(null)}>{notice}</Alert> : null}

      <div className="card p-6">
        <SectionHeading
          title={t("billing.currentPlan", { plan: current.name })}
          description={
            subscription.current_period_end
              ? t(subscription.is_renewing ? "billing.renewsOn" : "billing.cancelledUntil", {
                  date: formatDate(subscription.current_period_end),
                })
              : t("billing.noDeadline")
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
                {t("billing.cancel")}
              </button>
            ) : null
          }
        />
        <p className="text-sm text-slatey-300">
          {tn("billing.creditsLeft", subscription.ai_credits_remaining)} ·{" "}
          {current.max_projects === 0
            ? t("billing.unlimitedProjects")
            : tn("billing.projectQuota", current.max_projects)}
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
                {isCurrent ? <Badge tone="neutral">{t("billing.inUse")}</Badge> : null}
              </div>
              <p className="mt-1 text-sm text-brass-200">
                {money(plan.price_amount, plan.price_currency)}
              </p>
              <p className="mt-3 text-sm text-slatey-400">{plan.description}</p>

              <ul className="mt-4 space-y-1.5 text-sm text-slatey-300">
                <li>
                  {plan.max_projects === 0
                    ? t("billing.unlimitedProjects")
                    : tn("billing.projectQuota", plan.max_projects)}
                </li>
                <li>{tn("billing.monthlyCredits", plan.monthly_ai_credits)}</li>
                <li>{t(plan.allows_export ? "billing.exportAllowed" : "billing.exportDenied")}</li>
                <li>
                  {t(plan.allows_matching ? "billing.matchingAllowed" : "billing.matchingDenied")}
                </li>
              </ul>

              {plan.price_amount > 0 && !isCurrent ? (
                <button
                  type="button"
                  className="btn-primary mt-5 w-full"
                  onClick={() => subscribe(plan)}
                  disabled={busy !== null}
                >
                  {busy === plan.code ? <Spinner /> : null}
                  {t("billing.subscribe")}
                </button>
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="card p-6">
        <SectionHeading
          title={t("billing.mobileMoney")}
          description={t("billing.mobileMoneyHint")}
        />
        <label className="label" htmlFor="phone">{t("billing.phone")}</label>
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
          <SectionHeading title={t("billing.payments")} />
          <div className="space-y-1.5">
            {payments.map((payment) => (
              <div
                key={payment.id}
                className="flex flex-wrap items-center gap-3 rounded px-1.5 py-2 text-sm hover:bg-ink-800"
              >
                <span className="text-slatey-200">
                  {formatNumber(payment.amount)} {payment.currency}
                </span>
                <Badge tone={payment.status === "SUCCEEDED" ? "success" : "neutral"}>
                  {t(`paymentStatus.${payment.status}`)}
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
