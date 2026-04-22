# Phase 2: Integration, Testing & Launch — Week 11

> **Status:** `NOT_STARTED`
> **Depends on:** [Phase 1A Backend](./PHASE_1A_BACKEND.md) + [Phase 1B Frontend](./PHASE_1B_FRONTEND.md) — both must be `DONE`
> **Unlocks:** MVP launch + pilot customer onboarding
> **Tracker:** [MVP_TRACKER.md](./MVP_TRACKER.md)

---

## Goal

Wire everything together, test end-to-end, deploy to production, and onboard 5–10 pilot customers. This is the final sprint before launch.

---

## End-to-End Flow Verification

Before anything else, manually walk through the complete flow and fix everything that breaks.

### Full Flow Checklist

```
HR SIDE:
1. [ ] Open landing page → click "Start Free Trial"
2. [ ] Signup: enter email, password, name, company → account created
3. [ ] Redirected to dashboard → empty state visible
4. [ ] Click "Create New Job" → fill wizard (title, JD, skills)
5. [ ] Job created → interview link generated and shown
6. [ ] Copy interview link → open in incognito/different browser

CANDIDATE SIDE (incognito):
7. [ ] Open interview link → landing page shows job title + company
8. [ ] Click "Start Interview" → upload resume form appears
9. [ ] Enter name + email + upload PDF/DOCX resume
10. [ ] Click "Begin Interview" → loading while resume parses
11. [ ] First AI question appears → references details from resume
12. [ ] Type a vague answer (e.g., "it was good") → AI asks follow-up
13. [ ] Type a detailed answer → AI moves to next question
14. [ ] Complete all questions → "Thank you" screen appears
15. [ ] Close interview tab

HR SIDE (back to original browser):
16. [ ] Check email → "New candidate completed interview" notification received
17. [ ] Open dashboard → job shows 1 candidate
18. [ ] Click into job → candidate appears in table with score
19. [ ] Click candidate → evaluation tab shows scores, summary, strengths, gaps
20. [ ] Click transcript tab → full chat history displayed
21. [ ] Click integrity tab → paste count, timing, tab switches visible
22. [ ] Click "Shortlist" → status updates, confirmation shown
23. [ ] Check candidate email → shortlist notification received
```

### Bug Categories to Watch For

| Category | Common Issues |
|----------|--------------|
| Auth | JWT expired during long session, redirect loops |
| Interview | Resume parse fails → no questions generated, interview hangs |
| AI | Slow response (>10s), token limit exceeded, malformed JSON from LLM |
| UI | Chat doesn't auto-scroll, mobile input keyboard covers chat |
| Email | Not delivered (check spam), wrong links in email body |
| Data | Candidate shows on wrong job, score displays as NaN |
| Security | Interview accessible after completion, candidate can see evaluation |

---

## Testing

### Integration Tests (Backend)

```bash
# Run from backend directory
pytest tests/ -v

# Test coverage
pytest tests/ --cov=app --cov-report=html
```

**Tests to write/verify:**

- [ ] `test_full_flow.py` — signup → create job → start interview → send messages → evaluation created
- [ ] `test_auth.py` — signup, login, token validation, expired token, invalid credentials
- [ ] `test_jobs.py` — CRUD, company isolation (user A can't see user B's jobs)
- [ ] `test_interviews.py` — start, message, completion, timeout, invalid token
- [ ] `test_evaluation.py` — evaluation created on completion, scores in valid range
- [ ] `test_rate_limiting.py` — login rate limit, interview message rate limit
- [ ] `test_security.py` — SQL injection in search, XSS in stored data, CORS enforcement

### Load Testing

```bash
# Install locust
pip install locust

# Create locustfile.py with scenarios:
# - 10 concurrent interviews
# - Each sends 8 messages with 3-second gaps
# - Verify all complete successfully

locust -f tests/locustfile.py --headless -u 10 -r 2 --run-time 5m
```

**Target:**
- [ ] 10 concurrent interviews complete without errors
- [ ] Average AI response time < 5 seconds
- [ ] No 500 errors
- [ ] No database deadlocks

### Frontend Testing

- [ ] Manual test on Chrome, Firefox, Safari (desktop)
- [ ] Manual test on iOS Safari + Chrome (mobile)
- [ ] Manual test on Android Chrome (mobile)
- [ ] Test interview chat on slow 3G (Chrome DevTools throttling)
- [ ] Test resume upload with various PDF/DOCX sizes (100KB to 10MB)
- [ ] Test with screen reader (basic a11y check)

---

## Security Review Checklist

