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
}

// === Candidates ===
export interface Candidate {
  id: string;
  name: string;
  email: string;
  status: "invited" | "in_progress" | "completed" | "shortlisted" | "rejected";
  overall_score: number | null;
  resume_url: string | null;
  created_at: string;
  completed_at: string | null;
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

export interface CandidateDetail extends Candidate {
  resume_url: string;
  resume_parsed_data: ResumeParsedData | null;
  interview: Interview;
  evaluation: Evaluation | null;
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
