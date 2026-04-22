# Phase 1B: Frontend — Weeks 8–10

> **Status:** `NOT_STARTED`
> **Depends on:** [Phase 1A Backend](./PHASE_1A_BACKEND.md) — auth + job CRUD endpoints must be ready (end of Week 5)
> **Unlocks:** [Phase 2 Integration & Launch](./PHASE_2_INTEGRATION_LAUNCH.md)
> **Tracker:** [MVP_TRACKER.md](./MVP_TRACKER.md)

---

## Goal

Build two frontend applications in one TanStack Start project:

1. **HR Dashboard** (authenticated) — signup, login, job management, candidate review
2. **Candidate Interview UI** (public) — resume upload, chat-based interview, completion screen
3. **Landing Page** (public, SSR) — value proposition, pricing, CTA

---

## Tech Stack (Frontend)

| Component | Tool | Version | Install |
|-----------|------|---------|---------|
| Framework | TanStack Start | Latest | `npm create @tanstack/start@latest` |
| Routing | TanStack Router | Latest | Included with TanStack Start |
| Styling | TailwindCSS | 4.x | `npm install tailwindcss @tailwindcss/vite` |
| UI Components | shadcn/ui | Latest | `npx shadcn@latest init` |
| Icons | Lucide React | Latest | `npm install lucide-react` |
| Theme | next-themes | Latest | `npm install next-themes` |
| HTTP Client | fetch (built-in) | — | No install needed |
| Form Validation | Zod + React Hook Form | Latest | `npm install zod react-hook-form @hookform/resolvers` |
| State | React Context + useState | Built-in | No install needed |
| File Upload | react-dropzone | Latest | `npm install react-dropzone` |
| Toast/Notifications | sonner | Latest | `npm install sonner` |
| Date formatting | date-fns | Latest | `npm install date-fns` |
| Charts (optional) | recharts | Latest | `npm install recharts` |

```bash
# Setup (Day 1)
npm create @tanstack/start@latest frontend
cd frontend
npx shadcn@latest init
npx shadcn@latest add button card input label table badge dialog dropdown-menu \
  separator tabs textarea toast avatar progress sheet select
npm install lucide-react next-themes zod react-hook-form @hookform/resolvers \
  react-dropzone sonner date-fns
```

---

## Project Structure

