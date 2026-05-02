import type {
  AuthResponse,
  JobPosting,
  Candidate,
  CandidateDetail,
  EmailTemplateKind,
  InterviewStartResponse,
  InterviewMessageResponse,
  ApplicationResponse,
  ApplicationStatusResponse,
  SendNotificationResponse,
  SessionLandingResponse,
  SessionStartResponse,
  ShareTokenResponse,
  PublicReport,
  EmailTemplates,
  EmailTemplatesUpdate,
  MeResponse,
  RefreshResponse,
} from "./types";
import type {
  AnalyticsOverview,
  AnalyticsWindow,
  JobAnalytics,
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

/**
 * Typed error thrown for any non-2xx response. Carries the HTTP status and
 * the raw `detail` payload so callers can branch on structured error codes
 * (e.g. the candidate-notification conflict guard).
 */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

// --- Silent token refresh on 401 ----------------------------------------------
//
// Strategy:
//   1. Any non-auth request that returns 401 triggers a single silent call to
//      POST /auth/refresh, then retries the original request once.
//   2. Concurrent 401s share ONE in-flight refresh promise (singleton) so we
//      never fan-out N parallel /auth/refresh calls under bursty load.
//   3. If the refresh itself fails (expired/revoked cookie), we surface the
//      original 401 — the AuthProvider's /auth/me probe will then redirect to
//      /login. We do NOT redirect from here to keep this layer transport-only.
//   4. Endpoints that must NEVER trigger refresh: /auth/login, /auth/signup,
//      /auth/refresh, /auth/logout. (Refreshing on these is either nonsensical
//      or would cause infinite recursion.)
//
// The optional `_skipRefresh` flag is used internally for the retry attempt so
// a second 401 in a row does not trigger an infinite refresh loop.

const REFRESH_PATH = "/auth/refresh";
const NO_REFRESH_PATHS = new Set<string>([
  "/auth/login",
  "/auth/signup",
  "/auth/logout",
  REFRESH_PATH,
]);

let inFlightRefresh: Promise<boolean> | null = null;

/**
 * Trigger a single silent refresh. Multiple callers awaiting concurrently will
 * share the same promise. Resolves to `true` if the cookie was refreshed,
 * `false` if the refresh itself failed (caller should treat as logged out).
 */
function refreshSession(): Promise<boolean> {
  if (inFlightRefresh) return inFlightRefresh;

  inFlightRefresh = (async () => {
    try {
      const response = await fetch(`${API_URL}${REFRESH_PATH}`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
      });
      return response.ok;
    } catch {
      return false;
    } finally {
      // Clear after a microtask so any callers awaiting see the resolved value
      // before the next request can kick off a new refresh.
      queueMicrotask(() => {
        inFlightRefresh = null;
      });
    }
  })();

  return inFlightRefresh;
}

/** Listeners notified when a silent refresh fails (cookie expired/revoked). */
const sessionExpiredListeners = new Set<() => void>();

export function onSessionExpired(listener: () => void): () => void {
  sessionExpiredListeners.add(listener);
  return () => sessionExpiredListeners.delete(listener);
}

function notifySessionExpired(): void {
  for (const listener of sessionExpiredListeners) {
    try {
      listener();
    } catch {
      // never let a listener break others
    }
  }
}

interface InternalRequestOptions extends RequestInit {
  /** Internal: skip the 401-refresh interceptor (used for retry + auth endpoints). */
  _skipRefresh?: boolean;
}

