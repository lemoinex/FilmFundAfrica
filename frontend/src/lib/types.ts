/** Types partagés avec l'API. Miroir des schémas Pydantic du backend. */

export type UserType = "AUTHOR" | "DIRECTOR" | "PRODUCER" | "INSTITUTION" | "ADMIN";

export type ProjectType =
  | "DOCUMENTARY"
  | "FEATURE_FILM"
  | "SHORT_FILM"
  | "TV_SERIES"
  | "WEB_SERIES"
  | "ANIMATION";

export type ProjectStatus =
  | "IDEA"
  | "DEVELOPMENT"
  | "WRITING"
  | "PRE_PRODUCTION"
  | "PRODUCTION"
  | "POST_PRODUCTION"
  | "COMPLETED";

export type DocumentType =
  | "LOGLINE"
  | "SHORT_SYNOPSIS"
  | "LONG_SYNOPSIS"
  | "INTENT_NOTE"
  | "DIRECTING_NOTE"
  | "TREATMENT"
  | "CHARACTER_SHEET"
  | "ORAL_PITCH"
  | "WRITTEN_PITCH"
  | "SERIES_BIBLE"
  | "SCREENPLAY";

export type DocumentStatus = "DRAFT" | "IN_REVIEW" | "FINAL";

export type RefineAction = "IMPROVE" | "SHORTEN" | "EXPAND" | "CORRECT";

export interface Profile {
  first_name: string;
  last_name: string;
  country?: string | null;
  city?: string | null;
  profession?: string | null;
  photo_url?: string | null;
  bio?: string | null;
  preferred_locale: string;
}