```
frontend/
├── .env
├── app.config.ts                         # TanStack Start config
├── app/
│   ├── routes/
│   │   ├── __root.tsx                    # Root layout + providers
│   │   ├── index.tsx                     # Landing page (SSR for SEO)
│   │   ├── _auth.tsx                     # Auth layout (centered card)
│   │   ├── _auth/
│   │   │   ├── login.tsx
│   │   │   └── signup.tsx
│   │   ├── _dashboard.tsx                # Dashboard layout (sidebar + header)
│   │   ├── _dashboard/
│   │   │   ├── dashboard.tsx              # Job list + stats
│   │   │   ├── jobs/
│   │   │   │   ├── new.tsx               # Create job wizard
│   │   │   │   └── $jobId/
│   │   │   │       ├── index.tsx          # Candidate pipeline for job
│   │   │   │       └── candidates/
│   │   │   │           └── $candidateId.tsx  # Candidate detail
│   │   │   └── settings.tsx               # Account settings (basic)
│   │   └── interview/
│   │       └── $token/
│   │           ├── index.tsx              # Interview landing + flow
│   │           └── complete.tsx           # Thank you screen
│   │
│   ├── components/
│   │   ├── ui/                           # shadcn components (auto-generated)
│   │   ├── layout/
│   │   │   ├── sidebar.tsx               # Dashboard sidebar nav
│   │   │   ├── header.tsx                # Top bar with user menu
│   │   │   └── mobile-nav.tsx            # Mobile hamburger nav
│   │   ├── auth/
│   │   │   ├── login-form.tsx
│   │   │   └── signup-form.tsx
│   │   ├── jobs/
│   │   │   ├── job-card.tsx              # Job summary card for dashboard
│   │   │   ├── job-create-wizard.tsx     # Multi-step job creation
│   │   │   ├── job-stats.tsx             # Quick stats (candidates, avg score)
│   │   │   └── interview-link-share.tsx  # Copy link + email invite UI
│   │   ├── candidates/
│   │   │   ├── candidate-table.tsx       # Sortable candidate list
│   │   │   ├── candidate-row.tsx         # Table row component
│   │   │   ├── candidate-detail.tsx      # Full evaluation view
│   │   │   ├── score-display.tsx         # Score badges/bars
│   │   │   ├── transcript-viewer.tsx     # Chat transcript read-only
│   │   │   ├── integrity-panel.tsx       # Anti-cheating signals display
│   │   │   └── candidate-actions.tsx     # Shortlist/reject buttons
│   │   ├── interview/
│   │   │   ├── interview-landing.tsx     # Welcome screen + start CTA
│   │   │   ├── resume-upload.tsx         # Drag-drop PDF/DOCX upload
│   │   │   ├── chat-interface.tsx        # Chat bubbles + input
│   │   │   ├── chat-message.tsx          # Single message bubble
│   │   │   ├── typing-indicator.tsx      # "AI is typing..." dots
│   │   │   ├── progress-bar.tsx          # "Question 3 of 8"
│   │   │   └── interview-complete.tsx    # Thank you screen
│   │   └── landing/
│   │       ├── hero.tsx                  # Main value proposition
│   │       ├── features.tsx              # Feature grid
│   │       ├── pricing.tsx               # Pricing cards
│   │       ├── testimonials.tsx          # Pilot customer quotes
│   │       └── cta.tsx                   # Final call to action
│   │
│   ├── lib/
│   │   ├── api.ts                        # API client (fetch wrapper)
│   │   ├── auth.ts                       # JWT storage, auth context
│   │   ├── types.ts                      # TypeScript interfaces
│   │   └── utils.ts                      # formatDate, truncate, etc.
│   │
│   └── hooks/
│       ├── use-auth.ts                   # Auth context hook
│       ├── use-api.ts                    # API call hook with loading/error
│       └── use-interview.ts             # Interview state management
```

> **TanStack Start routing notes:**
> - `__root.tsx` = root layout (equivalent to a global layout for the whole app)
> - `_auth.tsx` / `_dashboard.tsx` = pathless layout routes (prefix `_` means no URL segment)
> - `$jobId` / `$token` / `$candidateId` = dynamic params (TanStack Router convention)
> - `index.tsx` = default route for a folder
> - Landing page (`index.tsx`) uses SSR via `createFileRoute` with a `loader`. Dashboard routes are SPA-only.

---

## TypeScript Interfaces

**File: `src/lib/types.ts`**

```typescript
// === Auth ===
interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  company: Company;
}

interface Company {
  id: string;
  name: string;
  logo_url: string | null;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// === Jobs ===
interface JobPosting {
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

interface InterviewConfig {
  num_questions: number;
  style: "quick" | "standard" | "deep";
}

interface CustomQuestion {
  question: string;
  category: string;
}

// === Candidates ===
interface Candidate {
  id: string;
  name: string;
  email: string;
  status: "invited" | "in_progress" | "completed" | "shortlisted" | "rejected";
  overall_score: number | null;
  created_at: string;
  completed_at: string | null;
}

interface CandidateDetail extends Candidate {
  resume_url: string;
  resume_parsed_data: ResumeParsedData | null;
  interview: Interview;
  evaluation: Evaluation | null;
}

// === Interview ===
interface Interview {
  id: string;
  transcript: TranscriptMessage[];
  status: string;
  integrity_signals: IntegritySignals;
  cost_usd: number;
  started_at: string;
  completed_at: string | null;
}

interface TranscriptMessage {
  role: "interviewer" | "candidate";
  content: string;
  timestamp: string;
}

interface IntegritySignals {
  paste_count: number;
  tab_switch_count: number;
  avg_response_time_seconds: number;
  timing_anomalies: number;
  length_variance_flag: boolean;
  summary: string;
}

// === Evaluation ===
interface Evaluation {
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

// === Interview Session (candidate-side) ===
interface InterviewStartResponse {
  interview_token: string;
  first_question: string;
  total_questions: number;
}

interface InterviewMessageResponse {
  ai_response: string;
  progress: string;       // "3/8"
  is_complete: boolean;
}

interface ResumeParsedData {
  name: string;
  email: string;
  years_experience: number;
  current_role: string;
  skills: string[];
  experience: { company: string; role: string; duration: string }[];
  education: { institution: string; degree: string; year: number }[];
  summary: string;
}
```

