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
  name: string;
  email: string;
  years_experience: number;
  current_role: string;
  skills: string[];
  experience: { company: string; role: string; duration: string }[];
  education: { institution: string; degree: string; year: number }[];
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
