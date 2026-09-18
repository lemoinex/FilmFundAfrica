"use client";

import { authApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useI18n } from "@/lib/i18n";
import { LOCALES, LOCALE_NAMES, isLocale } from "@/lib/i18n/locale";

/**
 * Sélecteur de langue.
 *
 * Le changement est immédiat côté interface — il ne dépend pas de l'API, et
 * fonctionne donc aussi sur les pages publiques et hors ligne. Quand une
 * session est ouverte, la préférence est en plus enregistrée sur le profil,
 * pour qu'elle suive la personne d'un appareil à l'autre. Si cet appel échoue,
 * on n'en fait pas une erreur visible : la langue est déjà changée, et le
 * cookie la retiendra sur cet appareil.
 */
export function LanguageSwitcher({ className }: { className?: string }) {
  const { locale, setLocale, t } = useI18n();
  const { user, refreshUser } = useAuth();

  return (
    <label className={className}>
      <span className="sr-only">{t("common.changeLanguage")}</span>
      <select
        value={locale}
        aria-label={t("common.changeLanguage")}
        onChange={async (event) => {
          const next = event.target.value;
          if (!isLocale(next)) return;
          setLocale(next);
          if (!user) return;
          try {
            await authApi.updateProfile({ preferred_locale: next });
            await refreshUser();
          } catch {
            // Préférence non enregistrée : le cookie fait foi sur cet appareil.
          }
        }}
        className="rounded-lg border border-ink-700 bg-ink-900 px-2 py-1 text-xs text-slatey-300 transition-colors hover:border-ink-600 hover:text-slatey-100"
      >
        {LOCALES.map((value) => (
          <option key={value} value={value}>
            {LOCALE_NAMES[value]}
          </option>
        ))}
      </select>
    </label>
  );
}
