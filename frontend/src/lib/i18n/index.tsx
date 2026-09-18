"use client";

/**
 * Internationalisation de l'interface.
 *
 * Les catalogues sont de simples objets à clés plates (`projets.titre`), et
 * `en.ts` est typé `Record<MessageKey, string>` : une clé ajoutée au français
 * et oubliée en anglais fait échouer `tsc`. C'est la seule garantie qui tienne
 * dans la durée — une traduction manquante ne se voit pas à la relecture.
 *
 * Ce que ce module ne traduit pas, et il faut le savoir :
 *
 * * les **messages d'erreur de l'API**, rédigés en français côté serveur ;
 * * les **documents générés** par l'IA, dont la langue est celle du projet.
 *
 * La langue retenue vient, dans l'ordre : du profil de la personne connectée
 * (`preferred_locale`), du cookie `filmfund_locale`, puis du français. Le
 * cookie est lu par la mise en page racine, côté serveur, pour que `<html
 * lang>` soit juste dès le premier rendu — sans quoi un lecteur d'écran
 * annoncerait une page anglaise avec une voix française.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { en } from "./en";
import { fr, type MessageKey } from "./fr";
import { LOCALE_COOKIE, LOCALE_COOKIE_MAX_AGE_SECONDS, type Locale } from "./locale";
import { interpolate } from "./translate";

export {
  DEFAULT_LOCALE,
  LOCALES,
  LOCALE_COOKIE,
  LOCALE_NAMES,
  isLocale,
  resolveLocale,
  type Locale,
} from "./locale";

export type Messages = typeof fr;
export type { MessageKey };

/** Clés pluralisées : `projets.compte_one` / `projets.compte_other`. */
type PluralBase<K> = K extends `${infer Base}_other` ? Base : never;
export type PluralKey = PluralBase<MessageKey>;

const CATALOGS: Record<Locale, Record<string, string>> = { fr, en };

type Vars = Record<string, string | number>;

export type Translate = (key: MessageKey, vars?: Vars) => string;
export type TranslatePlural = (key: PluralKey, count: number, vars?: Vars) => string;

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: Translate;
  /** Accorde selon `count`, en suivant les règles de la langue. */
  tn: TranslatePlural;
  formatDate: (value?: string | null) => string;
  formatDateTime: (value?: string | null) => string;
  formatRelative: (value?: string | null) => string;
  formatNumber: (value: number) => string;
  /** Nombre de pages A4 estimé d'un document, exprimé en toutes lettres. */
  formatPages: (words: number) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

const EMPTY = "—";
/** Un document de dossier tient environ 450 mots par page A4. */
const WORDS_PER_PAGE = 450;

export function LocaleProvider({
  initialLocale,
  children,
}: {
  initialLocale: Locale;
  children: ReactNode;
}) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    document.cookie = `${LOCALE_COOKIE}=${next}; path=/; max-age=${LOCALE_COOKIE_MAX_AGE_SECONDS}; samesite=lax`;
  }, []);

  useEffect(() => {
    // `<html lang>` est posé par le serveur ; il doit suivre un changement
    // fait en cours de navigation, sans rechargement.
    document.documentElement.lang = locale;
  }, [locale]);

  const value = useMemo<I18nContextValue>(() => {
    const catalog = CATALOGS[locale];
    const tag = locale === "fr" ? "fr-FR" : "en-GB";
    const plural = new Intl.PluralRules(tag);

    const t: Translate = (key, vars) => interpolate(catalog[key] ?? key, vars);

    const tn: TranslatePlural = (key, count, vars) => {
      const category = plural.select(count);
      const template =
        catalog[`${key}_${category}`] ?? catalog[`${key}_other`] ?? `${key}_other`;
      return interpolate(template, { count, ...vars });
    };

    const dateFormat = new Intl.DateTimeFormat(tag, {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
    const dateTimeFormat = new Intl.DateTimeFormat(tag, {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
    const numberFormat = new Intl.NumberFormat(tag);
    const pagesFormat = new Intl.NumberFormat(tag, { maximumFractionDigits: 1 });
    // `Intl` porte déjà « il y a 3 jours » / « 3 days ago » : les écrire dans
    // le catalogue reviendrait à retraduire ce que la plateforme sait faire.
    const relativeFormat = new Intl.RelativeTimeFormat(tag, { numeric: "auto" });

    const formatDate = (value?: string | null) =>
      value ? dateFormat.format(new Date(value)) : EMPTY;

    const formatRelative = (value?: string | null) => {
      if (!value) return EMPTY;
      const minutes = Math.round((Date.now() - new Date(value).getTime()) / 60000);
      if (minutes < 1) return t("format.now");
      if (minutes < 60) return relativeFormat.format(-minutes, "minute");
      const hours = Math.round(minutes / 60);
      if (hours < 24) return relativeFormat.format(-hours, "hour");
      const days = Math.round(hours / 24);
      if (days < 30) return relativeFormat.format(-days, "day");
      return formatDate(value);
    };

    const formatPages = (words: number) => {
      const pages = words / WORDS_PER_PAGE;
      if (pages < 0.6) return t("format.lessThanOnePage");
      // `Intl` tranche l'accord : « 1,5 page » en français, « 1.5 pages » en
      // anglais. Les deux langues ne coupent pas au même endroit.
      return tn("format.pages", pages, { count: pagesFormat.format(pages) });
    };

    return {
      locale,
      setLocale,
      t,
      tn,
      formatDate,
      formatDateTime: (value) => (value ? dateTimeFormat.format(new Date(value)) : EMPTY),
      formatRelative,
      formatNumber: (value) => numberFormat.format(value),
      formatPages,
    };
  }, [locale, setLocale]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n doit être utilisé à l'intérieur d'un LocaleProvider.");
  }
  return context;
}

/** Raccourci pour les composants qui n'ont besoin que de traduire. */
export function useTranslate(): Translate {
  return useI18n().t;
}
