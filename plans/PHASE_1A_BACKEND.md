# Phase 1A: Backend — Weeks 4–7

> **Status:** `IN_PROGRESS`
> **Depends on:** [Phase 0 POC](./PHASE_0_POC.md) — must be `DONE`
> **Unlocks:** [Phase 1B Frontend](./PHASE_1B_FRONTEND.md) — can start Week 8 once auth + job CRUD endpoints are ready
> **Tracker:** [MVP_TRACKER.md](./MVP_TRACKER.md)

---

## Goal

Production-ready FastAPI backend with:
- HR user authentication
- Job posting CRUD
- AI interview engine (ported from POC)
- Candidate management
- Evaluation pipeline
- Anti-cheating signal storage
- Transactional email (invites)

**Frontend team (or you, in Week 8) can build against these APIs.**

---

## Tech Stack (Backend)

| Component | Tool | Version | Install |
|-----------|------|---------|---------|
| Runtime | Python 3.12 | 3.12+ | Already have |
| Framework | FastAPI | 0.115+ | `pip install fastapi[standard]` |
| Server | Uvicorn | 0.30+ | Included with fastapi[standard] |
| Database | PostgreSQL | 16 | Railway addon or local Docker |
| ORM | SQLAlchemy | 2.0+ | `pip install sqlalchemy[asyncio]` |
| Migrations | Alembic | 1.13+ | `pip install alembic` |
| Auth | PyJWT + bcrypt | 2.12+ / 5.0+ | `pip install PyJWT bcrypt` |
| Validation | Pydantic v2 | 2.0+ | Included with FastAPI |
| File upload | python-multipart | — | `pip install python-multipart` |
| S3 client | boto3 | — | `pip install boto3` |
| Email | Resend SDK | — | `pip install resend` |
| LLM | OpenAI SDK | 1.0+ | `pip install openai` |
| PDF/DOCX | pdfplumber + python-docx | — | Already from POC |
| Testing | pytest + httpx | — | `pip install pytest httpx pytest-asyncio` |
| Env | python-dotenv | — | Already from POC |

```bash
# Full install command
pip install "fastapi[standard]" "sqlalchemy[asyncio]" alembic \
  PyJWT bcrypt python-multipart \
  boto3 resend openai pdfplumber python-docx python-dotenv \
  pytest httpx pytest-asyncio asyncpg
```

---

## Project Structure

```
backend/
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── alembic.ini
├── alembic/
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, CORS, startup
│   ├── config.py                  # Settings from env vars
│   ├── database.py                # SQLAlchemy engine + session
│   │
│   ├── models/                    # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── company.py
│   │   ├── job_posting.py
│   │   ├── candidate.py
│   │   ├── interview.py
│   │   └── evaluation.py
│   │
│   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── job.py
│   │   ├── candidate.py
│   │   ├── interview.py
│   │   └── evaluation.py
│   │
│   ├── routers/                   # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py                # /auth/*
│   │   ├── jobs.py                # /jobs/*
│   │   ├── candidates.py          # /candidates/*
│   │   └── interviews.py         # /interview/*
│   │
│   ├── services/                  # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── job_service.py
│   │   ├── interview_service.py   # AI engine (ported from POC)
│   │   ├── evaluation_service.py
│   │   ├── resume_service.py      # PDF/DOCX parsing (ported from POC)
│   │   ├── email_service.py
│   │   └── prompts.py             # All LLM prompts (from POC)
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── rate_limiter.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── security.py            # JWT, password hashing
│       ├── storage.py             # S3 file upload/download
│       └── token_tracker.py       # LLM cost tracking
│
└── tests/
    ├── conftest.py                # Test fixtures, test DB
    ├── test_auth.py
    ├── test_jobs.py
    ├── test_interviews.py
    └── test_evaluation.py
```

---

## Database Schema

