/**
 * Ce que le serveur doit savoir de la langue, sans embarquer de composant.
 *
 * Ce fichier n'est pas marqué `"use client"` : la mise en page racine, qui
 * est un composant serveur, lit le cookie et en déduit `<html lang>`. Les
 * fonctions exportées depuis un module client ne seraient, elles, que des
 * références inertes côté serveur.
 */

export const LOCALES = ["fr", "en"] as const;
export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "fr";

/** Cookie posé par le sélecteur de langue, relu à chaque rendu serveur. */
export const LOCALE_COOKIE = "filmfund_locale";
export const LOCALE_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

/** Nom de chaque langue dans sa propre langue : c'est ainsi qu'on la cherche. */
export const LOCALE_NAMES: Record<Locale, string> = {
  fr: "Français",
  en: "English",
};

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}

export function resolveLocale(value: unknown): Locale {
  return isLocale(value) ? value : DEFAULT_LOCALE;
}