- [ ] **Auth:** Passwords hashed with bcrypt (`bcrypt.hashpw` — not plain text, not MD5)
- [ ] **Auth:** JWT tokens have expiry (7 days)
- [ ] **Auth:** Failed login doesn't reveal if email exists ("Invalid credentials" for both)
- [ ] **Input:** All user inputs sanitized before storage
- [ ] **Input:** File upload validates MIME type (not just extension)
- [ ] **Input:** Max request body size enforced (15MB)
- [ ] **Access:** HR users can only access their own company's data
- [ ] **Access:** Interview endpoints don't expose evaluation data to candidates
- [ ] **Access:** Archived/completed interviews reject new messages
- [ ] **CORS:** Only configured origins allowed (localhost:3000, production domain)
- [ ] **Rate limiting:** Login (5/min), interview message (30/min), interview start (10/hr)
- [ ] **Secrets:** No API keys in code, all in `.env`
- [ ] **Dependencies:** No known vulnerable packages (`pip audit`, `npm audit`)

---

## Deployment

### Backend (Railway)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and link project
railway login
railway init  # or railway link

# Set environment variables in Railway dashboard:
# DATABASE_URL (auto-provisioned PostgreSQL)
# JWT_SECRET_KEY
# OPENAI_API_KEY
# SUPABASE_URL
# SUPABASE_KEY
# RESEND_API_KEY
# FROM_EMAIL
# APP_URL (frontend production URL)

# Deploy
railway up

# Run migrations
railway run alembic upgrade head
```

**`Procfile` (backend root):**
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**`railway.toml`:**
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

### Frontend (Cloudflare Pages, Vercel, or any static host)

TanStack Start builds to a deployable output that works on any platform.

```bash
# Option A: Cloudflare Pages (recommended — free, fast, global CDN)
npm install -g wrangler
cd frontend
npm run build
wrangler pages deploy .output/public

# Option B: Vercel
npm install -g vercel
cd frontend
vercel

# Option C: Railway (same platform as backend)
# Just add the frontend as a separate service in Railway
```

**Set environment variables in your hosting dashboard:**
```
VITE_API_URL=https://api.yourdomain.com
VITE_APP_NAME=HR AI Interviewer
VITE_APP_URL=https://app.yourdomain.com
```

### Domain Setup (Cloudflare)

- [ ] Register domain (e.g., `hirescreen.ai` or `screenai.app`)
- [ ] Add domain to Cloudflare
- [ ] Configure DNS:
  - `app.yourdomain.com` → Frontend host (CNAME)
  - `api.yourdomain.com` → Railway (CNAME)
- [ ] Enable SSL (Cloudflare auto-SSL)
- [ ] Update env vars in Railway + frontend host with production URLs
- [ ] Update CORS origins in backend to include production domain
- [ ] Update email FROM address to use custom domain

### Monitoring Setup

- [ ] **Sentry (backend):** `pip install sentry-sdk[fastapi]`
  - Add `sentry_sdk.init()` in `app/main.py`
  - Set `SENTRY_DSN` env var
- [ ] **Sentry (frontend):** `npm install @sentry/react`
  - Initialize in `app/routes/__root.tsx`
  - Set `VITE_SENTRY_DSN` env var
- [ ] **Health endpoint:** `GET /health` returns `{"status": "ok", "db": "connected"}`
- [ ] **Uptime monitoring:** Use Railway's built-in health checks or free UptimeRobot

### Post-Deploy Verification

- [ ] Backend health endpoint responds: `curl https://api.yourdomain.com/health`
- [ ] Frontend loads: open `https://app.yourdomain.com`
- [ ] Signup works on production
- [ ] Full interview flow works on production
- [ ] Emails send from production (check with real email)
- [ ] SSL certificate valid on both domains
- [ ] API docs accessible: `https://api.yourdomain.com/docs`

---

## Pilot Customer Onboarding

### Pre-Launch Prep
- [ ] Create 3 demo job postings (different roles: engineering, marketing, sales)
- [ ] Run 3 complete demo interviews with sample resumes
- [ ] Take screenshots of: dashboard, candidate detail, evaluation, transcript
- [ ] Write 1-page onboarding guide (PDF or Notion page)

### Onboarding Guide Contents

```markdown
# Getting Started with [Product Name]

## Step 1: Create Your Account (1 minute)
1. Go to app.yourdomain.com/signup
2. Enter your work email, password, and company name
3. Verify your email

## Step 2: Create a Job Posting (3 minutes)
1. Click "Create New Job" on your dashboard
2. Enter the job title and paste your job description
3. Add required skills
4. Click "Create" — your interview link is ready!

## Step 3: Share with Candidates
- Copy the interview link and include it in your application process
- Or paste candidate emails to send interview invites directly

## Step 4: Review Results
- Candidates complete a 15–20 minute AI interview
- You'll get an email when each candidate finishes
- View scores, transcript, and AI evaluation on your dashboard

## What Candidates Experience
- Upload their resume
- Answer 8 adaptive questions via text chat
- Takes ~15–20 minutes
- Professional, conversational tone

## Need Help?
Email: support@yourdomain.com
```

