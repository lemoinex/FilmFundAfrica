/**
 * Listes d'ordre et de choix, indépendantes de la langue.
 *
 * Les libellés des énumérations vivent désormais dans les catalogues
 * (`src/lib/i18n/fr.ts`, `en.ts`), sous les clés `projectType.*`,
 * `fundingCategory.*`, etc. : `t(\`projectType.${type}\`)`. Ce qui reste ici
 * est l'ordre d'affichage et les valeurs proposées — ni l'un ni l'autre ne
 * change d'une langue à l'autre.
 */

import type { BudgetCategory, DocumentType, FundingCategory, ProjectType } from "./types";

/** Types de projet proposés dans les formulaires et les filtres. */
export const PROJECT_TYPES: ProjectType[] = [
  "DOCUMENTARY",
  "FEATURE_FILM",
  "SHORT_FILM",
  "TV_SERIES",
  "WEB_SERIES",
  "ANIMATION",
];

/** Dispositifs de financement, dans l'ordre d'affichage des filtres. */
export const FUNDING_CATEGORIES: FundingCategory[] = [
  "FUND",
  "GRANT",
  "RESIDENCY",
  "FESTIVAL",
  "LAB",
  "WORKSHOP",
  "COPRODUCTION",
  "BURSARY",
  "PITCHING_FORUM",
];

/** Documents du dossier, dans l'ordre où ils se construisent. */
export const DOCUMENT_TYPES: DocumentType[] = [
  "LOGLINE",
  "SHORT_SYNOPSIS",
  "LONG_SYNOPSIS",
  "INTENT_NOTE",
  "DIRECTING_NOTE",
  "TREATMENT",
  "CHARACTER_SHEET",
  "ORAL_PITCH",
  "WRITTEN_PITCH",
  "SERIES_BIBLE",
  "SCREENPLAY",
];

/** Ordre des phases de production : celui du budget et du calendrier. */
export const BUDGET_CATEGORY_ORDER: BudgetCategory[] = [
  "DEVELOPMENT",
  "PRE_PRODUCTION",
  "PRODUCTION",
  "POST_PRODUCTION",
  "DISTRIBUTION",
];

/** Durées cibles proposées pour un scénario (1 page ≈ 1 minute). */
export const DURATION_PRESETS = [10, 26, 30, 52, 90, 100, 110, 120, 150, 180];
