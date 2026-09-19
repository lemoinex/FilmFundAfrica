"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import { Alert, Spinner } from "@/components/ui";
import { ApiError, authApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useI18n } from "@/lib/i18n";
import type { UserType } from "@/lib/types";

const SELECTABLE_TYPES: UserType[] = ["AUTHOR", "DIRECTOR", "PRODUCER", "INSTITUTION"];

export default function RegisterPage() {
  const { register } = useAuth();
  const { t } = useI18n();
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    password: "",
    user_type: "AUTHOR" as UserType,
    country: "",
    city: "",
    profession: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  /** Message de confirmation : identique que l'adresse soit libre ou déjà prise. */
  const [sent, setSent] = useState<string | null>(null);
  const [resent, setResent] = useState(false);
  /**
   * `null` tant que le serveur n'a pas répondu : montrer le formulaire puis
   * le retirer serait plus déroutant qu'attendre un instant.
   *
   * En cas d'échec de l'appel, on ouvre. Le serveur reste seul juge et
   * refusera si l'inscription est fermée ; fermer sur un incident réseau
   * priverait d'inscription une plateforme ouverte, ce qui est le pire des
   * deux défauts.
   */
  const [open, setOpen] = useState<boolean | null>(null);

  useEffect(() => {
    let current = true;
    authApi
      .registrationStatus()
      .then((status) => current && setOpen(status.open))
      .catch(() => current && setOpen(true));
    return () => {
      current = false;
    };
  }, []);

  function update(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setFieldErrors({});
    setSubmitting(true);
    try {
      const detail = await register({
        ...form,
        country: form.country || undefined,
        city: form.city || undefined,
        profession: form.profession || undefined,
      });
      setSent(detail);
      setSubmitting(false);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        if (err.fields) {
          setFieldErrors(Object.fromEntries(err.fields.map((f) => [f.field, f.message])));
        }
      } else {
        setError(t("register.failed"));
      }
      setSubmitting(false);
    }
  }

  async function handleResend() {
    setResent(false);
    try {
      await authApi.resendVerification(form.email);
      setResent(true);
    } catch {
      // La réponse ne dit jamais si l'adresse existe : un échec réseau non plus
      // ne doit rien laisser deviner.
      setResent(true);
    }
  }

  if (open === null) {
    return (
      <div className="card flex items-center justify-center p-12">
        <Spinner />
      </div>
    );
  }

  if (!open) {
    return (
      <div className="card p-8">
        <h1 className="font-display text-2xl text-slatey-100">{t("register.closedTitle")}</h1>
        <p className="mt-3 text-sm text-slatey-300">{t("register.closedBody")}</p>
        <p className="mt-6 text-sm text-slatey-400">
          {t("register.closedHasAccount")}{" "}
          <Link href="/connexion" className="text-brass-300 hover:text-brass-200">
            {t("login.submit")}
          </Link>
        </p>
      </div>
    );
  }

  if (sent) {
    return (
      <div className="card p-8">
        <h1 className="font-display text-2xl text-slatey-100">{t("register.checkInbox")}</h1>
        <p className="mt-3 text-sm text-slatey-300">{sent}</p>
        <p className="mt-4 text-sm text-slatey-400">
          {t("register.linkSentTo", { email: form.email })}
        </p>

        {resent ? (
          <div className="mt-5">
            <Alert tone="info">{t("register.resent")}</Alert>
          </div>
        ) : null}

        <div className="mt-6 flex flex-wrap gap-3">
          <button type="button" className="btn-secondary" onClick={handleResend}>
            {t("register.resend")}
          </button>
          <Link href="/connexion" className="btn-primary">
            {t("verify.goToLogin")}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-8">
      <h1 className="font-display text-2xl text-slatey-100">{t("register.title")}</h1>
      <p className="mt-1.5 text-sm text-slatey-400">
        {t("register.subtitle")}
      </p>

      <form onSubmit={handleSubmit} className="mt-7 space-y-4">
        {error ? <Alert tone="danger">{error}</Alert> : null}

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="first_name">{t("register.firstName")}</label>
            <input
              id="first_name"
              className="field"
              required
              value={form.first_name}
              onChange={(event) => update("first_name", event.target.value)}
            />
          </div>
          <div>
            <label className="label" htmlFor="last_name">{t("register.lastName")}</label>
            <input
              id="last_name"
              className="field"
              required
              value={form.last_name}
              onChange={(event) => update("last_name", event.target.value)}
            />
          </div>
        </div>

        <div>
          <label className="label" htmlFor="email">{t("login.email")}</label>
          <input
            id="email"
            type="email"
            className="field"
            autoComplete="email"
            required
            value={form.email}
            onChange={(event) => update("email", event.target.value)}
          />
          {fieldErrors.email ? <p className="hint text-signal-danger">{fieldErrors.email}</p> : null}
        </div>

        <div>
          <label className="label" htmlFor="password">{t("login.password")}</label>
          <input
            id="password"
            type="password"
            className="field"
            autoComplete="new-password"
            required
            minLength={8}
            value={form.password}
            onChange={(event) => update("password", event.target.value)}
          />
          <p className="hint">{t("reset.passwordHint")}</p>
          {fieldErrors.password ? (
            <p className="hint text-signal-danger">{fieldErrors.password}</p>
          ) : null}
        </div>

        <div>
          <label className="label" htmlFor="user_type">{t("register.iAm")}</label>
          <select
            id="user_type"
            className="field"
            value={form.user_type}
            onChange={(event) => update("user_type", event.target.value)}
          >
            {SELECTABLE_TYPES.map((type) => (
              <option key={type} value={type}>
                {t(`userType.${type}`)}
              </option>
            ))}
          </select>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
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
            <label className="label" htmlFor="city">{t("register.city")}</label>
            <input
              id="city"
              className="field"
              value={form.city}
              onChange={(event) => update("city", event.target.value)}
            />
          </div>
        </div>

        <button type="submit" className="btn-primary w-full" disabled={submitting}>
          {submitting ? <Spinner /> : null}
          {t("register.submit")}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slatey-400">
        {t("register.alreadyRegistered")}{" "}
        <Link href="/connexion" className="text-brass-300 hover:text-brass-200">
          {t("login.submit")}
        </Link>
      </p>
    </div>
  );
}
