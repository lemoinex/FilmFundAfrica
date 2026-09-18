/**
 * Traduction hors composant React.
 *
 * `useI18n()` couvre l'interface ; il reste le client HTTP, qui n'est pas un
 * composant et doit pourtant rendre des messages lisibles (« Session expirée »).
 * Ce module lui donne accès aux mêmes catalogues, en relisant la langue dans
 * le cookie plutôt que dans un contexte React.
 */

import { en } from "./en";
import { fr, type MessageKey } from "./fr";
import { DEFAULT_LOCALE, LOCALE_COOKIE, resolveLocale, type Locale } from "./locale";

const CATALOGS: Record<Locale, Record<string, string>> = { fr, en };

export function interpolate(
  template: string,
  vars?: Record<string, string | number>,
): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in vars ? String(vars[name]) : match,
  );
}

export function translate(
  locale: Locale,
  key: MessageKey,
  vars?: Record<string, string | number>,
): string {
  return interpolate(CATALOGS[locale][key] ?? key, vars);
}

/** Langue en cours d'après le cookie. Côté serveur, la langue par défaut. */
export function currentLocale(): Locale {
  if (typeof document === "undefined") return DEFAULT_LOCALE;
  const match = document.cookie.match(new RegExp(`(?:^|; )${LOCALE_COOKIE}=([^;]*)`));
  return resolveLocale(match ? decodeURIComponent(match[1]) : undefined);
}

/** Traduit dans la langue en cours, depuis un module non React. */
export function tr(key: MessageKey, vars?: Record<string, string | number>): string {
  return translate(currentLocale(), key, vars);
}
