"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { Alert, Spinner } from "@/components/ui";
import { ApiError, authApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { USER_TYPE_LABELS } from "@/lib/labels";
import type { UserType } from "@/lib/types";

const SELECTABLE_TYPES: UserType[] = ["AUTHOR", "DIRECTOR", "PRODUCER", "INSTITUTION"];

export default function RegisterPage() {
  const { register } = useAuth();
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
        setError("Inscription impossible pour le moment.");
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

  if (sent) {
    return (
      <div className="card p-8">
        <h1 className="font-display text-2xl text-slatey-100">Vérifiez votre boîte mail</h1>
        <p className="mt-3 text-sm text-slatey-300">{sent}</p>
        <p className="mt-4 text-sm text-slatey-400">
          Le lien a été envoyé à <span className="text-slatey-200">{form.email}</span>. Il expire
          dans 24 heures. Pensez à regarder dans les indésirables.
        </p>

        {resent ? (
          <div className="mt-5">
            <Alert tone="info">Si un lien était en attente, un nouveau vient de partir.</Alert>
          </div>
        ) : null}

        <div className="mt-6 flex flex-wrap gap-3">
          <button type="button" className="btn-secondary" onClick={handleResend}>
            Renvoyer le lien
          </button>
          <Link href="/connexion" className="btn-primary">
            Aller à la connexion
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-8">
      <h1 className="font-display text-2xl text-slatey-100">Créer un compte</h1>
      <p className="mt-1.5 text-sm text-slatey-400">
        Gratuit — 1 projet et 1 génération IA pour commencer.
      </p>

      <form onSubmit={handleSubmit} className="mt-7 space-y-4">
        {error ? <Alert tone="danger">{error}</Alert> : null}

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="first_name">Prénom</label>
            <input
              id="first_name"
              className="field"
              required
              value={form.first_name}
              onChange={(event) => update("first_name", event.target.value)}
            />
          </div>
          <div>
            <label className="label" htmlFor="last_name">Nom</label>
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
          <label className="label" htmlFor="email">Adresse e-mail</label>
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
          <label className="label" htmlFor="password">Mot de passe</label>
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
          <p className="hint">Au moins 8 caractères, mêlant lettres et chiffres.</p>
          {fieldErrors.password ? (
            <p className="hint text-signal-danger">{fieldErrors.password}</p>
          ) : null}
        </div>

        <div>
          <label className="label" htmlFor="user_type">Je suis</label>
          <select
            id="user_type"
            className="field"
            value={form.user_type}
            onChange={(event) => update("user_type", event.target.value)}
          >
            {SELECTABLE_TYPES.map((type) => (
              <option key={type} value={type}>{USER_TYPE_LABELS[type]}</option>
            ))}
          </select>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
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
            <label className="label" htmlFor="city">Ville</label>
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
          Créer mon compte
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slatey-400">
        Déjà inscrit ?{" "}
        <Link href="/connexion" className="text-brass-300 hover:text-brass-200">Se connecter</Link>
      </p>
    </div>
  );
}