```sql
-- Companies
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    logo_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Users (HR users)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'admin',  -- admin, recruiter, viewer
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Job Postings
CREATE TABLE job_postings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    created_by UUID REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    department VARCHAR(100),
    location VARCHAR(255),
    employment_type VARCHAR(50) DEFAULT 'full_time',  -- full_time, part_time, contract
    required_skills TEXT[],            -- PostgreSQL array
    custom_questions JSONB,            -- HR-defined questions [{question, category}]
    interview_config JSONB DEFAULT '{"num_questions": 8, "style": "standard"}',
    status VARCHAR(20) DEFAULT 'active',  -- active, paused, archived
    interview_link_token VARCHAR(64) UNIQUE,  -- Public link for candidates
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Candidates
CREATE TABLE candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_posting_id UUID REFERENCES job_postings(id) ON DELETE CASCADE,
    name VARCHAR(255),
    email VARCHAR(255),
    resume_url VARCHAR(500),           -- S3 path
    resume_parsed_data JSONB,          -- Extracted resume structure
    status VARCHAR(20) DEFAULT 'invited',  -- invited, in_progress, completed, shortlisted, rejected
    interview_token VARCHAR(64) UNIQUE,    -- Unique per-candidate interview link
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Interviews
CREATE TABLE interviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID REFERENCES candidates(id) ON DELETE CASCADE,
    job_posting_id UUID REFERENCES job_postings(id) ON DELETE CASCADE,
    transcript JSONB DEFAULT '[]',     -- [{role, content, timestamp}]
    planned_questions JSONB,           -- Questions generated for this interview
    current_question_index INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'not_started',  -- not_started, in_progress, completed, abandoned
    -- Integrity signals
    integrity_signals JSONB DEFAULT '{}',  -- {paste_count, timing[], tab_switches, length_variance}
    total_prompt_tokens INTEGER DEFAULT 0,
    total_completion_tokens INTEGER DEFAULT 0,
    cost_usd NUMERIC(8,4) DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Evaluations
CREATE TABLE evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_id UUID UNIQUE REFERENCES interviews(id) ON DELETE CASCADE,
    overall_score NUMERIC(3,1),        -- 0.0–10.0
    skill_match NUMERIC(3,1),
    communication NUMERIC(3,1),
    problem_solving NUMERIC(3,1),
    cultural_fit NUMERIC(3,1),
    summary TEXT,
    strengths TEXT[],
    gaps TEXT[],
    red_flags TEXT[],
    recommendation VARCHAR(20),        -- strong_yes, yes, maybe, no, strong_no
    evaluation_tokens INTEGER,
    evaluation_cost_usd NUMERIC(8,4),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_candidates_job ON candidates(job_posting_id);
CREATE INDEX idx_candidates_status ON candidates(status);
CREATE INDEX idx_interviews_candidate ON interviews(candidate_id);
CREATE INDEX idx_interviews_status ON interviews(status);
CREATE INDEX idx_job_postings_company ON job_postings(company_id);
CREATE INDEX idx_job_postings_link_token ON job_postings(interview_link_token);
CREATE INDEX idx_candidates_interview_token ON candidates(interview_token);
```

---

## API Endpoints — Complete Contract

### Auth Routes (`/auth`)

| Method | Path | Auth | Request Body | Response | Notes |
|--------|------|------|-------------|----------|-------|
| POST | `/auth/signup` | Public | `{email, password, name, company_name}` | `{user, company, access_token}` | Creates company + user |
| POST | `/auth/login` | Public | `{email, password}` | `{access_token, token_type}` | Returns JWT |
| GET | `/auth/me` | JWT | — | `{user, company}` | Current user profile |

**JWT token payload:**
```json
{
  "sub": "user-uuid",
  "company_id": "company-uuid",
  "role": "admin",
  "exp": 1716000000
}
```

**Token expiry:** 7 days (MVP — extend later with refresh tokens)

### Job Routes (`/jobs`)

