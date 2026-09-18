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
