// === Auth ===
export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  company: Company;
}

export interface Company {
  id: string;
  name: string;
  logo_url: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
  /** Seconds until the access token expires. Used by the client to schedule proactive refresh. */
  expires_in: number;
}

export interface RefreshResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface MeResponse {
  user: User;
  /** Seconds until the current session cookie expires. */
  expires_in: number;
}

// === Team / Invites ===
export interface TeamMember {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
}

export interface TeamInvite {
  id: string;
  email: string;
  role: string;
  invited_by_user_id: string | null;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface InvitePreview {
  email: string;
  company_name: string;
  expires_at: string;
}

// === Jobs ===
export interface InterviewConfig {
  num_questions: number;
  style: "quick" | "standard" | "deep";
}

export interface CustomQuestion {
  question: string;
  category: string;
}

/** Per-job screening policy. Determines whether parsed applicants are
 *  auto-invited to interview, gated through HR review, or all queued for
 *  manual approval. */
export type ScreeningMode = "auto_all" | "hybrid_threshold" | "manual_all";

export interface JobPosting {
  id: string;
  title: string;
  description: string;
  department: string | null;
  location: string | null;
  employment_type: string;
  required_skills: string[];
  custom_questions: CustomQuestion[] | null;
  interview_config: InterviewConfig;
  status: "active" | "paused" | "archived";
  interview_link_token: string;
  candidate_count: number;
  avg_score: number | null;
  created_at: string;
  auto_send_status_emails: boolean;
  screening_mode: ScreeningMode;
  /** Hybrid mode: scores at or above this auto-invite the candidate. */
  auto_invite_threshold: number;
  /** Hybrid mode: scores below this still go to HR review (no auto-reject in v1). */
  review_threshold: number;
}

// === Candidates ===
/** Backend canonical candidate status values. Keep in sync with
 *  `backend/app/models/candidate.py`. */
export type CandidateStatus =
  | "applied"
  | "processing"
  | "ready"
  | "review_pending"
  | "in_progress"
  | "completed"
  | "shortlisted"
  | "rejected"
  | "error";

export type PreScreenDecision = "auto_invite" | "review" | "reject" | "error";

/**
 * Server-Sent Event payload for real-time candidate-status updates.
 *
 * Emitted by both the background screening pipeline (`actor_user_id` is
 * `null` — “system”) and by manual HR actions (`actor_user_id` is the
 * acting user; `actor_name` is the display name for toasts).
 *
 * The frontend uses `actor_user_id` to suppress no-op self-updates after
 * an optimistic UI patch.
 */
export interface CandidateUpdatedEvent {
  type: "candidate_updated";
  candidate_id: string;
  job_id: string;
  status: CandidateStatus;
  name: string | null;
  actor_user_id: string | null;
  actor_name: string | null;
  ts: string;
}

export interface Candidate {
  id: string;
  name: string;
  email: string;
  status: CandidateStatus;
  overall_score: number | null;
  // Sub-scores from the evaluation, surfaced by the comparison/ranking board.
  skill_match: number | null;
  communication: number | null;
  problem_solving: number | null;
  cultural_fit: number | null;
  recommendation:
    | "strong_yes"
    | "yes"
    | "maybe"
    | "no"
    | "strong_no"
    | null;
  resume_url: string | null;
  created_at: string;
  completed_at: string | null;
  /** Pre-screen LLM resume-vs-JD score (0-100). Null until pre-screening runs. */
  resume_match_score: number | null;
  /** Routing decision from the pre-screen engine. */
  pre_screen_decision: PreScreenDecision | null;
}

export interface ResumeParsedData {
  name: string | null;
  email: string | null;
  phone?: string | null;
  years_experience: number | null;
  current_role: string | null;
  current_company?: string | null;
  skills: string[];
  experience: {
    company: string | null;
    role: string | null;
    duration: string | null;
    highlights?: string[];
  }[];
  // `year` can be "2018", "2018-2022", "Expected 2026", etc. — keep flexible.
  education: {
    institution: string | null;
    degree: string | null;
    year: string | number | null;
  }[];
  summary: string;
}

// === Interview ===
export interface TranscriptMessage {
  role: "interviewer" | "candidate";
  content: string;
  timestamp: string;
}

export interface IntegritySignals {
  paste_count: number;
  tab_switch_count: number;
  avg_response_time_seconds: number;
  timing_anomalies: number;
  length_variance_flag: boolean;
  summary: string;
}

export interface Interview {
  id: string;
  transcript: TranscriptMessage[];
  status: string;
  integrity_signals: IntegritySignals;
  cost_usd: number;
  started_at: string;
  completed_at: string | null;
}

// === Evaluation ===
export interface Evaluation {
  overall_score: number;
  scores: {
    skill_match: number;
    communication: number;
    problem_solving: number;
    cultural_fit: number;
  };
  summary: string;
  strengths: string[];
  gaps: string[];
  red_flags: string[];
  recommendation: "strong_yes" | "yes" | "maybe" | "no" | "strong_no";
}

export interface PreScreenSummary {
  score: number | null;
  confidence: number | null;
  decision: PreScreenDecision | null;
  reason: string | null;
  breakdown: {
    matched_skills?: string[];
    missing_must_haves?: string[];
    rationale?: string;
    /**
     * Deterministic alias-aware skill match (Phase 2 / Item 8). Always
     * present on freshly-scored candidates; legacy rows scored before
     * Phase 2 won't have it.
     */
    deterministic_match?: {
      matched_skills: string[];
      missing_skills: string[];
      recall: number;
      evidence: Record<string, string>;
    };
    /**
     * Identity / re-use fraud signals raised by the pre-screen pipeline.
     * Only present when at least one signal fired. `risk_level === "block"`
     * means the candidate was force-routed to HR review even on a passing
     * score; `"warn"` is a softer flag for HR's attention.
     */
    fraud_signals?: {
      risk_level: "warn" | "block";
      signals: Array<{
        kind: "name_mismatch" | "email_mismatch" | "resume_content_reused";
        detail: string;
      }>;
    };
  } | null;
  pre_screened_at: string | null;
  invite_sent_at: string | null;
}

export interface CandidateDetail extends Candidate {
  resume_url: string;
  resume_parsed_data: ResumeParsedData | null;
  interview: Interview;
  evaluation: Evaluation | null;
  pre_screen?: PreScreenSummary | null;
  // Mirror of the parent job's `auto_send_status_emails` toggle, surfaced
  // so HR confirmation dialogs can show whether shortlist/reject will
  // trigger an automatic email.
  job_auto_send_status_emails?: boolean;
  // Last externally-visible notification we dispatched to the candidate.
  // Used by the UI to show "Last notified: Rejected (5 minutes ago)" and
  // to warn HR before sending a contradictory email.
  last_notification_kind?: EmailTemplateKind | null;
  last_notification_sent_at?: string | null;
}

// === Interview Session (candidate-side) ===
export interface InterviewStartResponse {
  interview_token: string;
  first_question: string;
  total_questions: number;
}

export interface InterviewMessageResponse {
  ai_response: string;
  progress: string;
  is_complete: boolean;
  is_last_question: boolean;
}

// === Application flow (two-phase) ===
export interface ApplicationResponse {
  message: string;
  candidate_id: string;
  status: string;
}

export interface ApplicationStatusResponse {
  status: string;
  interview_link: string | null;
}

export interface SessionLandingResponse {
  job_title: string;
  company_name: string;
  candidate_name: string;
  total_questions: number;
  status: string;
  current_question_index: number;
}

export interface SessionStartResponse {
  interview_token: string;
  first_message: string;
  total_questions: number;
}

// === Shareable evaluation report ===
export interface ShareTokenResponse {
  token: string;
  url: string;
  expires_at: string;
  token_id: string;
}

export interface PublicTranscriptMessage {
  role: "interviewer" | "candidate";
  content: string;
  timestamp: string;
}

export interface PublicReport {
  candidate_name: string;
  job_title: string;
  company_name: string;
  completed_at: string | null;
  evaluation: Evaluation;
  transcript: PublicTranscriptMessage[];
  expires_at: string;
}

// === Email templates ===
export type EmailTemplateKind = "shortlist" | "reject" | "status_correction";

export interface EmailTemplateBody {
  subject: string;
  body_html: string;
}

export interface EmailTemplates {
  shortlist: EmailTemplateBody;
  reject: EmailTemplateBody;
  status_correction: EmailTemplateBody;
}

export type EmailTemplatesUpdate = Partial<EmailTemplates>;

// === Candidate notifications ===
export interface SendNotificationResponse {
  sent: boolean;
  kind: EmailTemplateKind;
  last_notification_kind: EmailTemplateKind | null;
  last_notification_sent_at: string | null;
}

/** Shape of the FastAPI 409 detail returned when a notification would
 *  contradict the previously-sent one. The api layer surfaces this as a
 *  typed error so the UI can show a confirmation modal. */
export interface NotificationConflictDetail {
  code: "notification_conflict";
  message: string;
  previous_kind: EmailTemplateKind;
  requested_kind: EmailTemplateKind;
  last_sent_at: string | null;
}

// === Dashboard analytics (mirror of docs/architecture.md) ===
export type AnalyticsWindow = "7d" | "30d" | "90d" | "all";

export interface AnalyticsKPIs {
  active_jobs: number;
  applications: number;
  pending_review: number;
  /** 0..1 ratio. Null when there were no invites in the window. */
  completion_rate: number | null;
  /** USD per completed interview. Null when no interviews completed. */
  avg_cost_per_interview_usd: number | null;
  completed_awaiting_decision: number;
}

export interface AnalyticsFunnel {
  applied: number;
  under_review: number;
  invited: number;
  started: number;
  completed: number;
  shortlisted: number;
  rejected: number;
}

export interface AnalyticsActionItem {
  candidate_id: string;
  job_id: string;
  name: string | null;
  email: string | null;
  job_title: string;
  since: string | null;
}

export interface AnalyticsActionBucket {
  count: number;
  items: AnalyticsActionItem[];
}

export interface AnalyticsActionNeeded {
  pending_review: AnalyticsActionBucket;
  awaiting_decision: AnalyticsActionBucket;
  stalled_invites: AnalyticsActionBucket;
}

export interface AnalyticsJobHealthRow {
  id: string;
  title: string;
  status: "active" | "paused";
  candidate_count: number;
  pending_review: number;
  completion_rate: number | null;
  avg_score: number | null;
  avg_cost: number | null;
  median_time_to_complete_minutes: number | null;
}

export interface AnalyticsTrendPoint {
  /** UTC date in YYYY-MM-DD. Zero-filled for days with no activity. */
  date: string;
  applications: number;
  completed: number;
}

export interface AnalyticsCalibration {
  /** Number of `auto_invite` predictions with HR ground truth. */
  sample_size: number;
  /** Below this `agreement_rate` is null and UI should hide the headline. */
  min_sample: number;
  agreement_rate: number | null;
  auto_invite_n: number;
  auto_invite_agreed: number;
  total_predictions: number;
}

export interface AnalyticsOverview {
  window: AnalyticsWindow;
  /** ISO timestamp; null when window === "all". */
  window_start: string | null;
  generated_at: string;
  kpis: AnalyticsKPIs;
  funnel: AnalyticsFunnel;
  action_needed: AnalyticsActionNeeded;
  jobs: AnalyticsJobHealthRow[];
  trends: AnalyticsTrendPoint[];
  calibration: AnalyticsCalibration;
}

export interface AnalyticsHistogramBucket {
  lo: number;
  hi: number;
  label: string;
  count: number;
}

export interface JobAnalytics {
  job_id: string;
  job_title: string;
  window: AnalyticsWindow;
  window_start: string | null;
  generated_at: string;
  funnel: AnalyticsFunnel;
  score_histogram: AnalyticsHistogramBucket[];
  decision_breakdown: Record<string, number>;
  avg_score: number | null;
  avg_cost: number | null;
  completion_rate: number | null;
}