---

## API Client

**File: `src/lib/api.ts`**

```typescript
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = typeof window !== "undefined" 
    ? localStorage.getItem("access_token") 
    : null;

  const headers: HeadersInit = {
    ...(options.headers || {}),
  };

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (!(options.body instanceof FormData)) {
    (headers as Record<string, string>)["Content-Type"] = "application/json";
  }

  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Auth
export const auth = {
  signup: (data: { email: string; password: string; name: string; company_name: string }) =>
    apiRequest<AuthResponse>("/auth/signup", { method: "POST", body: JSON.stringify(data) }),
  login: (data: { email: string; password: string }) =>
    apiRequest<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  me: () => apiRequest<{ user: User }>("/auth/me"),
};

// Jobs
export const jobs = {
  list: () => apiRequest<{ jobs: JobPosting[] }>("/jobs"),
  get: (id: string) => apiRequest<{ job: JobPosting; candidates_summary: any }>(`/jobs/${id}`),
  create: (data: Partial<JobPosting>) =>
    apiRequest<{ job: JobPosting; interview_link: string }>("/jobs", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<JobPosting>) =>
    apiRequest<{ job: JobPosting }>(`/jobs/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiRequest<{ message: string }>(`/jobs/${id}`, { method: "DELETE" }),
  candidates: (id: string, params?: string) =>
    apiRequest<{ candidates: Candidate[] }>(`/jobs/${id}/candidates${params ? `?${params}` : ""}`),
};

// Candidates
export const candidates = {
  get: (id: string) => apiRequest<CandidateDetail>(`/candidates/${id}`),
  shortlist: (id: string) =>
    apiRequest<{ candidate: Candidate }>(`/candidates/${id}/shortlist`, { method: "POST" }),
  reject: (id: string) =>
    apiRequest<{ candidate: Candidate }>(`/candidates/${id}/reject`, { method: "POST" }),
};

