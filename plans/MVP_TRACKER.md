# MVP Build Tracker — AI HR Interviewer SaaS

Master tracking file for the MVP build. Each phase has its own detailed plan file.
AI agents: read this file first to understand overall progress, then read the specific phase file you need.

---

## Project Goal

Build a text-based AI interviewer SaaS that lets HR teams screen candidates automatically. MVP = working product with 5–10 pilot customers. Break-even at 3–4 paying customers ($79/month each).

## Phase Overview

| Phase | File | Timeline | Status | Depends On |
|-------|------|----------|--------|------------|
| **Phase 0: POC** | [PHASE_0_POC.md](./PHASE_0_POC.md) | Weeks 1–3 | `NOT_STARTED` | Nothing |
| **Phase 1A: Backend** | [PHASE_1A_BACKEND.md](./PHASE_1A_BACKEND.md) | Weeks 4–7 | `NOT_STARTED` | Phase 0 complete |
| **Phase 1B: Frontend** | [PHASE_1B_FRONTEND.md](./PHASE_1B_FRONTEND.md) | Weeks 8–10 | `NOT_STARTED` | Phase 1A API endpoints ready |
| **Phase 2: Integration & Launch** | [PHASE_2_INTEGRATION_LAUNCH.md](./PHASE_2_INTEGRATION_LAUNCH.md) | Week 11 | `NOT_STARTED` | Phase 1A + 1B complete |

**Total timeline: 11 weeks from start to MVP launch.**

## Status Legend

- `NOT_STARTED` — Work has not begun
- `IN_PROGRESS` — Currently being built
- `BLOCKED` — Waiting on dependency or decision
- `DONE` — Completed and verified

## Dependency Graph

```
Phase 0 (POC)
  │
  ├── Validates: AI interview quality, prompt engineering, cost per interview
  │
  └──▶ Phase 1A (Backend) ──▶ Phase 1B (Frontend) ──▶ Phase 2 (Launch)
       │                       │
       │ Provides:             │ Provides:
       │ • API endpoints       │ • HR dashboard
       │ • DB schema           │ • Candidate interview UI
       │ • AI engine           │ • Landing page
       │ • Auth system         │
       │                       │
       └── 1B can START        │
           Week 8 (while       │
           1A AI engine is     │
           still being         │
           polished Week 6-7)  │
```

**Parallel work opportunity:** Frontend auth pages + dashboard layout (Week 8) can begin once backend auth + job CRUD endpoints are ready (end of Week 5). The AI interview engine (Weeks 6–7) and frontend interview UI (Week 10) are sequential.

## Tech Stack (Final for MVP)

| Layer | Tool | Purpose |
|-------|------|---------|
| Backend | Python 3.12 + FastAPI 0.136+ | API server |
| Database | PostgreSQL + Alembic | Data persistence + migrations |
| Auth | JWT (PyJWT 2.12+ + bcrypt 5.0+) | HR user authentication |
| LLM | OpenAI GPT-4.1-mini (SDK 2.0+) | Interview AI engine |
| PDF/DOCX | pdfplumber + python-docx | Resume parsing |
| Frontend | TanStack Start (RC) + TailwindCSS v4 | HR dashboard + candidate UI |
| File Storage | Supabase Storage | Resume files (PDF/DOCX) |
| Email | Resend | Invites + notifications |
| Backend Hosting | Railway | $5–25/month |
| Frontend Hosting | Vercel / Cloudflare Pages / Railway | Deploy anywhere |
| Monitoring | Sentry | Error tracking |
| Domain | Cloudflare | DNS + SSL |

**Monthly MVP cost: ~$27–50** (before AI API usage)

## Key Decisions Made

1. **Text-only for MVP** — No voice interviews (3–4x COGS, complex infra). Voice is Phase 3.
2. **No Stripe billing for MVP** — Free pilots first. Stripe added in Post-MVP Phase 2.
3. **GPT-4.1-mini only** — Single model, don't add complexity. Fallback to GPT-4.1 only if mini produces bad quality.
4. **Railway for backend** — Cheapest deploy with zero DevOps. Frontend deploys anywhere (Vercel, Cloudflare Pages, etc.).
5. **No RAG for MVP** — Company knowledge base is Post-MVP. Interview uses only resume + JD.
6. **JWT auth, not OAuth** — Simpler to build. Google/LinkedIn OAuth added Post-MVP.
7. **TanStack Start over Next.js** — Client-first framework with selective SSR. Landing page gets SSR for SEO, dashboard/interview run as SPA. Not locked to Vercel.
8. **PyJWT + bcrypt over python-jose + passlib** — passlib is dead (last release Oct 2020). python-jose is semi-maintained. PyJWT and bcrypt are actively maintained industry standards.

## MVP Definition of Done

All of these must be true before declaring MVP complete:

- [ ] HR can sign up, create job posting, get interview link in <5 minutes
- [ ] Candidate can complete text-based AI interview on desktop and mobile
- [ ] AI generates relevant questions from resume + JD
- [ ] AI adapts follow-ups based on answer quality
- [ ] Evaluation produces scores (1–10) + written summary
- [ ] HR can view candidates ranked by score with full transcript
- [ ] HR can shortlist or reject candidates
- [ ] Candidate receives invitation and completion emails
- [ ] System handles 10 concurrent interviews without errors
- [ ] Average interview cost < $0.30
- [ ] Paste detection + response timing signals stored
- [ ] 5–10 pilot companies onboarded

## File Reading Guide for AI Agents

**"What should I build next?"**
→ Read this file → find the first phase with status `IN_PROGRESS` or `NOT_STARTED` → read that phase file

**"I finished a task, what do I update?"**
→ Open the specific phase file → check off the task → if all tasks in a section are done, update the section status → if all sections done, come back here and update the phase status

**"I need to understand how the AI interview works"**
→ Read `PHASE_0_POC.md` for prompts, schemas, and the interview logic

**"I need the API contract / DB schema"**
→ Read `PHASE_1A_BACKEND.md` for complete endpoint list and SQL schema

**"I need the page structure / UI components"**
→ Read `PHASE_1B_FRONTEND.md` for routes, components, and page wireframes

**"I need to deploy"**
→ Read `PHASE_2_INTEGRATION_LAUNCH.md` for deploy config and launch checklist
