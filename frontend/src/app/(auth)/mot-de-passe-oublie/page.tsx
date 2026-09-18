"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { Alert, Spinner } from "@/components/ui";
import { ApiError, authApi } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function ForgotPasswordPage() {
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const response = await authApi.forgotPassword(email);
      setMessage(response.detail);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("forgot.failed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card p-8">
      <h1 className="font-display text-2xl text-slatey-100">{t("forgot.title")}</h1>
      <p className="mt-1.5 text-sm text-slatey-400">
        {t("forgot.subtitle")}
      </p>

      {message ? (
        <div className="mt-6 space-y-4">
          <Alert tone="success">{message}</Alert>
          <Link href="/connexion" className="btn-secondary w-full">
            {t("forgot.backToLogin")}
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="mt-7 space-y-4">
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <div>
            <label className="label" htmlFor="email">{t("login.email")}</label>
            <input
              id="email"
              type="email"
              className="field"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <button type="submit" className="btn-primary w-full" disabled={submitting}>
            {submitting ? <Spinner /> : null}
            {t("forgot.submit")}
          </button>
        </form>
      )}
    </div>
  );
}