// Interview (public — no auth needed)
export const interview = {
  getJob: (token: string) =>
    apiRequest<{ job_title: string; company_name: string; description: string }>(`/interview/${token}`),
  start: (jobToken: string, formData: FormData) =>
    apiRequest<InterviewStartResponse>(`/interview/start`, {
      method: "POST",
      body: formData, // Contains: job_token, candidate_name, candidate_email, resume_file
    }),
  sendMessage: (data: { interview_token: string; message: string; integrity_signals: any }) =>
    apiRequest<InterviewMessageResponse>("/interview/message", { method: "POST", body: JSON.stringify(data) }),
  status: (token: string) =>
    apiRequest<{ status: string; progress: string }>(`/interview/${token}/status`),
};
```

---

## Week 8: Auth Pages + Dashboard + Job CRUD

**Status:** `NOT_STARTED`

**Prerequisite:** Backend auth + job CRUD endpoints ready (Phase 1A Week 4–5)

### Tasks
- [ ] Initialize TanStack Start project with TailwindCSS v4 + shadcn/ui
- [ ] Create `app/lib/api.ts` — API client with JWT token handling
- [ ] Create `app/lib/types.ts` — all TypeScript interfaces
- [ ] Create `app/lib/auth.ts` — auth context provider (login, logout, check session)
- [ ] Create `app/hooks/use-auth.ts` — hook to access auth state
- [ ] Create `app/hooks/use-api.ts` — hook with loading/error states for API calls
- [ ] **Auth Pages:**
  - [ ] `/login` — email + password form, JWT stored in localStorage
  - [ ] `/signup` — email + password + name + company name, auto-login after signup
  - [ ] Auth redirect: if logged in → `/dashboard`, if not logged in → `/login`
  - [ ] Form validation with Zod (email format, password min 8 chars)
  - [ ] Error states: invalid credentials, duplicate email, network error
- [ ] **Dashboard Layout:**
  - [ ] Sidebar with nav: Dashboard, Settings (simple for MVP)
  - [ ] Top header with company name + user avatar + logout dropdown
  - [ ] Mobile responsive: sidebar becomes sheet/drawer
- [ ] **Dashboard Page (`/dashboard`):**
  - [ ] Fetch + display job postings as cards
  - [ ] Each card shows: title, status badge, candidate count, avg score, created date
  - [ ] "Create New Job" button → navigates to `/jobs/new`
  - [ ] Empty state: "No job postings yet. Create your first one."
  - [ ] Loading skeleton while fetching
- [ ] **Create Job Page (`/jobs/new`):**
  - [ ] Step 1: Job title + department + location + employment type
  - [ ] Step 2: Job description (textarea, min 50 chars)
  - [ ] Step 3: Required skills (tag input) + interview style selector
  - [ ] Step 4: Review + create → redirects to job detail page
  - [ ] Shows generated interview link with copy button
  - [ ] Form validation at each step

### Component Details

**Login Form:**
```
┌─────────────────────────────┐
│         Company Logo         │
│                             │
│  ┌───────────────────────┐  │
│  │ Email                  │  │
│  └───────────────────────┘  │
│  ┌───────────────────────┐  │
│  │ Password               │  │
│  └───────────────────────┘  │
│                             │
│  [        Log In         ]  │
│                             │
│  Don't have an account?     │
│  Sign up →                  │
└─────────────────────────────┘
```

**Dashboard:**
```
┌──────────┬──────────────────────────────────────┐
│ Sidebar  │  Dashboard                            │
│          │                                       │
│ 📊 Dash  │  [+ Create New Job]                   │
│ ⚙ Settings│                                      │
│          │  ┌──────────────────────────────────┐ │
│          │  │ Senior Marketing Manager          │ │
│          │  │ ● Active  •  12 candidates        │ │
│          │  │ Avg score: 7.2  •  3 days ago     │ │
│          │  └──────────────────────────────────┘ │
│          │  ┌──────────────────────────────────┐ │
│          │  │ Sales Representative              │ │
│          │  │ ● Active  •  5 candidates         │ │
│          │  │ Avg score: 6.8  •  1 week ago     │ │
│          │  └──────────────────────────────────┘ │
└──────────┴──────────────────────────────────────┘
```

### Validation (Week 8)
- [ ] Signup → creates account → lands on dashboard
- [ ] Login → JWT stored → protected routes accessible
- [ ] Unauthenticated user → redirected to /login
- [ ] Dashboard shows job cards with correct data from API
- [ ] Create job wizard → job created → interview link shown
- [ ] Copy interview link works
- [ ] Mobile layout works (sidebar collapses)
- [ ] Loading and error states display correctly

---

## Week 9: Candidate Pipeline + Evaluation Review

**Status:** `NOT_STARTED`

**Prerequisite:** Backend candidate + evaluation endpoints ready (Phase 1A Week 5–7)

### Tasks
- [ ] **Job Detail Page (`/jobs/:id`):**
  - [ ] Fetch job detail + candidates list
  - [ ] Show interview link with copy button + "email invite" action
  - [ ] Candidate table: name, email, status, score, date, actions
  - [ ] Sort by: score (desc), date (desc), name (asc)
  - [ ] Filter by: status (all, completed, shortlisted, rejected, in_progress)
  - [ ] Score displayed as colored badge (green ≥7, yellow 5–6.9, red <5)
  - [ ] Click candidate row → navigate to candidate detail
  - [ ] Batch actions: select multiple → shortlist/reject (nice to have)
  - [ ] Empty state: "No candidates yet. Share the interview link to get started."
- [ ] **Candidate Detail Page (`/jobs/:id/candidates/:candidateId`):**
  - [ ] Header: candidate name, email, status badge, shortlist/reject buttons
  - [ ] **Evaluation Summary Tab:**
    - [ ] Overall score (large number + circular progress)
    - [ ] Individual scores as horizontal bars (skill, communication, problem_solving, cultural_fit)
    - [ ] Recommendation badge (strong_yes → green, no → red)
    - [ ] Summary paragraph
    - [ ] Strengths as green badges
    - [ ] Gaps as yellow badges
    - [ ] Red flags as red badges (if any)
  - [ ] **Transcript Tab:**
    - [ ] Chat-style display (interviewer left, candidate right)
    - [ ] Messages styled as bubbles
    - [ ] Timestamp on hover
    - [ ] Search within transcript (nice to have)
  - [ ] **Integrity Tab:**
    - [ ] Confidence level badge (high/medium/low)
    - [ ] Paste count with percentage
    - [ ] Tab switch count
    - [ ] Average response time
    - [ ] Timing anomalies count
    - [ ] Length variance flag
    - [ ] Summary sentence
  - [ ] **Resume Tab:**
    - [ ] Resume viewer or parsed data display
    - [ ] Download original resume button
  - [ ] Shortlist button → updates status + optional confirmation
  - [ ] Reject button → updates status + optional confirmation

### Component Wireframes

**Candidate Pipeline Table:**
```
┌─────────────────────────────────────────────────────────────────┐
│ Senior Marketing Manager — 12 candidates                        │
│                                                                 │
│ 🔗 Interview Link: https://app.../interview/abc123  [Copy]     │
│                                                                 │
│ Filter: [All ▾]  Sort: [Score ↓ ▾]                             │
│                                                                 │
│ ┌───┬──────────────┬────────────┬────────┬───────┬──────────┐  │
│ │   │ Name         │ Email      │ Status │ Score │ Date     │  │
│ ├───┼──────────────┼────────────┼────────┼───────┼──────────┤  │
│ │ ☐ │ Jane Doe     │ jane@...   │ ✅ Done │ 8.2   │ 2 hrs    │  │
│ │ ☐ │ John Smith   │ john@...   │ ✅ Done │ 7.5   │ 5 hrs    │  │
│ │ ☐ │ Sarah Lee    │ sarah@...  │ ⏳ IP  │ —     │ 1 day    │  │
│ │ ☐ │ Mike Chen    │ mike@...   │ ✅ Done │ 6.1   │ 2 days   │  │
│ └───┴──────────────┴────────────┴────────┴───────┴──────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Candidate Detail — Evaluation:**
```
┌──────────────────────────────────────────────────┐
│ ← Back to candidates                              │
│                                                   │
│ Jane Doe                    [⭐ Shortlist] [✗ Reject] │
│ jane@email.com • Completed 2 hours ago            │
│                                                   │
│ [Evaluation] [Transcript] [Integrity] [Resume]    │
│ ─────────────────────────────────────────────     │
│                                                   │
│   Overall Score:  ████████░░  8.2 / 10            │
│   Recommendation: ✅ YES                          │
│                                                   │
│   Skill Match:    ████████░░  8.5                 │
│   Communication:  ███████░░░  7.0                 │
│   Problem Solving:████████░░  8.0                 │
│   Cultural Fit:   █████████░  9.0                 │
│                                                   │
│   Summary:                                        │
│   "Strong candidate with 5 years of digital       │
│    marketing experience. Deep SEO knowledge..."    │
│                                                   │
│   Strengths: [SEO] [Data-driven] [Leadership]     │
│   Gaps: [No B2B SaaS experience]                  │
│   Red Flags: None                                 │
└──────────────────────────────────────────────────┘
```