| Method | Path | Auth | Request Body | Response | Notes |
|--------|------|------|-------------|----------|-------|
| POST | `/jobs` | JWT | `{title, description, department?, location?, employment_type?, required_skills[], custom_questions[]?, interview_config?}` | `{job, interview_link}` | Creates job + generates link token |
| GET | `/jobs` | JWT | — | `{jobs: [{id, title, status, candidate_count, avg_score, created_at}]}` | List company's jobs |
| GET | `/jobs/:id` | JWT | — | `{job, candidates_summary}` | Job detail with stats |
| PUT | `/jobs/:id` | JWT | Partial job fields | `{job}` | Update job |
| DELETE | `/jobs/:id` | JWT | — | `{message}` | Soft-delete (archive) |
| GET | `/jobs/:id/candidates` | JWT | Query: `?status=completed&sort=score&order=desc` | `{candidates: [{id, name, email, status, overall_score, completed_at}]}` | Candidate list with filters |

### Candidate Routes (`/candidates`)

| Method | Path | Auth | Request Body | Response | Notes |
|--------|------|------|-------------|----------|-------|
| GET | `/candidates/:id` | JWT | — | `{candidate, interview, evaluation}` | Full candidate detail |
| POST | `/candidates/:id/shortlist` | JWT | `{note?}` | `{candidate}` | Update status + optional email |
| POST | `/candidates/:id/reject` | JWT | `{note?}` | `{candidate}` | Update status + optional email |

### Interview Routes (`/interview`) — PUBLIC (no JWT, token-based)

| Method | Path | Auth | Request Body | Response | Notes |
|--------|------|------|-------------|----------|-------|
| GET | `/interview/:job_token` | Public | — | `{job_title, company_name, description}` | Landing page data |
| POST | `/interview/start` | Public | `{job_token, candidate_name, candidate_email, resume_file}` | `{interview_token, first_question}` | Parse resume, generate questions, return first Q |
| POST | `/interview/message` | Public | `{interview_token, message, integrity_signals?}` | `{ai_response, progress, is_complete}` | Candidate sends answer, gets next Q |
| GET | `/interview/:interview_token/status` | Public | — | `{status, progress}` | Check if interview is still active |

**Integrity signals payload (sent from frontend with each message):**
```json
{
  "was_pasted": true,
  "time_to_answer_seconds": 185,
  "answer_word_count": 220,
  "tab_switch_count": 2
}
```

### Email Routes (internal, triggered by actions)

| Trigger | Email Type | Recipient | Content |
|---------|-----------|-----------|---------|
| HR invites candidate | Interview invite | Candidate | Interview link + job details |
| Interview completed | Notification | HR user | "New candidate completed interview" |
| HR shortlists | Shortlist email | Candidate | "You've been selected for next round" |
| HR rejects | Rejection email | Candidate | "Thank you for your time" (gentle) |

---

## Week 4: Project Setup + Auth + Database

**Status:** `NOT_STARTED`

### Tasks
- [ ] Initialize FastAPI project with structure above
- [ ] Create `requirements.txt` with all dependencies
- [ ] Create `.env.example` with all required env vars
- [ ] Set up PostgreSQL (local Docker or Railway)
- [ ] Configure SQLAlchemy async engine + session factory
- [ ] Set up Alembic for migrations
- [ ] Create all database models (SQLAlchemy)
- [ ] Generate initial Alembic migration
- [ ] Implement password hashing (bcrypt directly — `bcrypt.hashpw` / `bcrypt.checkpw`)
- [ ] Implement JWT creation and verification (PyJWT — `jwt.encode` / `jwt.decode`)
- [ ] Build auth dependency (`get_current_user` for protected routes)
- [ ] Implement `POST /auth/signup` — create company + user + return JWT
- [ ] Implement `POST /auth/login` — verify password + return JWT
- [ ] Implement `GET /auth/me` — return current user profile
- [ ] Write tests: signup, login, token validation, duplicate email rejection
- [ ] Set up CORS middleware (allow localhost:3000 for frontend dev)
- [ ] Add request logging middleware

