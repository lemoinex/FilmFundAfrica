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

export type JobStatus = "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED";

/**
 * Une génération demandée. L'API répond par cette tâche plutôt que d'attendre
 * la fin : un scénario long enchaîne plusieurs appels au fournisseur et
 * dépasserait le délai d'une requête HTTP.
 */
export interface GenerationJob {
  id: string;
  project_id: string;
  document_id: string | null;
  kind: "GENERATE_DOCUMENT" | "REFINE_DOCUMENT";
  document_type: DocumentType;
  status: JobStatus;
  total_passes: number;
  completed_passes: number;
  credits_reserved: number;
  error_code: string | null;
  error_message: string | null;
  result: GenerationResult | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
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