### Pilot Outreach Sequence

**Day 1–3: Invite pilots (from LinkedIn outreach list)**

```
Subject: Your free pilot is ready — [Product Name]

Hi [Name],

Your pilot account is ready. Here's how to get started:

1. Sign up: [link]
2. Create your first job posting (takes 2 minutes)
3. Share the interview link with 5–10 candidates

Your pilot includes 50 free AI interviews for 30 days.

I'd love to hop on a 15-min call at [day] to walk you through it. 
Here's my calendar: [Calendly link]

— [Your name]
```

**Day 7: Check-in**
```
Subject: How's the pilot going?

Hi [Name], quick check — have you had a chance to run any interviews?

If you need help setting up, I'm happy to do a 10-min screenshare.

Common first question: "How do I customize the interview questions?"
→ When creating a job, scroll to Step 3 where you can add custom questions.
```

**Day 21: Conversion pitch**
```
Subject: Pilot ending soon — keep your data

Hi [Name],

Your pilot wraps up in 9 days. Here's what you've done so far:
- [X] candidates interviewed
- [X] hours of screening saved
- Average score: [X]

To keep your data and continue interviewing, pick a plan:
- Starter ($79/mo): 50 interviews — perfect for your volume
- Growth ($199/mo): 200 interviews — if you're ramping up hiring

Early adopter bonus: 20% off your first 3 months with code EARLYBIRD.

[Pick a plan →]
```

### Pilot Success Metrics

| Metric | Target | How to Measure |
|--------|--------|---------------|
| Pilots onboarded | 5–10 | Count signups |
| Interviews completed | 25+ across all pilots | DB query |
| Completion rate | >70% | completed / started |
| HR reviewed evaluations | >60% | Track dashboard visits |
| Pilot → paid conversion | 30–50% | Count upgrades within 30 days |
| Feedback collected | 5+ responses | Scheduled calls |

---

## Post-Launch Immediate Priorities (Week 12+)

These are NOT part of MVP but should be tackled immediately after:

| Priority | Task | Why |
|----------|------|-----|
| 1 | Stripe billing integration | Convert pilots to paying customers |
| 2 | Bug fixes from pilot feedback | Retention |
| 3 | Landing page polish + SEO | Inbound leads |
| 4 | Product Hunt launch prep | Growth spike |
| 5 | Usage tracking dashboard | Know your metrics |

---

## MVP COMPLETE Checklist

All of these must be true:

- [ ] Production backend deployed and healthy
- [ ] Production frontend deployed and accessible
- [ ] Custom domain with SSL working
- [ ] Full interview flow works on production (tested personally)
- [ ] Emails sending from production
- [ ] Monitoring/alerting active (Sentry)
- [ ] 5–10 pilot customers invited
- [ ] Onboarding guide sent to pilots
- [ ] 3 demo interviews completed as proof
- [ ] All security checks passed
- [ ] Load test passed (10 concurrent interviews)

**When all boxes are checked → MVP IS LIVE. Start selling.**

---

## Cost Summary at Launch

| Item | Monthly | Notes |
|------|---------|-------|
| Railway (backend) | $5–25 | Scales with usage |
| Railway PostgreSQL | $0–15 | Free tier covers MVP |
| Vercel (frontend) | $0 | Hobby plan |
| OpenAI API | $10–50 | Depends on interview volume |
| Supabase Storage | $0 | Free tier (1GB) |
| Resend | $0 | Free tier (3K emails/month) |
| Sentry | $0 | Free tier |
| Domain + Cloudflare | $1 | ~$12/year |
| **Total** | **$16–91/month** | **Break-even: 2 Starter customers** |

---

## Files Reference

| File | Purpose | Read When |
|------|---------|-----------|
| [MVP_TRACKER.md](./MVP_TRACKER.md) | Overall progress | Always — start here |
| [PHASE_0_POC.md](./PHASE_0_POC.md) | AI engine, prompts, schemas | Building/debugging AI interview |
| [PHASE_1A_BACKEND.md](./PHASE_1A_BACKEND.md) | API contract, DB schema, backend tasks | Building backend or API integration |
| [PHASE_1B_FRONTEND.md](./PHASE_1B_FRONTEND.md) | UI components, pages, types | Building frontend |
| **This file** | Testing, deploy, launch | Deploying + launching |
| [../ai_hr_interviewer_saa_s_readme.md](../ai_hr_interviewer_saa_s_readme.md) | Full product plan, economics, marketing | Strategy, pricing, marketing |
| [../USER_FLOW_PLAN.md](../USER_FLOW_PLAN.md) | User journey maps | UX decisions |
| [../DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md) | Full roadmap (POC → Enterprise) | Long-term planning |
