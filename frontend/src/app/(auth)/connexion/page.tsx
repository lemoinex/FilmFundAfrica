"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { Alert, Spinner } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Connexion impossible pour le moment.");
      setSubmitting(false);
    }
  }

  return (
    <div className="card p-8">
      <h1 className="font-display text-2xl text-slatey-100">Connexion</h1>
      <p className="mt-1.5 text-sm text-slatey-400">Retrouvez vos projets et vos dossiers.</p>

      <form onSubmit={handleSubmit} className="mt-7 space-y-4">
        {error ? <Alert tone="danger">{error}</Alert> : null}

        <div>
          <label className="label" htmlFor="email">Adresse e-mail</label>
          <input
            id="email"
            type="email"
            className="field"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>

        <div>
          <div className="mb-1.5 flex items-baseline justify-between">
            <label className="label mb-0" htmlFor="password">Mot de passe</label>
            <Link href="/mot-de-passe-oublie" className="text-xs text-brass-300 hover:text-brass-200">
              Mot de passe oublié ?
            </Link>
          </div>
          <input
            id="password"
            type="password"
            className="field"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>

        <button type="submit" className="btn-primary w-full" disabled={submitting}>
          {submitting ? <Spinner /> : null}
          Se connecter
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slatey-400">
        Pas encore de compte ?{" "}
        <Link href="/inscription" className="text-brass-300 hover:text-brass-200">
          Créer un compte
        </Link>
      </p>
    </div>
  );
}
