import type {
  DocumentStatus,
  DocumentType,
  FundingCategory,
  FundingStatus,
  ProjectStatus,
  ProjectType,
  UserType,
} from "./types";

export const PROJECT_TYPE_LABELS: Record<ProjectType, string> = {
  DOCUMENTARY: "Documentaire",
  FEATURE_FILM: "Long métrage",
  SHORT_FILM: "Court métrage",
  TV_SERIES: "Série TV",
  WEB_SERIES: "Web-série",
  ANIMATION: "Animation",
};

export const PROJECT_STATUS_LABELS: Record<ProjectStatus, string> = {
  IDEA: "Idée",
  DEVELOPMENT: "Développement",
  WRITING: "Écriture",
  PRE_PRODUCTION: "Préproduction",
  PRODUCTION: "Production",
  POST_PRODUCTION: "Postproduction",
  COMPLETED: "Terminé",
};

export const USER_TYPE_LABELS: Record<UserType, string> = {
  AUTHOR: "Auteur",
  DIRECTOR: "Réalisateur",
  PRODUCER: "Producteur",
  INSTITUTION: "Institution",
  ADMIN: "Administrateur",
};

export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  LOGLINE: "Logline",
  SHORT_SYNOPSIS: "Synopsis court",
  LONG_SYNOPSIS: "Synopsis long",
  INTENT_NOTE: "Note d'intention",
  DIRECTING_NOTE: "Note de réalisation",
  TREATMENT: "Traitement",
  CHARACTER_SHEET: "Présentation des personnages",
  ORAL_PITCH: "Pitch oral",
  WRITTEN_PITCH: "Pitch écrit",
  SERIES_BIBLE: "Bible du projet",
  SCREENPLAY: "Scénario",
};

export const DOCUMENT_STATUS_LABELS: Record<DocumentStatus, string> = {
  DRAFT: "Brouillon",
  IN_REVIEW: "En relecture",
  FINAL: "Finalisé",
};

export const ORIGIN_LABELS: Record<string, string> = {
  MANUAL: "Édition manuelle",
  AI_GENERATE: "Génération IA",
  AI_IMPROVE: "IA — amélioration",
  AI_SHORTEN: "IA — raccourcissement",
  AI_EXPAND: "IA — développement",
  AI_CORRECT: "IA — correction",
  RESTORE: "Restauration",
};

export const FUNDING_CATEGORY_LABELS: Record<FundingCategory, string> = {
  FUND: "Fonds",
  GRANT: "Subvention",
  RESIDENCY: "Résidence",
  FESTIVAL: "Festival",
  LAB: "Laboratoire",
  WORKSHOP: "Atelier",
  COPRODUCTION: "Coproduction",
  BURSARY: "Bourse",
  PITCHING_FORUM: "Forum de pitch",
};

export const FUNDING_STATUS_LABELS: Record<FundingStatus, string> = {
  OPEN: "Ouvert",
  CLOSED: "Clos",
  UPCOMING: "À venir",
  UNVERIFIED: "Non vérifié",
};

/** Durées cibles proposées pour un scénario (1 page ≈ 1 minute). */
export const DURATION_PRESETS = [10, 26, 30, 52, 90, 100, 110, 120, 150, 180];
