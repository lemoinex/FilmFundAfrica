/**
 * Client HTTP de l'API FilmFund Africa.
 *
 * Les jetons sont conservés côté navigateur (localStorage) : le backend est
 * sans état. Un 401 déclenche une tentative de rafraîchissement, puis une
 * redirection vers la page de connexion si elle échoue.
 */

import { currentLocale, tr } from "./i18n/translate";
import type {
  AIConfig,
  AIConfigTestResult,
  AIConfigUpdate,
  AgentRun,
  AgentRunDetail,
  AuthResponse,
  Budget,
  CheckoutResponse,
  BudgetCategory,
  BudgetItem,
  Character,
  DashboardResponse,
  DocumentSummary,
  DocumentType,
  DocumentTypeInfo,
  DocumentVersion,
  Dossier,
  DossierFinding,
  DossierModification,
  DossierStatus,
  FundingPlan,
  FundingPlanLine,
  FundingSourceType,
  GenerationJob,
  GenerationResult,
  MatchExplanation,
  MatchListResponse,
  NotificationItem,
  Opportunity,
  OpportunityCandidate,
  OpportunityPage,
  Payment,
  Plan,
  Project,
  ProjectDocument,
  ProjectSummary,
  ReadinessScore,
  RefineAction,
  SchedulePhase,
  SubscriptionState,
  ScreenplayCapacity,
  User,
} from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

const ACCESS_KEY = "ffa.access_token";
const REFRESH_KEY = "ffa.refresh_token";

