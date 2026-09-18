/**
 * Suivi des erreurs côté navigateur et serveur de rendu.
 *
 * Sans `NEXT_PUBLIC_SENTRY_DSN`, `initSentry()` ne fait rien : aucune requête
 * ne part vers un tiers, comme côté API sans `SENTRY_DSN`.
 *
 * L'expurgation reprend la règle du backend (`app/core/observability.py`) :
 * un rapport d'erreur part chez un tiers, il ne peut pas emporter ce que les
 * gens nous ont confié. Le navigateur ajoute un risque que l'API n'a pas —
 * les URL visitées et les fils d'Ariane (« breadcrumbs ») — et c'est
 * précisément là que transitent les jetons de confirmation d'adresse et de
 * réinitialisation de mot de passe.
 */

import * as Sentry from "@sentry/nextjs";

export const REDACTED = "[expurgé]";

const EMAIL_RE = /[\w.+-]+@[\w-]+\.[\w.-]+/g;
/** Jeton passé dans une URL de confirmation ou de réinitialisation. */
const TOKEN_IN_URL_RE = /(token=)[^&\s]+/gi;
/** Numéro de téléphone international, tel qu'utilisé par le mobile money. */
const PHONE_RE = /\+?\d[\d\s.-]{7,}\d/g;

export function scrubText(value: string): string {
  return value
    .replace(EMAIL_RE, REDACTED)
    .replace(TOKEN_IN_URL_RE, `$1${REDACTED}`)
    .replace(PHONE_RE, REDACTED);
}

/** Expurge récursivement une structure avant envoi. */
export function scrub(value: unknown): unknown {
  if (typeof value === "string") return scrubText(value);
  if (Array.isArray(value)) return value.map(scrub);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, item]) => [key, scrub(item)]),
    );
  }
  return value;
}

export function initSentry(): void {
  const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
  if (!dsn) return;

  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || "development",
    release: process.env.NEXT_PUBLIC_SENTRY_RELEASE || undefined,
    // Le suivi d'erreurs n'a pas besoin de traces, et elles coûtent cher.
    tracesSampleRate: Number(process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE ?? 0),
    // Adresse IP, identifiants de session, valeurs des champs de formulaire :
    // rien de tout cela ne doit accompagner une pile d'appels.
    sendDefaultPii: false,
    beforeSend: (event) => scrub(event) as typeof event,
    beforeBreadcrumb: (breadcrumb) => {
      // Un fil d'Ariane de navigation porte l'URL complète : sur
      // `/verifier-email?token=…`, c'est le jeton lui-même qui partirait.
      return scrub(breadcrumb) as typeof breadcrumb;
    },
  });
}