### Validation (Week 9)
- [ ] Job detail page shows candidates from API
- [ ] Sorting by score works
- [ ] Filtering by status works
- [ ] Candidate detail shows all evaluation data
- [ ] Transcript displays as chat bubbles
- [ ] Integrity signals displayed clearly
- [ ] Shortlist/reject buttons update status
- [ ] Score colors correct (green/yellow/red)
- [ ] Empty states for no candidates, no evaluation

---

## Week 10: Candidate Interview UI + Landing Page

**Status:** `NOT_STARTED`

**Prerequisite:** Backend interview endpoints ready (Phase 1A Week 6–7)

### Tasks
- [ ] **Interview Landing Page (`/interview/:token`):**
  - [ ] Fetch job info from `GET /interview/:token`
  - [ ] Show: company name, job title, brief description
  - [ ] "Start Interview" CTA button
  - [ ] Estimated time: "~15–20 minutes"
  - [ ] What to expect section: "Upload resume → Answer questions → Get evaluated"
  - [ ] Mobile-first design (most candidates will be on phone)
- [ ] **Resume Upload Screen:**
  - [ ] Drag-and-drop zone (react-dropzone)
  - [ ] Accept PDF/DOCX only, max 10MB
  - [ ] Candidate name + email input fields
  - [ ] "Begin Interview" button
  - [ ] Loading state while resume is being parsed
  - [ ] Error handling: invalid file type, too large, parse failure