export const tokenStore = {
  get access() {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh: string) {
    window.localStorage.setItem(ACCESS_KEY, access);
    window.localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    window.localStorage.removeItem(ACCESS_KEY);
    window.localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  code?: string;
  fields?: { field: string; message: string }[];

  constructor(
    message: string,
    status: number,
    code?: string,
    fields?: { field: string; message: string }[],
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  auth?: boolean;
  raw?: boolean;
}

async function refreshAccessToken(): Promise<boolean> {
  const refresh = tokenStore.refresh;
  if (!refresh) return false;

  const response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept-Language": currentLocale() },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!response.ok) return false;

  const data = await response.json();
  tokenStore.set(data.access_token, data.refresh_token ?? refresh);
  return true;
}

async function toApiError(response: Response): Promise<ApiError> {
  let detail = tr("api.httpError", { status: response.status });
  let code: string | undefined;
  let fields: { field: string; message: string }[] | undefined;
  try {
    const data = await response.json();
    detail = data.detail ?? detail;
    code = data.code;
    fields = data.errors;
    if (fields?.length && !data.detail) {
      detail = fields.map((f) => f.message).join(" · ");
    }
  } catch {
    /* réponse sans corps JSON */
  }
  return new ApiError(detail, response.status, code, fields);
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, auth = true, raw = false, headers, ...rest } = options;

  const send = async (): Promise<Response> => {
    const finalHeaders: Record<string, string> = {
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      // La langue choisie ici prime sur celle du navigateur : quelqu'un peut
      // lire l'interface en anglais depuis un navigateur configuré en
      // français, et l'API doit lui répondre dans la langue qu'il lit.
      "Accept-Language": currentLocale(),
      ...((headers as Record<string, string>) ?? {}),
    };
    if (auth && tokenStore.access) {
      finalHeaders.Authorization = `Bearer ${tokenStore.access}`;
    }
    return fetch(`${API_URL}${path}`, {
      ...rest,
      headers: finalHeaders,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let response = await send();

  if (response.status === 401 && auth && tokenStore.refresh) {
    if (await refreshAccessToken()) {
      response = await send();
    }
  }

  if (response.status === 401 && auth) {
    tokenStore.clear();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/connexion")) {
      window.location.href = "/connexion";
    }
    throw new ApiError(tr("api.sessionExpired"), 401, "session_expired");
  }

  if (!response.ok) throw await toApiError(response);
  if (raw) return response as unknown as T;
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/* ------------------------------------------------------------------ */
/* Authentification                                                    */
/* ------------------------------------------------------------------ */
export const authApi = {
  register: (payload: {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    user_type: string;
    country?: string;
    city?: string;
    profession?: string;
  }) =>
    // L'inscription n'ouvre pas de session : elle envoie un lien de
    // confirmation, et répond la même chose que l'adresse soit libre ou prise.
    request<{ detail: string }>("/api/v1/auth/register", {
      method: "POST",
      body: payload,
      auth: false,
    }),

  verifyEmail: (token: string) =>
    request<AuthResponse>("/api/v1/auth/verify-email", {
      method: "POST",
      body: { token },
      auth: false,
    }),

  resendVerification: (email: string) =>
    request<{ detail: string }>("/api/v1/auth/resend-verification", {
      method: "POST",
      body: { email },
      auth: false,
    }),

  login: (email: string, password: string) =>
    request<AuthResponse>("/api/v1/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    }),

  me: () => request<User>("/api/v1/auth/me"),

  forgotPassword: (email: string) =>
    request<{ detail: string }>("/api/v1/auth/forgot-password", {
      method: "POST",
      body: { email },
      auth: false,
    }),

  resetPassword: (token: string, newPassword: string) =>
    request<{ detail: string }>("/api/v1/auth/reset-password", {
      method: "POST",
      body: { token, new_password: newPassword },
      auth: false,
    }),

  updateProfile: (payload: Record<string, unknown>) =>
    request<User>("/api/v1/users/me/profile", { method: "PUT", body: payload }),
};

/* ------------------------------------------------------------------ */
/* Projets                                                             */
/* ------------------------------------------------------------------ */
export const projectApi = {
  list: (search?: string) =>
    request<ProjectSummary[]>(`/api/v1/projects${search ? `?search=${encodeURIComponent(search)}` : ""}`),

  get: (id: string) => request<Project>(`/api/v1/projects/${id}`),

  create: (payload: Record<string, unknown>) =>
    request<Project>("/api/v1/projects", { method: "POST", body: payload }),

  update: (id: string, payload: Record<string, unknown>) =>
    request<Project>(`/api/v1/projects/${id}`, { method: "PUT", body: payload }),

  remove: (id: string) =>
    request<{ detail: string }>(`/api/v1/projects/${id}`, { method: "DELETE" }),

  score: (id: string) => request<ReadinessScore>(`/api/v1/projects/${id}/score`),

  addCharacter: (projectId: string, payload: Record<string, unknown>) =>
    request<Character>(`/api/v1/projects/${projectId}/characters`, {
      method: "POST",
      body: payload,
    }),

  updateCharacter: (projectId: string, characterId: string, payload: Record<string, unknown>) =>
    request<Character>(`/api/v1/projects/${projectId}/characters/${characterId}`, {
      method: "PUT",
      body: payload,
    }),

  removeCharacter: (projectId: string, characterId: string) =>
    request<{ detail: string }>(`/api/v1/projects/${projectId}/characters/${characterId}`, {
      method: "DELETE",
    }),
};

/* ------------------------------------------------------------------ */
/* AI Writer                                                           */
/* ------------------------------------------------------------------ */
export const documentApi = {
  types: () => request<DocumentTypeInfo[]>("/api/v1/documents/types"),

  /** Découpage réel des scénarios longs, tel que le serveur le calcule. */
  screenplayCapacity: () =>
    request<ScreenplayCapacity>("/api/v1/documents/screenplay-capacity"),

  list: (projectId: string) =>
    request<DocumentSummary[]>(`/api/v1/projects/${projectId}/documents`),

  get: (projectId: string, documentId: string) =>
    request<ProjectDocument>(`/api/v1/projects/${projectId}/documents/${documentId}`),

  generate: (
    projectId: string,
    documentType: DocumentType,
    payload: {
      language?: string;
      target_duration_minutes?: number | null;
      additional_instructions?: string | null;
      overwrite?: boolean;
    } = {},
  ) =>
    request<GenerationJob>(
      `/api/v1/projects/${projectId}/documents/${documentType}/generate`,
      // Pas de langue imposée ici : un « fr » codé en dur rendait le choix de
      // l'appelant inopérant et produisait des documents français pour un
      // dossier anglais. Sans valeur, le serveur applique sa propre défaut.
      { method: "POST", body: { overwrite: true, ...payload } },
    ),

  save: (
    projectId: string,
    documentId: string,
    payload: { content: string; title?: string; status?: string; note?: string },
  ) =>
    request<ProjectDocument>(`/api/v1/projects/${projectId}/documents/${documentId}`, {
      method: "PUT",
      body: payload,
    }),

  refine: (projectId: string, documentId: string, action: RefineAction, instructions?: string) =>
    request<GenerationJob>(
      `/api/v1/projects/${projectId}/documents/${documentId}/refine`,
      { method: "POST", body: { action, instructions: instructions ?? null } },
    ),

  remove: (projectId: string, documentId: string) =>
    request<{ detail: string }>(`/api/v1/projects/${projectId}/documents/${documentId}`, {
      method: "DELETE",
    }),

  versions: (projectId: string, documentId: string) =>
    request<DocumentVersion[]>(
      `/api/v1/projects/${projectId}/documents/${documentId}/versions`,
    ),

  version: (projectId: string, documentId: string, versionNumber: number) =>
    request<DocumentVersion & { content: string }>(
      `/api/v1/projects/${projectId}/documents/${documentId}/versions/${versionNumber}`,
    ),

  restore: (projectId: string, documentId: string, versionNumber: number) =>
    request<ProjectDocument>(
      `/api/v1/projects/${projectId}/documents/${documentId}/versions/${versionNumber}/restore`,
      { method: "POST" },
    ),
};

/* ------------------------------------------------------------------ */
/* Funding Intelligence                                                */
/* ------------------------------------------------------------------ */
export interface FundingSearchParams extends Record<string, unknown> {
  query?: string;
  country?: string;
  project_type?: string;
  genre?: string;
  language?: string;
  category?: string;
  min_amount?: number;
  max_amount?: number;
  deadline_before?: string;
  include_closed?: boolean;
  sort?: string;
  page?: number;
  page_size?: number;
}

function toQueryString(params: Record<string, unknown>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

export const fundingApi = {
  search: (params: FundingSearchParams = {}) =>
    request<OpportunityPage>(`/api/v1/funding${toQueryString(params)}`),

  get: (id: string) => request<Opportunity>(`/api/v1/funding/${id}`),

  /** Calcul déterministe : gratuit, aucun crédit consommé. */
  computeMatches: (projectId: string) =>
    request<MatchListResponse>(`/api/v1/projects/${projectId}/match-funding`, {
      method: "POST",
    }),

  matches: (projectId: string) =>
    request<MatchListResponse>(`/api/v1/projects/${projectId}/matches`),

  /** Explication rédigée par l'IA : consomme 1 crédit à la première demande. */
  explain: (projectId: string, opportunityId: string, refresh = false) =>
    request<MatchExplanation>(
      `/api/v1/projects/${projectId}/matches/${opportunityId}/explain${refresh ? "?refresh=true" : ""}`,
      { method: "POST" },
    ),
};

/* ------------------------------------------------------------------ */
/* Administration des dispositifs                                      */
/* ------------------------------------------------------------------ */
export const adminFundingApi = {
  list: (query?: string, page = 1) =>
    request<OpportunityPage>(
      `/api/v1/admin/funding${toQueryString({ query, page, page_size: 50 })}`,
    ),

  get: (id: string) => request<Opportunity>(`/api/v1/admin/funding/${id}`),

  create: (payload: Record<string, unknown>) =>
    request<Opportunity>("/api/v1/admin/funding", { method: "POST", body: payload }),

  update: (id: string, payload: Record<string, unknown>) =>
    request<Opportunity>(`/api/v1/admin/funding/${id}`, { method: "PUT", body: payload }),

  verify: (id: string, status: string) =>
    request<Opportunity>(`/api/v1/admin/funding/${id}/verify?new_status=${status}`, {
      method: "POST",
    }),

  remove: (id: string) =>
    request<{ detail: string }>(`/api/v1/admin/funding/${id}`, { method: "DELETE" }),

  addRequirement: (id: string, payload: Record<string, unknown>) =>
    request<Opportunity>(`/api/v1/admin/funding/${id}/requirements`, {
      method: "POST",
      body: payload,
    }),

  removeRequirement: (id: string, requirementId: string) =>
    request<Opportunity>(`/api/v1/admin/funding/${id}/requirements/${requirementId}`, {
      method: "DELETE",
    }),
};

/* ------------------------------------------------------------------ */
/* Tableau de bord, notifications, export                              */
/* ------------------------------------------------------------------ */
export const dashboardApi = {
  get: () => request<DashboardResponse>("/api/v1/dashboard"),
  notifications: () => request<NotificationItem[]>("/api/v1/notifications"),
  markRead: (id: string) =>
    request<{ detail: string }>(`/api/v1/notifications/${id}/read`, { method: "POST" }),
};

export const candidateApi = {
  /** File de validation de la veille : rien n'est publié sans relecture. */
  list: (status?: string) =>
    request<OpportunityCandidate[]>(
      `/api/v1/admin/candidates${status ? `?status=${status}` : ""}`,
    ),

  approve: (candidateId: string, corrections: Record<string, unknown> = {}) =>
    request<{ detail: string }>(`/api/v1/admin/candidates/${candidateId}/approve`, {
      method: "POST",
      body: corrections,
    }),

  reject: (candidateId: string, note?: string) =>
    request<OpportunityCandidate>(`/api/v1/admin/candidates/${candidateId}/reject`, {
      method: "POST",
      body: { note: note ?? null },
    }),
};

export const aiConfigApi = {
  /** Configuration effective du fournisseur d'IA. Ne renvoie jamais de clé. */
  get: () => request<AIConfig>("/api/v1/admin/ai/config"),

  update: (payload: AIConfigUpdate) =>
    request<AIConfig>("/api/v1/admin/ai/config", { method: "PUT", body: payload }),

  /** Appel réel et facturé : la seule preuve qu'une clé fonctionne. */
  test: () => request<AIConfigTestResult>("/api/v1/admin/ai/test", { method: "POST" }),
};

export const billingApi = {
  plans: () => request<Plan[]>("/api/v1/billing/plans"),

  subscription: () => request<SubscriptionState>("/api/v1/billing/subscription"),

  payments: () => request<Payment[]>("/api/v1/billing/payments"),

  /** Ouvre un paiement : rien n'est accordé tant qu'il n'a pas abouti. */
  checkout: (planCode: string, phoneNumber?: string) =>
    request<CheckoutResponse>("/api/v1/billing/checkout", {
      method: "POST",
      body: { plan_code: planCode, phone_number: phoneNumber ?? null },
    }),

  cancel: () =>
    request<{ detail: string }>("/api/v1/billing/cancel", { method: "POST" }),

  /** Réservée au prestataire simulé, en développement. */
  simulate: (reference: string, succeed = true) =>
    request<{ detail: string }>(
      `/api/v1/billing/simulate/${reference}?succeed=${succeed}`,
      { method: "POST" },
    ),
};

export const budgetApi = {
  get: (projectId: string) => request<Budget>(`/api/v1/projects/${projectId}/budget`),

  /** Installe les postes attendus pour ce type de projet, sans montants. */
  generate: (projectId: string, replace = false) =>
    request<Budget>(`/api/v1/projects/${projectId}/budget/generate`, {
      method: "POST",
      body: { replace },
    }),

  updateBudget: (projectId: string, payload: { currency?: string; notes?: string }) =>
    request<Budget>(`/api/v1/projects/${projectId}/budget`, { method: "PUT", body: payload }),

  addItem: (
    projectId: string,
    payload: {
      category: BudgetCategory;
      label: string;
      quantity?: number;
      unit?: string | null;
      unit_price?: number;
    },
  ) =>
    request<BudgetItem>(`/api/v1/projects/${projectId}/budget/items`, {
      method: "POST",
      body: payload,
    }),

  updateItem: (
    projectId: string,
    itemId: string,
    payload: Partial<{
      category: BudgetCategory;
      label: string;
      quantity: number;
      unit: string | null;
      unit_price: number;
    }>,
  ) =>
    request<BudgetItem>(`/api/v1/projects/${projectId}/budget/items/${itemId}`, {
      method: "PUT",
      body: payload,
    }),

  deleteItem: (projectId: string, itemId: string) =>
    request<{ detail: string }>(`/api/v1/projects/${projectId}/budget/items/${itemId}`, {
      method: "DELETE",
    }),

  plan: (projectId: string) =>
    request<FundingPlan>(`/api/v1/projects/${projectId}/funding-plan`),

  addPlanLine: (
    projectId: string,
    payload: {
      source_type: FundingSourceType;
      source_name?: string | null;
      amount?: number;
      is_secured?: boolean;
      expected_date?: string | null;
    },
  ) =>
    request<FundingPlanLine>(`/api/v1/projects/${projectId}/funding-plan/lines`, {
      method: "POST",
      body: payload,
    }),

  updatePlanLine: (
    projectId: string,
    lineId: string,
    payload: Partial<{
      source_type: FundingSourceType;
      source_name: string | null;
      amount: number;
      is_secured: boolean;
      expected_date: string | null;
    }>,
  ) =>
    request<FundingPlanLine>(`/api/v1/projects/${projectId}/funding-plan/lines/${lineId}`, {
      method: "PUT",
      body: payload,
    }),

  deletePlanLine: (projectId: string, lineId: string) =>
    request<{ detail: string }>(
      `/api/v1/projects/${projectId}/funding-plan/lines/${lineId}`,
      { method: "DELETE" },
    ),

  schedule: (projectId: string) =>
    request<SchedulePhase[]>(`/api/v1/projects/${projectId}/schedule`),

  setPhase: (
    projectId: string,
    payload: {
      phase: BudgetCategory;
      start_date?: string | null;
      end_date?: string | null;
      notes?: string | null;
    },
  ) =>
    request<SchedulePhase>(`/api/v1/projects/${projectId}/schedule`, {
      method: "PUT",
      body: payload,
    }),
};

export const jobApi = {
  get: (jobId: string) => request<GenerationJob>(`/api/v1/jobs/${jobId}`),

  listForProject: (projectId: string) =>
    request<GenerationJob[]>(`/api/v1/projects/${projectId}/jobs`),
};

/** Première attente avant d'interroger une tâche, en millisecondes. */
const JOB_POLL_START_MS = 1000;
/** Plafond de l'attente : au-delà, l'écran paraîtrait figé. */
const JOB_POLL_MAX_MS = 5000;

/**
 * Suit une génération jusqu'à son état terminal et renvoie son résultat.
 *
 * L'attente entre deux interrogations s'allonge progressivement : une logline
 * est prête en quelques secondes, un scénario de 110 pages demande plusieurs
 * minutes — inutile d'interroger le serveur toutes les secondes pendant tout
 * ce temps.
 */
export async function waitForJob<T = GenerationResult>(
  job: GenerationJob,
  options: { onProgress?: (job: GenerationJob) => void; signal?: AbortSignal } = {},
): Promise<T> {
  let current = job;
  let delay = JOB_POLL_START_MS;
  options.onProgress?.(current);

  while (current.status === "QUEUED" || current.status === "RUNNING") {
    await new Promise((resolve) => setTimeout(resolve, delay));
    delay = Math.min(Math.round(delay * 1.4), JOB_POLL_MAX_MS);
    if (options.signal?.aborted) {
      throw new ApiError(tr("api.jobTrackingAborted"), 0, "job_tracking_aborted");
    }
    current = await jobApi.get(current.id);
    options.onProgress?.(current);
  }

  if (current.status === "FAILED" || current.result === null) {
    throw new ApiError(
      current.error_message ?? tr("api.generationFailed"),
      500,
      current.error_code ?? "job_failed",
    );
  }
  return current.result as T;
}

export const dossierApi = {
  /** Lance un passage. Répond par une tâche : huit appels ne tiennent pas
   *  dans une requête HTTP. */
  run: (projectId: string) =>
    request<GenerationJob>(`/api/v1/projects/${projectId}/dossier/run`, { method: "POST" }),

  get: (projectId: string) => request<Dossier>(`/api/v1/projects/${projectId}/dossier`),

  status: (projectId: string) =>
    request<DossierStatus>(`/api/v1/projects/${projectId}/dossier/status`),

  findings: (projectId: string, includeResolved = false) =>
    request<DossierFinding[]>(
      `/api/v1/projects/${projectId}/dossier/findings` +
        (includeResolved ? "?include_resolved=true" : ""),
    ),

  modifications: (projectId: string) =>
    request<DossierModification[]>(`/api/v1/projects/${projectId}/dossier/modifications`),

  runs: (projectId: string) =>
    request<AgentRun[]>(`/api/v1/projects/${projectId}/dossier/runs`),

  run_detail: (projectId: string, runId: string) =>
    request<AgentRunDetail>(`/api/v1/projects/${projectId}/dossier/runs/${runId}`),
};

/** Télécharge un export en réutilisant le jeton d'accès courant. */
export async function downloadExport(path: string, fallbackName: string): Promise<void> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      "Accept-Language": currentLocale(),
      ...(tokenStore.access ? { Authorization: `Bearer ${tokenStore.access}` } : {}),
    },
  });
  if (!response.ok) throw await toApiError(response);

  const disposition = response.headers.get("Content-Disposition");
  const match = disposition?.match(/filename="?([^"]+)"?/);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = match?.[1] ?? fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
