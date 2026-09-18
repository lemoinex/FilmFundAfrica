"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { Alert, Spinner } from "@/components/ui";
import { ApiError, authApi } from "@/lib/api";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const [token, setToken] = useState(searchParams.get("token") ?? "");
  const [password, setPassword] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await authApi.resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Réinitialisation impossible.");
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <div className="space-y-4">
        <Alert tone="success">
          Mot de passe mis à jour. Vous pouvez vous connecter avec le nouveau.
        </Alert>
        <Link href="/connexion" className="btn-primary w-full">Se connecter</Link>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="mt-7 space-y-4">
      {error ? <Alert tone="danger">{error}</Alert> : null}

      {!searchParams.get("token") ? (
        <div>
          <label className="label" htmlFor="token">Jeton reçu par e-mail</label>
          <input
            id="token"
            className="field"
            required
            value={token}
            onChange={(event) => setToken(event.target.value)}
          />
        </div>
      ) : null}

      <div>
        <label className="label" htmlFor="password">Nouveau mot de passe</label>
        <input
          id="password"
          type="password"
          className="field"
          autoComplete="new-password"
          required
          minLength={8}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <p className="hint">Au moins 8 caractères, mêlant lettres et chiffres.</p>
      </div>

      <button type="submit" className="btn-primary w-full" disabled={submitting}>
        {submitting ? <Spinner /> : null}
        Définir le mot de passe
      </button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="card p-8">
      <h1 className="font-display text-2xl text-slatey-100">Nouveau mot de passe</h1>
      <Suspense fallback={<div className="skeleton mt-7 h-32 rounded" />}>
        <ResetPasswordForm />
      </Suspense>
    </div>
  );
}