async function apiRequest<T>(
  path: string,
  options: InternalRequestOptions = {},
): Promise<T> {
  const { _skipRefresh, ...fetchOptions } = options;
  const headers: Record<string, string> = {};

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (!(fetchOptions.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  // CSRF guard on the backend looks for this header on cookie-authenticated
  // mutating requests. Browsers will not send it on cross-site form posts.
  headers["X-Requested-With"] = "XMLHttpRequest";

  // Merge any additional headers from options
  if (fetchOptions.headers) {
    const incoming =
      fetchOptions.headers instanceof Headers
        ? Object.fromEntries(fetchOptions.headers.entries())
        : (fetchOptions.headers as Record<string, string>);
    Object.assign(headers, incoming);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...fetchOptions,
    headers,
    // Send the HttpOnly session cookie set by /auth/login.
    credentials: "include",
  });

  // 401 interceptor: silently refresh + retry once.
  if (
    response.status === 401 &&
    !_skipRefresh &&
    !NO_REFRESH_PATHS.has(path)
  ) {
    const refreshed = await refreshSession();
    if (refreshed) {
      return apiRequest<T>(path, { ...options, _skipRefresh: true });
    }
    // Refresh failed → cookie is gone or expired. Surface the original error
    // and let listeners (AuthProvider) handle the redirect to /login.
    notifySessionExpired();
  }

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new ApiError(
      formatApiError(error.detail, response.status),
      response.status,
      error.detail,
    );
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
  me: () => apiRequest<MeResponse>("/auth/me"),
  refresh: () =>
    apiRequest<RefreshResponse>("/auth/refresh", { method: "POST" }),
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
  candidates: (
    id: string,
    opts: { limit?: number; offset?: number; sort?: string; order?: string } = {},
  ) => {
    const { limit = 50, offset = 0, sort, order } = opts;
    const qs = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (sort) qs.set("sort", sort);
    if (order) qs.set("order", order);
    return apiRequest<{ candidates: Candidate[]; total: number }>(
      `/jobs/${id}/candidates?${qs.toString()}`,
    );
  },
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
  /** HR action: approve a candidate awaiting pre-screen review.
   *  Generates the interview and emails the invite link. */
  approveInterview: (id: string) =>
    apiRequest<CandidateDetail>(`/candidates/${id}/approve-interview`, {
      method: "POST",
    }),
  /** HR action: reject a candidate awaiting pre-screen review.
   *  Marks the candidate `rejected` without ever emailing an interview link. */
  rejectPreScreen: (id: string) =>
    apiRequest<CandidateDetail>(`/candidates/${id}/reject-pre-screen`, {
      method: "POST",
    }),
  /** HR action: explicitly email the candidate about their current status.
   *
   *  Throws `ApiError` with status 409 and a `notification_conflict` detail
   *  when the requested email contradicts the previous one (e.g. the
   *  candidate was already notified of a rejection and HR is now trying to
   *  send a shortlist email). Set `force=true` to override the guard \u2014
   *  typically after sending a `status_correction` email first.
   */
  sendNotification: (
    id: string,
    args: { kind: EmailTemplateKind; force?: boolean },
  ) =>
    apiRequest<SendNotificationResponse>(
      `/candidates/${id}/send-notification`,
      {
        method: "POST",
        body: JSON.stringify({ kind: args.kind, force: args.force ?? false }),
      },
    ),
};

// Shareable evaluation reports
export const share = {
  create: (candidateId: string) =>
    apiRequest<ShareTokenResponse>(`/candidates/${candidateId}/share`, {
      method: "POST",
    }),
  revoke: (candidateId: string, tokenId: string) =>
    apiRequest<void>(`/candidates/${candidateId}/share/${tokenId}`, {
      method: "DELETE",
    }),
};

// Public report (no auth, callable from /report/[token])
export const publicReports = {
  get: (token: string) =>
    apiRequest<PublicReport>(`/public/report/${token}`),
};

// Per-company status-email templates
export const emailTemplates = {
  get: () => apiRequest<EmailTemplates>("/companies/me/email-templates"),
  update: (data: EmailTemplatesUpdate) =>
    apiRequest<EmailTemplates>("/companies/me/email-templates", {
      method: "PUT",
      body: JSON.stringify(data),
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

// Dashboard analytics. Single endpoint that replaces the old N+1
// pattern (jobs.list → candidates per job) the dashboard used to do
// client-side. See `plans/DASHBOARD_METRICS.md` for definitions.
export const analytics = {
  overview: (window: AnalyticsWindow = "30d") =>
    apiRequest<AnalyticsOverview>(
      `/analytics/overview?window=${encodeURIComponent(window)}`,
    ),
  job: (jobId: string, window: AnalyticsWindow = "30d") =>
    apiRequest<JobAnalytics>(
      `/analytics/jobs/${encodeURIComponent(jobId)}?window=${encodeURIComponent(window)}`,
    ),
};