**Environment variables (`.env.example`):**
```
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/hr_interviewer

# Auth
JWT_SECRET_KEY=your-secret-key-change-this
JWT_ALGORITHM=HS256
JWT_EXPIRY_DAYS=7

# OpenAI
OPENAI_API_KEY=sk-your-key

# Storage (Supabase)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_BUCKET=resumes

# Email (Resend)
RESEND_API_KEY=re_your-key
FROM_EMAIL=interviews@yourdomain.com

# App
APP_URL=http://localhost:3000
API_URL=http://localhost:8000
```

### Validation
- [ ] `POST /auth/signup` creates company + user in DB, returns JWT
- [ ] `POST /auth/login` returns JWT for valid credentials, 401 for invalid
- [ ] `GET /auth/me` returns user for valid JWT, 401 for missing/expired
- [ ] Duplicate email signup returns 409
- [ ] Invalid email format returns 422
- [ ] Password minimum 8 characters enforced

---

## Week 5: Job CRUD + Resume Upload + Candidate Management

**Status:** `NOT_STARTED`

### Tasks
- [ ] Implement `POST /jobs` — create job posting with auto-generated interview link token
- [ ] Implement `GET /jobs` — list all jobs for current user's company with stats
- [ ] Implement `GET /jobs/:id` — job detail with candidate summary counts
- [ ] Implement `PUT /jobs/:id` — update job (validate ownership)
- [ ] Implement `DELETE /jobs/:id` — soft-delete (set status = archived)
- [ ] Implement `GET /jobs/:id/candidates` — list with status filter + score sorting
- [ ] Generate unique interview link tokens (URL-safe, 32 chars)
- [ ] Set up Supabase Storage client for resume uploads
- [ ] Implement file upload: validate PDF/DOCX, max 10MB, upload to S3
- [ ] Implement `GET /candidates/:id` — full detail with interview + evaluation
- [ ] Implement `POST /candidates/:id/shortlist` — update status
- [ ] Implement `POST /candidates/:id/reject` — update status
- [ ] Write tests: job CRUD, candidate listing, file upload validation
- [ ] Add pagination to list endpoints (limit/offset, default 20)
- [ ] Add input validation: title required, description min 50 chars

### Validation
- [ ] Create job → returns job with interview_link_token
- [ ] List jobs → only shows current company's jobs
- [ ] Job with 5 candidates → stats show correct counts per status
- [ ] Resume upload → file stored in Supabase, URL saved in candidate record
- [ ] Non-PDF/DOCX upload → rejected with 422
- [ ] >10MB upload → rejected with 413
- [ ] Shortlist/reject → candidate status updated, returned correctly

---

## Week 6: AI Interview Engine (Port from POC)

**Status:** `NOT_STARTED`

### Tasks
- [ ] Create `app/services/interview_service.py` — port `InterviewEngine` from POC
- [ ] Create `app/services/resume_service.py` — port resume parser from POC
- [ ] Create `app/services/evaluation_service.py` — port evaluator from POC
- [ ] Move all prompts to `app/services/prompts.py`
- [ ] Implement `GET /interview/:job_token` — return job info for landing page
- [ ] Implement `POST /interview/start`:
  - [ ] Validate job_token exists and job is active
  - [ ] Accept resume file upload + candidate name/email
  - [ ] Create candidate record in DB
  - [ ] Parse resume → save structured data
  - [ ] Generate questions from resume + JD
  - [ ] Create interview record with planned_questions
  - [ ] Return interview_token + first question
- [ ] Implement `POST /interview/message`:
  - [ ] Validate interview_token, interview is in_progress
  - [ ] Save candidate message to transcript
  - [ ] Store integrity signals (paste, timing, tab switches)
  - [ ] Run follow-up detection (vague/contradictory/detailed)
  - [ ] If more questions → return next AI response + progress
  - [ ] If all questions done → trigger evaluation, return completion message
- [ ] Implement interview timeout: auto-complete after 60 min of inactivity
- [ ] Track token usage per API call, accumulate on interview record
- [ ] Handle edge cases:
  - [ ] Empty answer → prompt candidate to provide more detail
  - [ ] Very long answer (>1000 words) → accept but truncate for LLM context
  - [ ] Rapid-fire answers (<5 seconds) → flag in integrity signals
  - [ ] Resume parse failure → fallback to generic questions from JD only