- [ ] **Chat Interface:**
  - [ ] AI message appears first (first question)
  - [ ] Text input at bottom (auto-focus)
  - [ ] Send button + Enter key to submit
  - [ ] Messages display as chat bubbles (AI left, candidate right)
  - [ ] Typing indicator while AI processes response
  - [ ] Progress bar: "Question 3 of 8"
  - [ ] Auto-scroll to latest message
  - [ ] **Integrity tracking (invisible to candidate):**
    - [ ] Detect paste events on input field (`paste` event listener)
    - [ ] Track time between question rendered → answer submitted
    - [ ] Track tab visibility changes (`visibilitychange` event)
    - [ ] Send integrity_signals with each `/interview/message` call
  - [ ] Auto-save: if user refreshes, resume from last message
  - [ ] Handle slow AI response (>5 seconds): show extended typing indicator
  - [ ] Handle network error: retry button, don't lose the answer
- [ ] **Interview Complete Screen:**
  - [ ] "Thank you for completing the interview!"
  - [ ] "The hiring team will review your responses."
  - [ ] Estimated next steps timeline
  - [ ] No score shown to candidate (HR sees it, candidate doesn't)
- [ ] **Landing Page (`/`):**
  - [ ] Hero: headline + subheadline + "Start Free Trial" CTA
  - [ ] Feature grid: 4–6 key features with icons
  - [ ] How it works: 3-step process (Create job → Share link → Review results)
  - [ ] Pricing section: Starter/Growth/Agency cards (info only for MVP, no Stripe yet)
  - [ ] Testimonial section (placeholder for pilot feedback)
  - [ ] Footer: links, company info
  - [ ] SEO: meta tags, Open Graph, structured data
  - [ ] Mobile responsive

### Chat Interface Component Detail

```typescript
// src/hooks/use-interview.ts — Interview state manager

interface InterviewState {
  status: "landing" | "upload" | "chatting" | "complete";
  jobInfo: { job_title: string; company_name: string; description: string } | null;
  interviewToken: string | null;
  messages: { role: "interviewer" | "candidate"; content: string }[];
  progress: string;  // "3/8"
  isAiTyping: boolean;
  // Integrity tracking (not shown in UI)
  pasteCount: number;
  tabSwitchCount: number;
  currentQuestionRenderedAt: number;  // timestamp
}
```

**Integrity Tracking Implementation:**

```typescript
// Paste detection — attach to input field
const handlePaste = (e: React.ClipboardEvent) => {
  // Don't prevent paste — just log it
  setPasteCount(prev => prev + 1);
};

// Tab visibility — attach on mount
useEffect(() => {
  const handleVisibility = () => {
    if (document.hidden) {
      setTabSwitchCount(prev => prev + 1);
    }
  };
  document.addEventListener("visibilitychange", handleVisibility);
  return () => document.removeEventListener("visibilitychange", handleVisibility);
}, []);

// Response timing — track per question
const handleSendMessage = async (message: string) => {
  const timeToAnswer = (Date.now() - currentQuestionRenderedAt) / 1000;
  
  const response = await interview.sendMessage({
    interview_token: interviewToken,
    message,
    integrity_signals: {
      was_pasted: pasteCount > lastPasteCount,
      time_to_answer_seconds: Math.round(timeToAnswer),
      answer_word_count: message.split(/\s+/).length,
      tab_switch_count: tabSwitchCount,
    },
  });
  
  // Reset per-question counters
  setCurrentQuestionRenderedAt(Date.now());
  setLastPasteCount(pasteCount);
};
```

### Chat UI Wireframe

```
┌────────────────────────────────┐
│ Marketing Manager Interview     │
│ Acme Corp                       │
│ ▓▓▓▓▓▓░░░░░░░░  Question 4/8   │
├────────────────────────────────┤
│                                 │
│  🤖 Thanks for that detail      │
│  about your SEO work at Acme.   │
│  Next question: Can you         │
│  describe a campaign that       │
│  didn't go as planned?          │
│                                 │
│              I once launched a  │
│              PPC campaign that  │
│              went over budget   │
│              by 40%. The issue  │
│              was...          👤 │
│                                 │
│  🤖 That's an interesting case. │
│  How did you communicate the    │
│  overspend to stakeholders?     │
│                                 │
│  ●●● AI is typing...           │
│                                 │
├────────────────────────────────┤
│ ┌──────────────────────┐ [Send] │
│ │ Type your answer...   │       │
│ └──────────────────────┘        │
└────────────────────────────────┘
```

### Landing Page Wireframe

```
┌──────────────────────────────────────────────┐
│  Logo                    Features  Pricing   │
│                          [Start Free Trial]  │
├──────────────────────────────────────────────┤
│                                              │
│  Screen candidates in minutes,               │
│  not hours.                                  │
│                                              │
│  AI-powered first-round interviews that      │
│  save HR teams 70% of screening time.        │
│                                              │
│  [Start Free Trial]  [See Demo]              │
│                                              │
├──────────────────────────────────────────────┤
│                                              │
│  How It Works                                │
│                                              │
│  1. Create Job    2. Share Link   3. Review  │
│  Paste your JD    Candidates get  See scores │
│  and we generate  a unique link   and ranked │
│  interview Qs     to interview    candidates │
│                                              │
├──────────────────────────────────────────────┤
│                                              │
│  Pricing                                     │
│                                              │
│  Starter $79/mo  Growth $199/mo  Agency $499 │
│  50 interviews   200 interviews  1K interviews│
│                                              │
├──────────────────────────────────────────────┤
│  Footer                                      │
└──────────────────────────────────────────────┘
```

### Validation (Week 10)
- [ ] Interview landing loads job info from API
- [ ] Resume upload accepts PDF/DOCX, rejects unsupported formats
- [ ] Chat interface sends/receives messages correctly
- [ ] AI typing indicator shows during processing
- [ ] Progress bar updates after each question
- [ ] Paste detection logs correctly (verify in network tab)
- [ ] Tab switch count increments when switching tabs
- [ ] Response timing sent with each message
- [ ] Complete screen shows after final question
- [ ] Landing page renders on desktop and mobile
- [ ] All pages work on mobile (especially chat interface)
- [ ] No candidate data exposed (scores, evaluation) to candidate

---

## Artifacts Produced by Phase 1B

| Artifact | Used In Phase 2 |
|----------|----------------|
| Auth flow | E2E testing |
| Dashboard | Pilot customer onboarding |
| Candidate pipeline | HR review workflow |
| Interview chat UI | Candidate testing |
| Landing page | Marketing, pilot acquisition |
| Integrity tracking | Verify signals reach backend |

---

## Environment Variables (Frontend)

**File: `.env`**
```
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=HR AI Interviewer
VITE_APP_URL=http://localhost:3000
```

---

## Key Frontend Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Framework | TanStack Start | Client-first with selective SSR, Vite-based, deploy anywhere |
| Component library | shadcn/ui | Copy-paste, customizable, no vendor lock-in |
| State management | React Context + hooks | Simple enough for MVP, no Redux needed |
| CSS approach | TailwindCSS v4 | Fast development, consistent design, new config-free setup |
| Form handling | React Hook Form + Zod v4 | Type-safe validation, good DX |
| Auth storage | localStorage | Simple for MVP. Switch to httpOnly cookies later. |
| Data fetching | Native fetch | No TanStack Query yet — add in Phase 2 if needed |
| Routing | TanStack Router (file-based) | Type-safe params, layouts via pathless routes |
