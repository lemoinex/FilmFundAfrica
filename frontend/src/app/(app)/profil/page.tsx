"use client";

import { useEffect, useState, type FormEvent } from "react";

import { Alert, Badge, SectionHeading, Spinner } from "@/components/ui";
import { ApiError, authApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatDate } from "@/lib/format";
import { USER_TYPE_LABELS } from "@/lib/labels";

const PLAN_LABELS: Record<string, string> = {
  FREE: "Gratuit",
  PRO_AUTHOR: "Pro Auteur",
  PRODUCER: "Producteur",
};

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    country: "",
    city: "",
    profession: "",
    bio: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!user?.profile) return;
    setForm({
      first_name: user.profile.first_name ?? "",
      last_name: user.profile.last_name ?? "",
      country: user.profile.country ?? "",
      city: user.profile.city ?? "",
      profession: user.profile.profession ?? "",
      bio: user.profile.bio ?? "",
    });
  }, [user]);

  function update(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
    setSaved(false);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await authApi.updateProfile(form);
      await refreshUser();
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Enregistrement impossible.");
    } finally {
      setSaving(false);
    }
  }

  if (!user) return null;

  return (
    <div className="space-y-7">
      <SectionHeading title="Profil" description="Ces informations n'apparaissent dans aucun document généré." />

      <div className="card p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm text-slatey-400">{user.email}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Badge tone="brass">{USER_TYPE_LABELS[user.user_type]}</Badge>
              <Badge tone="neutral">
                Offre {PLAN_LABELS[user.plan_code ?? "FREE"] ?? "Gratuit"}
              </Badge>
              <Badge tone="neutral">Membre depuis {formatDate(user.created_at)}</Badge>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs uppercase tracking-wide text-slatey-400">Crédits IA</p>
            <p className="font-display text-2xl tabular-nums text-brass-200">
              {user.ai_credits_remaining}
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="card space-y-4 p-6">
        {error ? <Alert tone="danger">{error}</Alert> : null}
        {saved ? <Alert tone="success">Profil enregistré.</Alert> : null}

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="first_name">Prénom</label>
            <input
              id="first_name"
              className="field"
              value={form.first_name}
              onChange={(event) => update("first_name", event.target.value)}
            />
          </div>
          <div>
            <label className="label" htmlFor="last_name">Nom</label>
            <input
              id="last_name"
              className="field"
              value={form.last_name}
              onChange={(event) => update("last_name", event.target.value)}
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
            <label className="label" htmlFor="city">Ville</label>
            <input
              id="city"
              className="field"
              value={form.city}
              onChange={(event) => update("city", event.target.value)}
            />
          </div>
        </div>

        <div>
          <label className="label" htmlFor="profession">Profession</label>
          <input
            id="profession"
            className="field"
            value={form.profession}
            onChange={(event) => update("profession", event.target.value)}
          />
        </div>

        <div>
          <label className="label" htmlFor="bio">Présentation</label>
          <textarea
            id="bio"
            className="field"
            rows={4}
            value={form.bio}
            onChange={(event) => update("bio", event.target.value)}
          />
        </div>

        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? <Spinner /> : null}
          Enregistrer
        </button>
      </form>
    </div>
  );
}