### Interview Flow (Backend Perspective)

```
POST /interview/start
  │
  ├── 1. Lookup job by token → 404 if not found
  ├── 2. Upload resume to S3 → get URL
  ├── 3. Parse resume (pdfplumber/python-docx + LLM) → structured data
  ├── 4. Generate questions (LLM) → list of {question, category, intent, follow_up}
  ├── 5. Create candidate record (status: in_progress)
  ├── 6. Create interview record (status: in_progress, planned_questions)
  ├── 7. Return {interview_token, first_question, total_questions}
  │
  └── If resume parse fails:
      ├── Create candidate with resume_parsed_data = null
      └── Generate questions from JD only (still works, less personalized)

POST /interview/message (called N times, once per candidate answer)
  │
  ├── 1. Validate interview_token → 404 if not found
  ├── 2. Check status == in_progress → 400 if completed/abandoned
  ├── 3. Append candidate message to transcript
  ├── 4. Store integrity signals in interview.integrity_signals
  ├── 5. Evaluate answer quality (LLM): vague/contradictory/detailed
  │   ├── Vague + follow_ups < 2 → return follow-up question
  │   ├── Contradictory → return clarification question
  │   └── Detailed OR max follow-ups → advance to next question
  ├── 6. Append AI response to transcript
  ├── 7. Update token usage
  ├── 8. If all questions answered:
  │   ├── Set interview status = completed
  │   ├── Run evaluation (async or inline for MVP)
  │   ├── Create evaluation record
  │   ├── Update candidate status = completed
  │   ├── Send email notification to HR
  │   └── Return {is_complete: true, message: "Thank you..."}
  └── 9. Return {ai_response, progress: "4/8", is_complete: false}
```

### Validation
- [ ] `POST /interview/start` with valid resume → returns token + first question
- [ ] `POST /interview/message` → returns AI follow-up or next question
- [ ] Vague answer (5 words) → follow-up triggered
- [ ] Detailed answer → moves to next question
- [ ] After all questions → evaluation generated automatically
- [ ] Interview cost tracked correctly in DB
- [ ] Invalid job_token → 404
- [ ] Message to completed interview → 400

---

## Week 7: Evaluation Pipeline + Email + Rate Limiting + Polish

**Status:** `NOT_STARTED`

### Tasks
- [ ] Implement full evaluation pipeline:
  - [ ] Triggered automatically when interview completes
  - [ ] Reads full transcript + resume + JD
  - [ ] Calls LLM with evaluation prompt → structured scores
  - [ ] Saves to evaluations table
  - [ ] Includes integrity signal summary in evaluation
- [ ] Integrity signal aggregation:
  - [ ] Calculate paste_percentage (paste_count / total_answers)
  - [ ] Calculate avg_response_time
  - [ ] Flag timing anomalies (>3 min pause + >200 word instant answer)
  - [ ] Calculate response_length_variance (std dev of word counts)
  - [ ] Generate integrity_summary JSON stored on evaluation
- [ ] Set up Resend email service:
  - [ ] Interview invite email (candidate)
  - [ ] Interview completed notification (HR user)
  - [ ] Shortlist notification (candidate)
  - [ ] Rejection notification (candidate)
- [ ] Implement rate limiting:
  - [ ] `/auth/login` → 5 attempts per minute per IP
  - [ ] `/interview/message` → 30 messages per minute per interview
  - [ ] `/interview/start` → 10 starts per hour per IP
- [ ] Add request validation middleware (max body size: 15MB)
- [ ] Security hardening:
  - [ ] Sanitize all user inputs (prevent XSS in stored data)
  - [ ] Validate UUIDs in path params
  - [ ] Ensure HR users can only see their company's data (tenant isolation)
  - [ ] Rate limit login attempts
  - [ ] CORS: only allow configured origins
