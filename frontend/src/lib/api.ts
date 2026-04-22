import type {
  AuthResponse,
  User,
  JobPosting,
  Candidate,
  CandidateDetail,
  InterviewStartResponse,
  InterviewMessageResponse,
  ApplicationResponse,
  ApplicationStatusResponse,
  SessionLandingResponse,
  SessionStartResponse,
} from "./types";

// All API calls go through the Next.js rewrite proxy so the browser sees
// them as same-origin. This lets the backend issue an HttpOnly session
// cookie without cross-site cookie complications.
export const API_URL = "/api/backend";

/**
 * Render a FastAPI/pydantic error payload into a human-readable string.
 * - String detail: returned as-is.
 * - Pydantic validation array: joins each issue as `field: message`.
 * - Anything else: falls back to a generic HTTP message.
 */
function formatApiError(detail: unknown, status: number): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((d) => {
        if (!d || typeof d !== "object") return String(d);
        const item = d as { loc?: unknown[]; msg?: string; message?: string };
        const field =
          Array.isArray(item.loc) && item.loc.length
            ? String(item.loc[item.loc.length - 1])
            : null;
        const message = item.msg || item.message || JSON.stringify(item);
        return field ? `${field}: ${message}` : message;
      })
      .filter(Boolean);
    if (parts.length) return parts.join("; ");
  }
  if (detail && typeof detail === "object") {
    try {
      return JSON.stringify(detail);
    } catch {
      // fallthrough
    }
  }
  return `Request failed (HTTP ${status})`;
}

async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {};

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  // CSRF guard on the backend looks for this header on cookie-authenticated
  // mutating requests. Browsers will not send it on cross-site form posts.
  headers["X-Requested-With"] = "XMLHttpRequest";

  // Merge any additional headers from options
  if (options.headers) {
    const incoming =
      options.headers instanceof Headers
        ? Object.fromEntries(options.headers.entries())
        : (options.headers as Record<string, string>);
    Object.assign(headers, incoming);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    // Send the HttpOnly session cookie set by /auth/login.
    credentials: "include",
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(formatApiError(error.detail, response.status));
  }

  // 204 No Content -> nothing to parse.
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json();
}

// Auth
export const auth = {
  signup: (data: {
    email: string;
    password: string;
    name: string;
    company_name: string;
  }) =>
    apiRequest<AuthResponse>("/auth/signup", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  login: (data: { email: string; password: string }) =>
    apiRequest<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  me: () => apiRequest<{ user: User }>("/auth/me"),
  logout: () => apiRequest<void>("/auth/logout", { method: "POST" }),
};

// Jobs
export const jobs = {
  list: () => apiRequest<{ jobs: JobPosting[] }>("/jobs"),
  get: (id: string) =>
    apiRequest<{ job: JobPosting; candidates_summary: unknown }>(
      `/jobs/${id}`,
    ),
  create: (data: Partial<JobPosting>) =>
    apiRequest<{ job: JobPosting; interview_link: string }>("/jobs", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Partial<JobPosting>) =>
    apiRequest<{ job: JobPosting }>(`/jobs/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    apiRequest<{ message: string }>(`/jobs/${id}`, { method: "DELETE" }),
  candidates: (id: string, params?: string) =>
    apiRequest<{ candidates: Candidate[] }>(
      `/jobs/${id}/candidates${params ? `?${params}` : ""}`,
    ),
};

// Candidates
export const candidates = {
  get: (id: string) => apiRequest<CandidateDetail>(`/candidates/${id}`),
  shortlist: (id: string) =>
    apiRequest<Candidate>(`/candidates/${id}/shortlist`, {
      method: "POST",
    }),
  reject: (id: string) =>
    apiRequest<Candidate>(`/candidates/${id}/reject`, {
      method: "POST",
    }),
};

// Interview (public — no auth needed)
export const interview = {
  getJob: (token: string) =>
    apiRequest<{
      job_title: string;
      company_name: string;
      description: string;
    }>(`/interview/${token}`),

  // Phase A — Application
  apply: (formData: FormData) =>
    apiRequest<ApplicationResponse>(`/interview/apply`, {
      method: "POST",
      body: formData,
    }),
  applicationStatus: (interviewToken: string) =>
    apiRequest<ApplicationStatusResponse>(
      `/interview/apply/${interviewToken}/status`,
    ),

  // Phase B — Interview session
  sessionLanding: (interviewToken: string) =>
    apiRequest<SessionLandingResponse>(
      `/interview/session/${interviewToken}`,
    ),
  sessionStart: (interviewToken: string) =>
    apiRequest<SessionStartResponse>(
      `/interview/session/${interviewToken}/start`,
      { method: "POST" },
    ),
  sendMessage: (data: {
    interview_token: string;
    message: string;
    integrity_signals: unknown;
  }) =>
    apiRequest<InterviewMessageResponse>("/interview/message", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Legacy
  start: (jobToken: string, formData: FormData) =>
    apiRequest<InterviewStartResponse>(`/interview/start`, {
      method: "POST",
      body: formData,
    }),
  status: (token: string) =>
    apiRequest<{ status: string; progress: string }>(
      `/interview/${token}/status`,
    ),
};
