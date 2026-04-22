# HR AI Interviewer SaaS

A multi-tenant HR platform that lets companies post jobs, collect candidate
applications via a public link, run an AI-driven screening interview, and
review structured evaluations — all from a single dashboard.

## Features

- **Multi-tenant accounts** — each company has isolated jobs, candidates,
  interviews, and users (admin / recruiter roles).
- **AI screening interviews** — pluggable LLM provider (OpenAI / Anthropic /
  custom) drives a chat-based interview with the candidate; transcript and
  structured evaluation are persisted.
- **Public application links** — candidates apply through a tokenised URL,
  upload a resume (PDF/DOCX, magic-byte validated), and start the interview.
- **Cookie-based session auth** — `HttpOnly` `SameSite=Lax` JWT cookie issued
  by the backend, with `Authorization: Bearer` accepted as a fallback for
  programmatic clients (CLI / scripts).
- **CSRF protection** — header-based (`X-Requested-With: XMLHttpRequest`)
  guard on cookie-authenticated mutating requests.
- **Rate limiting** — slowapi-based, per-route limits, in-memory by default,
  Redis-backed in production via `REDIS_URL`.
- **Account hardening** — bcrypt password hashing, password complexity rules,
  account lockout after repeated failures, JWT revocation on password change
  via `pwd_iat` claim.
- **Audit log** — JSON-formatted security events on stdout for shipping to
  Loki / CloudWatch / Datadog.
- **Email notifications** — Resend integration for invites and interview
  links (gated behind `ENABLE_TEST_EMAILS` in non-prod).
- **Database migrations** — Alembic with async SQLAlchemy 2.0 + aiosqlite
  (dev) / Postgres (prod-ready).

## Architecture

```
                            ┌──────────────────────┐
                            │   Next.js (App)      │
                            │   src/app/**         │
                            └──────────┬───────────┘
                                       │ same-origin fetch
                                       │ /api/backend/* (HttpOnly cookie)
                                       ▼
                            ┌──────────────────────┐
                            │  Next.js rewrite     │
                            │  next.config.ts      │
                            └──────────┬───────────┘
                                       │ proxy
                                       ▼
                            ┌──────────────────────┐
                            │  FastAPI (uvicorn)   │
                            │  app/main.py         │
                            ├──────────────────────┤
                            │  Routers:            │
                            │   /auth /jobs        │
                            │   /candidates        │
                            │   /interview         │
                            ├──────────────────────┤
                            │  Middleware:         │
                            │   CORS, security,    │
                            │   slowapi, log,      │
                            │   request-ID         │
                            └────┬─────────┬───────┘
                                 │         │
                ┌────────────────┘         └─────────────┐
                ▼                                        ▼
   ┌─────────────────────────┐               ┌─────────────────────┐
   │  SQLAlchemy 2.0 (async) │               │  LLM Providers      │
   │  Alembic migrations     │               │  (OpenAI/Anthropic) │
   │  SQLite (dev) / PG      │               │  Resend (email)     │
   │                         │               │  Supabase Storage   │
   └─────────────────────────┘               └─────────────────────┘
```

## Tech Stack

| Layer        | Tech                                                          |
| ------------ | ------------------------------------------------------------- |
| Frontend     | Next.js 15 (App Router), TypeScript, Tailwind v4, shadcn/ui   |
| Backend      | FastAPI 0.136, Pydantic v2, Starlette                         |
| ORM          | SQLAlchemy 2.0 async + Alembic                                |
| DB           | SQLite (dev), PostgreSQL (prod)                               |
| Auth         | PyJWT (HS256), bcrypt, HttpOnly cookie + Bearer fallback      |
| Rate limit   | slowapi + Redis (or in-memory)                                |
| LLM          | OpenAI / Anthropic (pluggable adapter)                        |
| Email        | Resend                                                        |
| Storage      | Supabase Storage (resumes)                                    |

## Prerequisites

- **Python** 3.11+
- **Node.js** 20+
- **Redis** (optional in dev — only required if you want shared rate-limit
  state across processes; the default is in-memory)

## Backend Setup

```bash
git clone <repo-url> hr-ai-nterviewer-saas
cd hr-ai-nterviewer-saas/backend

# 1. Create venv + install
python -m venv venv
./venv/Scripts/activate          # Windows
# source venv/bin/activate       # macOS/Linux
pip install -r requirements.txt

# 2. Configure environment
cp ../.env.example .env
# Generate a strong JWT secret and paste it into .env:
python -c "import secrets; print(secrets.token_hex(64))"

# 3. Apply migrations + load seed data
python scripts/reset_db.py        # dev convenience: drops DB + migrates + seeds

# 4. Run dev server
uvicorn app.main:app --reload --port 8000
```

Visit interactive docs: <http://localhost:8000/docs>

### Database Lifecycle

| Task                          | Command                                                  |
| ----------------------------- | -------------------------------------------------------- |
| Apply pending migrations      | `python -m alembic upgrade head`                         |
| Generate a new migration      | `python -m alembic revision --autogenerate -m "msg"`     |
| Roll back one revision        | `python -m alembic downgrade -1`                         |
| **Dev** wipe + migrate + seed | `python scripts/reset_db.py` *(refuses in production)*   |
| Manual reseed (no wipe)       | `python scripts/seed_data.py`                            |

> **Dev seed credentials** (password is `Password123!` for all):
>
> - `admin@techcorp.com` — admin, TechCorp
> - `recruiter@techcorp.com` — recruiter, TechCorp
> - `admin@innovatelab.com` — admin, InnovateLab

## Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local       # if a template exists
npm run dev
```

Visit <http://localhost:3000>. The frontend talks to the backend through the
same-origin path `/api/backend/*` thanks to the rewrite in
[`frontend/next.config.ts`](frontend/next.config.ts), so the HttpOnly session
cookie works end-to-end without any cross-origin / `SameSite=None` complexity.

To point the frontend at a non-default backend, set
`BACKEND_INTERNAL_URL=http://other-host:8000` before `npm run dev`.

## API Endpoints

All cookie-authenticated mutating endpoints (`POST` / `PUT` / `DELETE`) require
the header `X-Requested-With: XMLHttpRequest`. Bearer-only callers (no cookie
present) are exempt.

### Auth — `/auth`

| Method | Path             | Auth      | Notes                                          |
| ------ | ---------------- | --------- | ---------------------------------------------- |
| POST   | `/auth/signup`   | public    | Creates company + admin user (5/min)           |
| POST   | `/auth/login`    | public    | Sets `hri_session` cookie + returns JWT (20/min)|
| POST   | `/auth/logout`   | session   | Clears cookie (204)                            |
| GET    | `/auth/me`       | session   | Returns current user + company                 |

### Jobs — `/jobs`

| Method | Path                   | Auth    | Notes                            |
| ------ | ---------------------- | ------- | -------------------------------- |
| GET    | `/jobs`                | session | List jobs in caller's company    |
| POST   | `/jobs`                | session | Create job                       |
| GET    | `/jobs/{id}`           | session | Get job + interview link         |
| PUT    | `/jobs/{id}`           | session | Update job                       |
| DELETE | `/jobs/{id}`           | session | Soft-delete                      |

### Candidates — `/candidates`

| Method | Path                        | Auth    | Notes                                   |
| ------ | --------------------------- | ------- | --------------------------------------- |
| GET    | `/candidates`               | session | List candidates (filterable by job)     |
| GET    | `/candidates/{id}`          | session | Candidate detail + evaluations          |
| GET    | `/candidates/{id}/resume`   | session | Stream resume file                      |

### Interview (public) — `/interview`

| Method | Path                          | Auth   | Notes                                            |
| ------ | ----------------------------- | ------ | ------------------------------------------------ |
| POST   | `/interview/apply`            | token  | Upload resume against job interview link (10/min)|
| GET    | `/interview/status/{token}`   | token  | Poll resume parse status                         |
| POST   | `/interview/start/{token}`    | token  | Begin interview session (10/hour)                |
| POST   | `/interview/message`          | token  | Exchange message with AI interviewer (60/min)    |
| POST   | `/interview/finish`           | token  | Mark interview complete                          |

## Security Model

- **Auth** — HttpOnly `hri_session` cookie (SameSite=Lax, Secure in prod) with
  `Authorization: Bearer` fallback for scripts.
- **CSRF** — Mutating cookie requests must send
  `X-Requested-With: XMLHttpRequest`. Bearer-only requests are exempt.
- **Password policy** — Minimum 10 chars, must contain a letter and a digit.
- **Lockout** — 5 failed login attempts triggers a 15-minute lockout (HTTP 423).
- **JWT revocation** — Tokens carry `pwd_iat`; password change rotates the
  user's `password_changed_at` and any earlier token is rejected.
- **File uploads** — Magic-byte sniffed (PDF / DOCX), size-capped, never
  trusted by extension.
- **Audit log** — `AUDIT { json }` lines on stdout for `user.signup`,
  `user.login`, `user.lockout`, `user.password_change`, etc.
- **Rate limit** — Per-route via slowapi; 429 JSON response with
  `Rate limit exceeded: N per window` detail.

## Production Checklist

- [ ] `ENVIRONMENT=production` (enables `Secure` cookie, disables test emails,
      blocks `reset_db.py`)
- [ ] `JWT_SECRET_KEY` set to 64+ hex chars (`secrets.token_hex(64)`)
- [ ] `DATABASE_URL` points to managed Postgres
- [ ] `REDIS_URL` set so rate limits are shared across replicas
- [ ] `RATE_LIMIT_ENABLED=true`
- [ ] `ENABLE_TEST_EMAILS=false`
- [ ] `python -m alembic upgrade head` run on deploy
- [ ] CORS allow-list narrowed to the production frontend origin
- [ ] HTTPS terminator (nginx / load balancer) sets
      `X-Forwarded-For` so per-IP rate limits are accurate
- [ ] Audit log shipped to centralised logging (Loki / CloudWatch / Datadog)

## Project Layout

```
hr-ai-nterviewer-saas/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint, audit logger setup
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── routers/             # auth, jobs, candidates, interview
│   │   ├── services/            # business logic
│   │   ├── middleware/          # rate_limiter, security headers, logging
│   │   ├── models/              # SQLAlchemy ORM
│   │   ├── schemas/             # Pydantic request/response models
│   │   └── utils/               # security, cookies, file_validation, ...
│   ├── alembic/                 # migrations + env.py (async)
│   ├── scripts/
│   │   ├── reset_db.py          # dev: wipe + migrate + seed
│   │   └── seed_data.py         # idempotent seed loader
│   ├── requirements.txt
│   └── hr_interviewer.db        # dev SQLite (gitignored)
├── frontend/
│   ├── src/app/                 # Next.js App Router pages
│   ├── src/lib/api.ts           # fetch wrapper (credentials: include)
│   ├── src/lib/auth.tsx         # AuthProvider (cookie-based)
│   └── next.config.ts           # /api/backend rewrite proxy
└── .env.example                 # canonical environment template
```
