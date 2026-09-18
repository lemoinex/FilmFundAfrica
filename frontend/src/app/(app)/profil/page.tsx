"use client";

import { useEffect, useState, type FormEvent } from "react";

import { Alert, Badge, SectionHeading, Spinner } from "@/components/ui";
import { ApiError, authApi } from "@/lib/api";
import { LanguageSwitcher } from "@/components/language-switcher";
import { useAuth } from "@/lib/auth-context";
import { useI18n, type MessageKey } from "@/lib/i18n";

/** Codes d'offre connus ; tout autre code retombe sur l'offre gratuite. */
const PLAN_KEYS: Record<string, MessageKey> = {
  FREE: "plan.FREE",
  PRO_AUTHOR: "plan.PRO_AUTHOR",
  PRODUCER: "plan.PRODUCER",
};

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const { t, formatDate } = useI18n();
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
      setError(err instanceof ApiError ? err.message : t("profile.saveFailed"));
    } finally {
      setSaving(false);
    }
  }

  if (!user) return null;

  return (
    <div className="space-y-7">
      <SectionHeading title={t("profile.title")} description={t("profile.subtitle")} />

      <div className="card p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm text-slatey-400">{user.email}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Badge tone="brass">{t(`userType.${user.user_type}`)}</Badge>
              <Badge tone="neutral">
                {t("profile.plan", {
                  plan: t(PLAN_KEYS[user.plan_code ?? "FREE"] ?? "plan.FREE"),
                })}
              </Badge>
              <Badge tone="neutral">
                {t("profile.memberSince", { date: formatDate(user.created_at) })}
              </Badge>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs uppercase tracking-wide text-slatey-400">{t("profile.credits")}</p>
            <p className="font-display text-2xl tabular-nums text-brass-200">
              {user.ai_credits_remaining}
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="card space-y-4 p-6">
        {error ? <Alert tone="danger">{error}</Alert> : null}
        {saved ? <Alert tone="success">{t("profile.saved")}</Alert> : null}

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="first_name">{t("register.firstName")}</label>
            <input
              id="first_name"
              className="field"
              value={form.first_name}
              onChange={(event) => update("first_name", event.target.value)}
            />
          </div>
          <div>
            <label className="label" htmlFor="last_name">{t("register.lastName")}</label>
            <input
              id="last_name"
              className="field"
              value={form.last_name}
              onChange={(event) => update("last_name", event.target.value)}
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
            <label className="label" htmlFor="city">{t("register.city")}</label>
            <input
              id="city"
              className="field"
              value={form.city}
              onChange={(event) => update("city", event.target.value)}
            />
          </div>
        </div>

        <div>
          <label className="label" htmlFor="profession">{t("profile.profession")}</label>
          <input
            id="profession"
            className="field"
            value={form.profession}
            onChange={(event) => update("profession", event.target.value)}
          />
        </div>

        <div>
          <label className="label" htmlFor="bio">{t("profile.bio")}</label>
          <textarea
            id="bio"
            className="field"
            rows={4}
            value={form.bio}
            onChange={(event) => update("bio", event.target.value)}
          />
        </div>

        <div>
          <span className="label">{t("common.language")}</span>
          <LanguageSwitcher className="block" />
          <p className="hint">{t("profile.languageHint")}</p>
        </div>

        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? <Spinner /> : null}
          {t("common.save")}
        </button>
      </form>
    </div>
  );
}