- [ ] API documentation: ensure all endpoints have OpenAPI descriptions
- [ ] Error handling: consistent error response format `{detail: string, code: string}`
- [ ] Write integration tests: full flow (signup → create job → interview → evaluation)
- [ ] Write load test: simulate 10 concurrent interviews

### Evaluation Response Shape (returned in `GET /candidates/:id`)

```json
{
  "evaluation": {
    "overall_score": 7.8,
    "scores": {
      "skill_match": 8.0,
      "communication": 7.0,
      "problem_solving": 8.5,
      "cultural_fit": 7.0
    },
    "summary": "Strong candidate with 5 years of marketing experience...",
    "strengths": ["Deep SEO knowledge", "Data-driven approach", "Team leadership"],
    "gaps": ["Limited B2B SaaS experience", "No enterprise marketing exposure"],
    "red_flags": [],
    "recommendation": "yes"
  },
  "integrity": {
    "confidence": "high",
    "paste_percentage": 0.12,
    "avg_response_time_seconds": 95,
    "tab_switch_count": 1,
    "timing_anomalies": 0,
    "length_variance_flag": false,
    "summary": "1 of 8 answers pasted. Response timing consistent. No significant flags."
  }
}
```

### Validation (Week 7 — Backend Complete)
- [ ] Full interview flow works end-to-end via API calls
- [ ] Evaluation scores stored in DB
- [ ] Integrity signals aggregated and included in response
- [ ] Emails send successfully (test with Resend test mode)
- [ ] Rate limiting blocks abuse
- [ ] 10 concurrent interviews complete without errors
- [ ] API response times: <500ms for CRUD, <5s for AI calls
- [ ] All tests pass
- [ ] OpenAPI docs accessible at `/docs`

---

## Artifacts Produced by Phase 1A

These are consumed by Phase 1B (Frontend):

| Artifact | What Frontend Needs |
|----------|-------------------|
| Auth endpoints | Login/signup integration |
| Job CRUD endpoints | Dashboard, job creation wizard |
| Candidate list endpoint | Candidate pipeline table |
| Candidate detail endpoint | Evaluation display, transcript viewer |
| Interview public endpoints | Candidate interview chat UI |
| OpenAPI spec (`/docs`) | Auto-generated API reference |
| Email templates | N/A (backend handles) |
| Error response format | Frontend error handling |

**API base URL for frontend:** `http://localhost:8000` (dev) / `https://api.yourdomain.com` (prod)

---

## Environment Setup Commands

```bash
# Create project
mkdir backend && cd backend

# Virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install "fastapi[standard]" "sqlalchemy[asyncio]" alembic \
  PyJWT bcrypt python-multipart \
  boto3 resend openai pdfplumber python-docx python-dotenv \
  pytest httpx pytest-asyncio asyncpg

# Save requirements
pip freeze > requirements.txt

# Initialize Alembic
alembic init alembic

# Edit alembic/env.py to use your SQLAlchemy models and DATABASE_URL

# Start PostgreSQL (Docker)
docker run -d --name hr-postgres \
  -e POSTGRES_DB=hr_interviewer \
  -e POSTGRES_PASSWORD=devpassword \
  -p 5432:5432 \
  postgres:16

# Run first migration
alembic revision --autogenerate -m "initial schema"
alembic upgrade head

# Run server
uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/ -v
```

---

## Decisions to Make During Phase 1A

| Decision | Options | Default | Impact |
|----------|---------|---------|--------|
| Async vs sync SQLAlchemy | async (asyncpg) / sync (psycopg2) | async | Async is better for concurrent interviews but harder to debug |
| Evaluation timing | Inline (blocking) / Background task | Inline | Background is better UX but adds complexity. Inline for MVP. |
| File storage | Supabase / AWS S3 / Local disk | Supabase | Free tier is generous. Switch to S3 if hitting limits. |
| Email provider | Resend / SendGrid / SES | Resend | Best DX, generous free tier (3K/month) |
| Interview token format | UUID / nanoid / random string | nanoid (URL-safe, 21 chars) | Short enough for URLs, unique enough to prevent guessing |