export interface User {
  id: string;
  email: string;
  user_type: UserType;
  is_active: boolean;
  is_verified: boolean;
  ai_credits_remaining: number;
  created_at: string;
  profile?: Profile | null;
  plan_code?: "FREE" | "PRO_AUTHOR" | "PRODUCER" | null;
  /** Faux en bêta interne pour un administrateur : aucun quota ne lui est opposé. */
  commercial_rules_apply?: boolean;
  /** L'offre inclut-elle l'analyse de compatibilité ? La recherche reste ouverte à tous. */
  allows_matching?: boolean;
  /** Faux pendant la bêta privée : aucune souscription possible, pour personne. */
  subscription_open?: boolean;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Character {
  id: string;
  project_id: string;
  name: string;
  role?: string | null;
  age?: string | null;
  description?: string | null;
  arc?: string | null;
  sort_order: number;
}

export interface Project {
  id: string;
  user_id: string;
  title: string;
  project_type: ProjectType;
  genre?: string | null;
  country?: string | null;
  language: string;
  duration?: number | null;
  logline?: string | null;
  short_synopsis?: string | null;
  long_synopsis?: string | null;
  theme?: string | null;
  target_audience?: string | null;
  concept?: string | null;
  stakes?: string | null;
  director_vision?: string | null;
  objectives?: string | null;
  status: ProjectStatus;
  readiness_score?: number | null;
  created_at: string;
  updated_at: string;
  characters: Character[];
}

export interface ProjectSummary {
  id: string;
  title: string;
  project_type: ProjectType;
  genre?: string | null;
  status: ProjectStatus;
  readiness_score?: number | null;
  updated_at: string;
  document_count: number;
}

export interface ProjectDocument {
  id: string;
  project_id: string;
  document_type: DocumentType;
  title: string;
  content: string;
  status: DocumentStatus;
  current_version: number;
  word_count: number;
  /** Langue de rédaction du document, indépendante de celle de l'interface. */
  language: string;
  created_at: string;
  updated_at: string;
}

export type DocumentSummary = Omit<ProjectDocument, "content" | "created_at">;

export interface DocumentVersion {
  id: string;
  document_id: string;
  version_number: number;
  word_count: number;
  origin: string;
  prompt_version?: string | null;
  ai_model?: string | null;
  note?: string | null;
  created_at: string;
}

export interface GenerationResult {
  document: ProjectDocument;
  credits_consumed: number;
  credits_remaining: number;
  provider: string;
  model: string;
  prompt_version: string;
  latency_ms: number;
  passes: number;
  missing_information: string[];
}

export type CandidateStatus = "PENDING" | "APPROVED" | "REJECTED";

/** Dispositif repéré par la veille, en attente de relecture humaine. */
export interface OpportunityCandidate {
  id: string;
  name: string;
  source_url: string;
  source_name: string;
  status: CandidateStatus;
  payload: Record<string, unknown>;
  review_note: string | null;
  reviewed_at: string | null;
  opportunity_id: string | null;
  last_seen_at: string | null;
  created_at: string;
}

export type PlanCode = "FREE" | "PRO_AUTHOR" | "PRODUCER";
export type SubscriptionStatus = "ACTIVE" | "CANCELLED" | "EXPIRED";
export type PaymentStatus = "PENDING" | "SUCCEEDED" | "FAILED" | "CANCELLED" | "REFUNDED";

export interface Plan {
  id: string;
  code: PlanCode;
  name: string;
  description: string;
  price_amount: number;
  price_currency: string;
  billing_period: string;
  max_projects: number;
  monthly_ai_credits: number;
  allows_export: boolean;
  allows_matching: boolean;
  allows_collaboration: boolean;
  allows_advanced_budget: boolean;
  sort_order: number;
}

export interface SubscriptionState {
  plan: Plan;
  status: SubscriptionStatus;
  started_at: string | null;
  current_period_end: string | null;
  cancelled_at: string | null;
  /** Vrai tant que la période payée court, résiliation comprise. */
  is_active: boolean;
  /** Faux dès que l'abonnement est résilié. */
  is_renewing: boolean;
  ai_credits_remaining: number;
}

export interface Payment {
  id: string;
  provider: string;
  provider_reference: string;
  status: PaymentStatus;
  amount: number;
  currency: string;
  phone_number: string | null;
  checkout_url: string | null;
  failure_reason: string | null;
  paid_at: string | null;
  created_at: string;
}

export interface CheckoutResponse {
  payment: Payment;
  instructions: string | null;
}

export type BudgetCategory =
  | "DEVELOPMENT"
  | "PRE_PRODUCTION"
  | "PRODUCTION"
  | "POST_PRODUCTION"
  | "DISTRIBUTION";

export type FundingSourceType =
  | "PRODUCER"
  | "PUBLIC_FUND"
  | "TELEVISION"
  | "COPRODUCER"
  | "INVESTOR"
  | "SPONSOR"
  | "OTHER";

export interface BudgetItem {
  id: string;
  category: BudgetCategory;
  label: string;
  quantity: number;
  unit: string | null;
  unit_price: number;
  /** Toujours calculé côté serveur : quantité × prix unitaire. */
  amount: number;
  sort_order: number;
}

export interface CategoryTotal {
  category: BudgetCategory;
  amount: number;
  item_count: number;
  share: number;
}

export interface Budget {
  id: string;
  project_id: string;
  currency: string;
  total_amount: number;
  notes: string | null;
  items: BudgetItem[];
  totals_by_category: CategoryTotal[];
  updated_at: string;
}

export interface FundingPlanLine {
  id: string;
  source_type: FundingSourceType;
  source_name: string | null;
  amount: number;
  is_secured: boolean;
  expected_date: string | null;
}

export interface FundingPlan {
  currency: string;
  total_budget: number;
  secured_amount: number;
  identified_amount: number;
  sought_amount: number;
  funded_percentage: number;
  uncovered_amount: number;
  lines: FundingPlanLine[];
}

export interface SchedulePhase {
  id: string;
  phase: BudgetCategory;
  start_date: string | null;
  end_date: string | null;
  notes: string | null;
}

export type JobStatus =
  | "QUEUED"
  | "RUNNING"
  | "SUCCEEDED"
  | "FAILED"
  /** Arrêtée à la demande. Distinct d'un échec : personne n'a rien raté. */
  | "CANCELLED";

/**
 * Une génération demandée. L'API répond par cette tâche plutôt que d'attendre
 * la fin : un scénario long enchaîne plusieurs appels au fournisseur et
 * dépasserait le délai d'une requête HTTP.
 */
export interface GenerationJob {
  id: string;
  project_id: string;
  document_id: string | null;
  kind: "GENERATE_DOCUMENT" | "REFINE_DOCUMENT" | "RUN_AGENT_CHAIN";
  /** Nul pour un passage de la chaîne, qui ne vise aucun document. */
  document_type: DocumentType | null;
  status: JobStatus;
  total_passes: number;
  completed_passes: number;
  credits_reserved: number;
  error_code: string | null;
  error_message: string | null;
  /** La forme dépend de `kind`. */
  result: GenerationResult | AgentChainResult | null;
  /** Renseigné dès qu'un arrêt est demandé, avant même qu'il prenne effet. */
  cancel_requested_at: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

// ---------------------------------------------------------------------------
// Dossier construit par la chaîne d'agents

export type AgentRole =
  | "DEVELOPMENT"
  | "SCREENWRITER"
  | "DIRECTOR"
  | "PRODUCER"
  | "FINANCING"
  | "IMPACT"
  | "CONSISTENCY_VALIDATOR"
  | "FUNDING_PACKAGE_VALIDATOR";

export type Severity = "CRITICAL" | "MAJOR" | "MINOR" | "PASS";

export type ValidationVerdict =
  | "PASS"
  | "PASS_WITH_WARNINGS"
  | "REQUIRES_CORRECTION"
  | "BLOCKED";

export interface AgentChainResult {
  run_id: string;
  verdict: ValidationVerdict | null;
  /** Ce que le verdict autorise — distinct du succès technique de la tâche. */
  exportable: boolean;
  rounds: number;
  stalled: boolean;
  exhausted: boolean;
  steps: number;
  open_findings: number;
}

export interface DossierFinding {
  id: string;
  severity: Severity;
  element: string;
  description: string;
  /** Agent capable de corriger. Sans lui, le constat n'a pas de destinataire. */
  owner: AgentRole | null;
  suggested_correction: string | null;
  /** Renseigné quand le constat a été levé : daté, pas effacé. */
  resolved_at: string | null;
  created_at: string;
}

export interface DossierModification {
  id: string;
  agent: AgentRole;
  element: string;
  reason: string;
  impact: string;
  validation_status: ValidationVerdict | null;
  created_at: string;
}

export interface AgentStep {
  id: string;
  sequence: number;
  agent: AgentRole;
  agent_version: string;
  analysis: string;
  rationale: string;
  next_agent_instructions: string;
  verdict: ValidationVerdict | null;
  changeset: Record<string, unknown>;
  created_at: string;
}

export interface AgentRun {
  id: string;
  verdict: ValidationVerdict | null;
  rounds: number;
  exhausted: boolean;
  stalled: boolean;
  created_at: string;
  finished_at: string | null;
}

export interface AgentRunDetail extends AgentRun {
  steps: AgentStep[];
}

export interface Dossier {
  id: string;
  project_id: string;
  project_identity: Record<string, unknown>;
  logline: Record<string, unknown> | null;
  concept: Record<string, unknown>;
  synopsis: Record<string, unknown>;
  characters: Record<string, unknown>[];
  screenplay: Record<string, unknown>;
  director_vision: Record<string, unknown>;
  production_plan: Record<string, unknown>;
  budget: Record<string, unknown>;
  financing_plan: Record<string, unknown>;
  cultural_analysis: Record<string, unknown>;
  impact_analysis: Record<string, unknown>;
  final_documents: string[];
  updated_at: string;
}

export interface DossierStatus {
  project_id: string;
  verdict: ValidationVerdict | null;
  /** Seul critère d'export : ni l'absence d'erreur ni le nombre de passages. */
  exportable: boolean;
  open_findings: number;
  blocking_findings: number;
  last_run_at: string | null;
  runs: number;
}

export interface ScoreCriterion {
  key: string;
  label: string;
  weight: number;
  earned: number;
  detail: string;
}

export interface ReadinessScore {
  total: number;
  criteria: ScoreCriterion[];
  improvements: string[];
  computed_at: string;
}

export interface DocumentTypeInfo {
  document_type: DocumentType;
  label: string;
  prompt_name: string;
  prompt_version: string;
  outline: string[];
  target_pages: [number, number] | null;
  depends_on: DocumentType[];
}

/* ------------------------------------------------------------------ */
/* Funding Intelligence                                                */
/* ------------------------------------------------------------------ */
export type FundingCategory =
  | "FUND"
  | "GRANT"
  | "RESIDENCY"
  | "FESTIVAL"
  | "LAB"
  | "WORKSHOP"
  | "COPRODUCTION"
  | "BURSARY"
  | "PITCHING_FORUM";

export type FundingStatus = "OPEN" | "CLOSED" | "UPCOMING" | "UNVERIFIED";

export type MatchState = "met" | "unmet" | "unknown";

export interface FundingRequirement {
  id: string;
  opportunity_id: string;
  label: string;
  description?: string | null;
  is_mandatory: boolean;
  required_document_type?: DocumentType | null;
}

export interface OpportunitySummary {
  id: string;
  name: string;
  organization: string;
  category: FundingCategory;
  country?: string | null;
  amount_label?: string | null;
  deadline?: string | null;
  days_left?: number | null;
  status: FundingStatus;
  is_demo: boolean;
  /** Traçabilité : jamais affichée sans ces deux informations. */
  source_name?: string | null;
  source_url?: string | null;
  last_verified_at?: string | null;
}

export interface Opportunity {
  id: string;
  name: string;
  organization: string;
  description: string;
  website?: string | null;
  country?: string | null;
  eligible_countries: string[];
  project_types: string[];
  genres: string[];
  languages: string[];
  category: FundingCategory;
  minimum_budget?: number | null;
  maximum_budget?: number | null;
  currency: string;
  deadline?: string | null;
  opening_date?: string | null;
  application_url?: string | null;
  requirements: string;
  status: FundingStatus;
  source_name?: string | null;
  source_url?: string | null;
  last_verified_at?: string | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  requirement_items: FundingRequirement[];
}

export interface OpportunityPage {
  items: OpportunitySummary[];
  total: number;
  page: number;
  page_size: number;
  facets: Record<string, string[]>;
}

export interface MatchCriterion {
  key: string;
  label: string;
  weight: number;
  earned: number;
  state: MatchState;
  detail: string;
  blocking: boolean;
}

export interface MatchResult {
  opportunity: OpportunitySummary;
  compatibility: number;
  eligible: boolean;
  assessed_ratio: number;
  criteria: MatchCriterion[];
  met_conditions: string[];
  missing_conditions: string[];
  unknown_conditions: string[];
  required_documents: string[];
  missing_documents: string[];
  computed_at: string;
  has_explanation: boolean;
}

export interface MatchListResponse {
  project_id: string;
  project_title: string;
  total: number;
  results: MatchResult[];
  computed_at: string;
  disclaimer: string;
}

export interface MatchExplanation {
  opportunity_id: string;
  compatibility: number;
  explanation: string;
  credits_consumed: number;
  credits_remaining: number;
  provider: string;
  model: string;
  prompt_version: string;
  disclaimer: string;
}

export interface ScreenplayCapacity {
  pages_per_pass: number;
  max_passes: number;
  max_minutes: number;
  words_per_page: number;
}

export interface DashboardStats {
  projects: number;
  documents_generated: number;
  compatible_opportunities: number;
  upcoming_deadlines: number;
  ai_credits_remaining: number;
}

export interface RecommendedOpportunity {
  id: string;
  name: string;
  organization: string;
  amount_label?: string | null;
  deadline?: string | null;
  compatibility: number;
  is_demo: boolean;
  source_name?: string | null;
  source_url?: string | null;
  last_verified_at?: string | null;
}

export interface NotificationItem {
  id: string;
  title: string;
  body: string;
  notification_type: string;
  link?: string | null;
  is_read: boolean;
  created_at: string;
}

export interface DashboardResponse {
  welcome_name: string;
  stats: DashboardStats;
  projects: ProjectSummary[];
  recommended_opportunities: RecommendedOpportunity[];
  notifications: NotificationItem[];
}

/** Fournisseurs d'IA que l'application sait construire. */
export type AIProviderName = "anthropic" | "openai" | "mock";

/**
 * État d'un fournisseur vu par l'administration.
 *
 * `key_hint` ne contient que les quatre derniers caractères : l'API ne
 * renvoie jamais une clé, même à un administrateur.
 */
export interface AIProviderState {
  name: AIProviderName;
  configured: boolean;
  key_hint: string | null;
  key_source: "database" | "environment" | "unreadable" | "none";
  default_model: string;
  requires_key: boolean;
}

export interface AIConfig {
  active_provider: AIProviderName;
  effective_model: string;
  configured_model: string;
  model_source: "database" | "environment" | "provider_default" | "none";
  providers: AIProviderState[];
}

export interface AIConfigUpdate {
  provider?: AIProviderName;
  model?: string;
  key_provider?: AIProviderName;
  api_key?: string;
}

export interface AIConfigTestResult {
  ok: boolean;
  provider: string;
  model: string;
  detail: string;
  input_tokens: number;
  output_tokens: number;
  latency_ms: number;
}

/** Cycle de vie de la plateforme : bêta interne, puis phase commerciale. */
export interface PlatformStatus {
  mode: "internal" | "public";
  internal: boolean;
  start_date: string;
  target_end_date: string;
}
