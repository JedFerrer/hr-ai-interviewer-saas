# Development Plan — AI HR Interviewer SaaS

Detailed phase-by-phase development breakdown from Proof of Concept to Enterprise.

---

## Overview

| Phase | Timeline | Team Size | Goal | Exit Criteria |
|-------|---------|-----------|------|--------------|
| **Phase 0: POC** | Weeks 1–3 | 1 dev | Validate AI interview quality | Demo produces useful evaluation |
| **Phase 1: MVP** | Weeks 4–11 | 1–2 devs | Launchable product, 5–10 pilots | Candidates complete interviews, HR reviews results |
| **Phase 2: Post-MVP** | Weeks 12–20 | 1–2 devs | First paying customers | Stripe billing live, 10+ paying customers |
| **Phase 3: Scale** | Months 5–9 | 2–3 devs | Grow revenue, reduce churn | $5K+ MRR, <8% monthly churn |
| **Phase 4: Enterprise** | Month 10+ | 3–5 team | Enterprise deals, expansion | $15K+ MRR, first enterprise contract |

---

## Phase 0: Proof of Concept — Weeks 1–3

### Goal
Validate that an LLM can conduct a screening interview from a resume + job description and produce evaluation output that an HR person finds useful. No UI. Internal demo only.

### Week 1: Resume Parsing + Question Generation

**Tasks:**
- [ ] Set up Python project with Poetry/pip
- [ ] Implement PDF resume parser (pdfplumber)
- [ ] Create resume → structured data extraction prompt
- [ ] Create JD + resume → interview questions prompt
- [ ] Test with 5 sample resumes across different roles
- [ ] Validate question quality (are they relevant? specific?)

**Deliverable:** Script that takes a PDF resume + JD text and outputs 5–8 relevant screening questions.

**Prompts to build:**
```
SYSTEM: You are an expert HR interviewer. Given a job description 
and a candidate's resume, generate screening interview questions.

Categories:
1. Resume verification (2 questions)
2. Role-specific skills (2-3 questions)  
3. Behavioral/situational (2 questions)

Rules:
- Reference specific details from the resume
- Questions should be open-ended
- Difficulty should match the seniority level
```

### Week 2: Interview Simulation + Adaptive Follow-ups

**Tasks:**
- [ ] Build conversational interview loop (CLI-based)
- [ ] Implement adaptive follow-up logic (vague answer → probe deeper)
- [ ] Add conversation history management (sliding window)
- [ ] Test full interview flow end-to-end (you play candidate)
- [ ] Measure token usage per interview (target: <50K total tokens)

**Deliverable:** CLI tool where you paste answers and the AI adapts its next question.

**Key decision:** Follow-up strategy
```
IF answer is < 30 words OR flagged as vague:
  → Generate follow-up probing for specifics
IF answer contradicts resume:
  → Generate clarification question
ELSE:
  → Move to next planned question
```

### Week 3: Evaluation + Scoring Output

**Tasks:**
- [ ] Build evaluation prompt (full transcript → structured scores)
- [ ] Define scoring schema: skill_match, communication, reasoning, cultural_fit (1–10)
- [ ] Generate AI summary with strengths, gaps, and red flags
- [ ] Output as structured JSON
- [ ] Test with 3 mock interviews, show output to 2–3 HR people for feedback
- [ ] Calculate cost per interview (target: <$0.15 with GPT-4.1-mini)

**Deliverable:** Complete POC — resume in → questions → interview → scores + summary out.

**Evaluation output schema:**
```json
{
  "overall_score": 7.8,
  "scores": {
    "skill_match": 8,
    "communication": 7,
    "problem_solving": 8,
    "cultural_fit": 7
  },
  "summary": "Strong technical candidate with...",
  "strengths": ["Deep SEO knowledge", "Strategic thinking"],
  "gaps": ["Limited B2B experience"],
  "red_flags": [],
  "recommendation": "shortlist"
}
```

### POC Tech Stack
| Component | Tool | Cost |
|-----------|------|------|
| Language | Python 3.12 | $0 |
| LLM | OpenAI GPT-4.1-mini | ~$0.10–0.15/interview |
| PDF parsing | pdfplumber | $0 |
| Output | JSON to console | $0 |
| **Total** | | **<$10 for all testing** |

### POC Validation Checklist
- [ ] Generated questions are relevant to the resume + JD
- [ ] Follow-up questions adapt based on answer quality
- [ ] Evaluation scores align with human judgment (±1 point)
- [ ] AI summary is useful to an HR person (get feedback from 2+ people)
- [ ] Cost per interview is under $0.20
- [ ] Full interview takes <50K tokens

---

## Phase 1: MVP — Weeks 4–11

### Goal
Launchable web application for 5–10 pilot customers. Text-based AI interviews with HR dashboard and candidate flow.

### Week 4–5: Backend Foundation

**Tasks:**
- [ ] Set up FastAPI project structure
- [ ] Set up PostgreSQL database with Alembic migrations
- [ ] Design and implement database schema (see below)
- [ ] Implement authentication (email/password, JWT tokens)
- [ ] Build API endpoints: auth, companies, job postings (CRUD)
- [ ] Set up file upload for resumes (S3-compatible storage)
- [ ] Integrate resume parsing from POC into API endpoint
- [ ] Write integration tests for auth + job posting flows
- [ ] Set up CI/CD pipeline (GitHub Actions)

**Database Schema (Core):**
```sql
companies
  id, name, created_at

users (HR users)
  id, company_id, email, password_hash, role, created_at

job_postings
  id, company_id, created_by, title, description,
  required_skills[], custom_questions[], interview_config,
  status (active/paused/archived), created_at

candidates
  id, job_posting_id, name, email, resume_url,
  resume_parsed_data, status (invited/in_progress/completed/shortlisted/rejected),
  created_at

interviews
  id, candidate_id, job_posting_id, transcript[],
  status (in_progress/completed), started_at, completed_at

evaluations
  id, interview_id, overall_score, skill_match, communication,
  problem_solving, cultural_fit, summary, strengths[],
  gaps[], red_flags[], recommendation, created_at
```

**API Endpoints (v1):**
```
POST   /auth/signup
POST   /auth/login
GET    /auth/me

POST   /jobs                    # Create job posting
GET    /jobs                    # List my job postings
GET    /jobs/:id                # Get job details + candidates
PUT    /jobs/:id                # Update job posting
DELETE /jobs/:id                # Archive job posting

GET    /jobs/:id/candidates     # List candidates for job
GET    /candidates/:id          # Get candidate detail + evaluation

POST   /interview/start         # Candidate starts interview (public)
POST   /interview/message       # Candidate sends message (public)
GET    /interview/:token/status # Check interview status (public)

POST   /candidates/:id/shortlist
POST   /candidates/:id/reject
```

### Week 6–7: AI Interview Engine

**Tasks:**
- [ ] Port POC interview logic into service layer
- [ ] Build interview state machine (waiting → in_progress → completed)
- [ ] Implement question generation endpoint (resume + JD → questions)
- [ ] Build conversational turn handler (candidate message → AI response)
- [ ] Add follow-up detection logic (vague/contradictory/detailed)
- [ ] Implement interview completion detection (all questions answered)
- [ ] Build evaluation pipeline (transcript → scores + summary)
- [ ] Add token usage tracking per interview
- [ ] Handle edge cases: empty answers, very long answers, timeout
- [ ] Rate limiting on interview endpoints (prevent abuse)
- [ ] **Interview Integrity — Tier 1 (anti-cheating):**
  - [ ] Paste detection: JS `paste` event listener on answer input, log paste vs typed
  - [ ] Response timing: log time between question shown → answer submitted per question
  - [ ] Flag suspicious patterns: long pause + instant wall of text (>3 min + 200+ words)
  - [ ] Response length variance: flag if all answers are suspiciously same length
  - [ ] Conversational pacing: break complex questions into 2-part exchanges
  - [ ] Store integrity signals per interview in database
  - [ ] Include integrity summary in evaluation JSON output

**Interview State Machine:**
```
                 [candidate clicks link]
                         │
          ┌──────────────▼──────────────┐
          │  INVITED                     │
          │  (link sent, not started)    │
          └──────────────┬──────────────┘
                         │ [uploads resume]
          ┌──────────────▼──────────────┐
          │  RESUME_UPLOADED             │
          │  (parsing in progress)       │
          └──────────────┬──────────────┘
                         │ [starts chat]
          ┌──────────────▼──────────────┐
          │  IN_PROGRESS                 │
          │  (answering questions)       │
          ├──────────────┬──────────────┤
          │              │ [abandoned]   │
          │              ▼              │
          │         INCOMPLETE          │
          │  (partial, auto-saved)      │
          └──────────────┬──────────────┘
                         │ [all questions answered]
          ┌──────────────▼──────────────┐
          │  COMPLETED                   │
          │  (evaluation generated)      │
          └──────────────┬──────────────┘
                         │ [HR reviews]
               ┌─────────┴─────────┐
               ▼                   ▼
          SHORTLISTED          REJECTED
```

### Week 8–9: Frontend — HR Dashboard

**Tasks:**
- [ ] Set up Next.js project with TailwindCSS
- [ ] Implement auth pages (signup, login, email verification)
- [ ] Build onboarding wizard (3-step job creation)
- [ ] Dashboard: list active job postings with stats
- [ ] Job detail page: candidate list with scores, filters, sorting
- [ ] Candidate detail page: evaluation summary, transcript, resume viewer
- [ ] Interview integrity panel: paste count, timing anomalies, tab switches, AI-detection flags
- [ ] Shortlist/reject actions with optional email notifications
- [ ] Copy interview link, email invite (paste emails)
- [ ] Responsive layout (works on tablet)
- [ ] Loading states, error handling, empty states

**Page Structure:**
```
/login
/signup
/onboarding
/dashboard                    → Job list + quick stats
/jobs/:id                     → Candidate pipeline for this job
/jobs/:id/candidates/:id      → Individual candidate review
/jobs/new                     → Create new job posting
/settings                     → Account, company, billing (Phase 2)
```

### Week 10: Frontend — Candidate Interview

**Tasks:**
- [ ] Interview landing page (company branding, job title, CTA)
- [ ] Resume upload screen with drag-drop and parsing feedback
- [ ] Chat interface (message bubbles, typing indicator, progress bar)
- [ ] Implement paste detection in chat input (capture `paste` browser event)
- [ ] Track per-answer timing (question rendered → answer submitted)
- [ ] Track tab visibility changes (`visibilitychange` event) and log count
- [ ] Auto-save interview progress (reconnect on refresh)
- [ ] Thank you / completion screen
- [ ] Mobile-optimized layout (full-screen chat)
- [ ] Handle edge cases: slow AI, network errors, session expiry
- [ ] Accessibility: keyboard navigation, screen reader friendly

### Week 11: Integration, Testing, Deploy

**Tasks:**
- [ ] End-to-end testing: HR creates job → candidate completes interview → HR reviews
- [ ] Load testing: simulate 10 concurrent interviews
- [ ] Security review: auth, input validation, rate limiting, CORS
- [ ] Set up production environment (Railway or Render)
- [ ] Configure custom domain + SSL
- [ ] Set up monitoring (Sentry for errors)
- [ ] Set up transactional email (Resend — interview invites, confirmations)
- [ ] Create 3 demo job postings for pilot onboarding
- [ ] Write pilot customer onboarding guide (1-page)
- [ ] Deploy and onboard first 5 pilot customers

### MVP Tech Stack

| Layer | Technology | Monthly Cost |
|-------|-----------|-------------|
| Frontend | Next.js + TailwindCSS (Vercel) | $0 (hobby) |
| Backend | FastAPI (Railway) | $25–50 |
| Database | PostgreSQL (Railway addon) | $0–15 |
| Cache | Redis (Upstash free tier) | $0 |
| AI | OpenAI GPT-4.1-mini | $50–200 (usage) |
| File Storage | Supabase Storage | $0 (free tier) |
| Email | Resend | $0 (3K emails/month free) |
| Monitoring | Sentry | $0 (free tier) |
| Domain | Namecheap/Cloudflare | $2 |
| **Total** | | **$77–267/month** |

### MVP Definition of Done
- [ ] HR can sign up, create job posting, and get interview link in <5 minutes
- [ ] Candidate can complete text-based AI interview on desktop and mobile
- [ ] AI generates relevant questions based on resume + JD
- [ ] AI adapts follow-ups based on answer quality
- [ ] Evaluation produces scores (1–10) + written summary
- [ ] HR can view candidates ranked by score
- [ ] HR can view full interview transcript
- [ ] HR can shortlist or reject candidates
- [ ] Candidate receives invitation and completion emails
- [ ] System handles 10 concurrent interviews without errors
- [ ] Average interview cost < $0.30

---

## Phase 2: Post-MVP — Weeks 12–20

### Goal
Convert pilots to paying customers. Add features that close deals and reduce churn.

### Week 12–13: Billing + RAG Foundation

**Tasks:**
- [ ] Integrate Stripe: subscription plans (Starter $79, Growth $199, Agency $499)
- [ ] Build billing page: current plan, usage meter, upgrade/downgrade
- [ ] Implement interview usage tracking + overage billing
- [ ] Free trial: 14-day, 10 interviews, no credit card
- [ ] Trial expiry flow: email reminders at day 7, 12, 14
- [ ] Set up pgvector extension for RAG
- [ ] Build document upload (company policies, FAQs) and vectorization pipeline
- [ ] Implement RAG retrieval for candidate Q&A about company

**Billing States:**
```
TRIAL (14 days, 10 interviews)
  │
  ├─ Converts → ACTIVE (Starter/Growth/Agency)
  │                │
  │                ├─ Upgrades/Downgrades
  │                ├─ Hits limit → Overage charges OR soft block
  │                └─ Cancels → CANCELLED (access until period end)
  │
  └─ Expires → EXPIRED (read-only dashboard, no new interviews)
```

### Week 14–15: Interview Quality + Integrity Tier 2 + Email Automation

**Tasks:**
- [ ] **Interview Integrity — Tier 2 (anti-cheating):**
  - [ ] AI-text classifier: run answers through detection model, score probability of AI-generated text
  - [ ] Resume-anchored questions: generate questions that reference specific resume details (company names, dates, projects) that ChatGPT can't fabricate
  - [ ] Writing style consistency: compare linguistic fingerprint across all answers, flag dramatic shifts
  - [ ] Enhanced tab-switch detection: log duration away, correlate with answer quality
  - [ ] Integrity scoring algorithm: combine all signals into single confidence score
  - [ ] HR dashboard: integrity panel with per-answer detail view
- [ ] Bias detection layer: flag evaluations with unusual score variance
- [ ] Improve evaluation prompt with rubric-based scoring
- [ ] Add "confidence" score to evaluations (how certain is the AI)
- [ ] Build email template system (customizable by HR)
- [ ] Automated candidate emails: invite, reminder, shortlisted, rejected
- [ ] HR notification emails: new candidate completed, weekly summary
- [ ] Interview reminder for abandoned sessions (1hr, 24hr, 72hr)

### Week 16–17: Analytics + Export

**Tasks:**
- [ ] Dashboard analytics: interviews/week, avg score, completion rate
- [ ] Time-to-screen metric (interview completed → HR reviewed)
- [ ] Candidate source tracking (which link/email generated the candidate)
- [ ] CSV export: candidate list with scores
- [ ] PDF export: individual candidate evaluation report
- [ ] Comparison view: side-by-side evaluate 2–4 candidates

### Week 18–19: Interview Scheduling + Polish

**Tasks:**
- [ ] Calendar link generation for shortlisted candidates (Calendly-style)
- [ ] "Schedule next interview" action on candidate detail
- [ ] Candidate self-scheduling from shortlist email
- [ ] Settings page: company profile, logo upload, email templates
- [ ] Status page for system health
- [ ] Help/docs page with FAQ and quick-start guide

### Week 20: Optimization + Growth Foundation

**Tasks:**
- [ ] Performance optimization: faster interview responses (<3s target)
- [ ] Implement response caching for repeated similar questions
- [ ] PostHog analytics integration (product usage tracking)
- [ ] Referral program: share link → 1 month free for referrer
- [ ] SEO: landing page, blog setup (Next.js blog or separate)
- [ ] Collect and display customer testimonials from pilots

### Phase 2 New Tech

| Addition | Tool | Monthly Cost |
|----------|------|-------------|
| Payments | Stripe | 2.9% + $0.30 per charge |
| Vector DB | pgvector (built into Postgres) | $0 |
| Analytics | PostHog | $0 (free tier) |
| Scheduling | Cal.com embed OR custom | $0 |

### Phase 2 Exit Criteria
- [ ] Stripe billing live with all 3 plans
- [ ] 10+ paying customers
- [ ] MRR > $1,000
- [ ] Monthly churn < 15%
- [ ] Interview completion rate > 70%
- [ ] RAG-powered company knowledge working for 3+ customers

---

## Phase 3: Scale Features — Months 5–9

### Goal
Grow to $5K–10K MRR. Add features that increase ARPU, reduce churn, and expand addressable market.

### Month 5: Voice Interviews

**WARNING: Voice interviews cost 3–4x more per interview than text ($0.51–0.91 vs $0.14–0.28). Must be priced as premium feature to protect margins.**

**Tasks:**
- [ ] Research and select voice provider (Daily.co vs Twilio vs WebRTC)
- [ ] Build voice interview flow: speech-to-text → AI → text-to-speech
- [ ] Real-time voice UI: recording indicator, playback controls
- [ ] Voice transcription stored alongside text transcripts
- [ ] Voice-specific evaluation signals (pace, clarity — basic only)
- [ ] Enable/disable voice per job posting
- [ ] Mobile voice interview support
- [ ] **Voice-specific pricing logic:**
  - [ ] Voice only available on Growth+ plans
  - [ ] Voice interviews count as 2–3x against quota OR separate voice quota
  - [ ] Track voice vs text usage separately in billing
  - [ ] Voice overage rate: $2.50–3.00/interview (vs $1.00–1.50 text)
- [ ] **Voice consent flow:**
  - [ ] Candidate consent screen before voice interview starts
  - [ ] Disclose recording and AI processing
  - [ ] Offer text fallback option (candidate can switch to text mid-interview)
- [ ] **Voice cost optimization:**
  - [ ] Evaluate self-hosted Whisper for STT (eliminates $0.15–0.25/interview)
  - [ ] Implement audio compression before storage
  - [ ] Set max voice interview duration (30 min cap)

**Technical Approach:**
```
Candidate speaks → WebRTC audio stream
  → Whisper/Deepgram STT → text
  → GPT-4.1-mini processes → response text
  → ElevenLabs/OpenAI TTS → audio stream → candidate hears
Latency target: < 2 seconds end-to-end
```

**Voice Cost Per Interview:**
```
STT (Deepgram):     $0.15–0.25  (15–25 min × $0.01/min)
LLM processing:     $0.10–0.15  (same as text)
TTS (OpenAI):       $0.20–0.40  (~15K chars × $15/1M chars)
Voice infra:        $0.05–0.10  (WebRTC server per session)
Audio storage:      $0.01       (~30MB per recording)
─────────────────────────────────
Total:              $0.51–0.91  (vs $0.14–0.28 text)
```

**Voice Disadvantages to Monitor:**
- Lower completion rate (~60–75% vs ~75–85% text)
- Accessibility issues for non-native speakers
- Mobile battery/bandwidth drain
- Voice recording consent varies by jurisdiction
- HR review slower (must listen or read transcript vs scanning text)

### Month 6: Multi-User + Team Features

**Tasks:**
- [ ] Team roles: Admin, Recruiter, Viewer
- [ ] Admin: manage team members, billing, settings
- [ ] Recruiter: create jobs, review candidates
- [ ] Viewer: read-only access to candidates and reports
- [ ] Team invitation flow (email invite → accept)
- [ ] Activity log: who reviewed/shortlisted/rejected each candidate
- [ ] Candidate assignment: assign reviewers per job
- [ ] Internal notes: team can comment on candidates

### Month 7: ATS Integrations

**Tasks:**
- [ ] Build webhook system for outbound events (interview completed, shortlisted, rejected)
- [ ] Greenhouse integration: push candidates + evaluation data
- [ ] Lever integration: sync job postings and candidates
- [ ] Workable integration: basic data sync
- [ ] Generic webhook: custom URL for any ATS
- [ ] Integration settings page in dashboard
- [ ] Log + retry failed webhook deliveries

**Integration Architecture:**
```
Interview completed → Evaluation generated
  │
  ├─ Webhook fires: POST to customer's ATS webhook URL
  │   Payload: { candidate, scores, summary, transcript_url }
  │
  ├─ Greenhouse: POST /candidates via Harvest API
  ├─ Lever: POST /opportunities via Lever API  
  └─ Workable: POST /candidates via Workable API
```

### Month 8: Custom Branding + Templates

**Tasks:**
- [ ] White-label interview pages: company logo, colors, custom CSS
- [ ] Custom email templates with company branding
- [ ] Interview template library (pre-built for common roles)
  - Software Engineer, Marketing Manager, Sales Rep, Customer Support, etc.
- [ ] Template marketplace: share/import templates
- [ ] Custom domain for interview links (interviews.company.com) via CNAME

### Month 9: API + Advanced Analytics

**Tasks:**
- [ ] Public REST API for customers to build integrations
- [ ] API key management in dashboard
- [ ] API documentation (auto-generated from FastAPI OpenAPI spec)
- [ ] Rate limiting per API key
- [ ] Advanced analytics dashboard:
  - Hiring funnel visualization (applied → screened → shortlisted → hired)
  - Score distribution charts
  - Time-to-screen trends
  - Completion rate by device, time of day
  - Candidate source effectiveness
- [ ] Weekly email digest for HR: summary of all activity

### Phase 3 New Tech / Costs

| Addition | Tool | Monthly Cost |
|----------|------|-------------|
| Voice (STT) | Deepgram | ~$0.01/min (~$0.20/interview) |
| Voice (TTS) | OpenAI TTS | ~$0.015/1K chars (~$0.30/interview) |
| Voice infra | Daily.co | $0–99/month |
| Audio storage | S3 | ~$0.01/interview |
| Hosting upgrade | Railway Pro | $200/month |
| **Total Increment** | | **+$200–500/month** |

**Voice margin warning:** At 1,000 voice interviews/month, voice COGS alone = ~$700. Agency plan ($499) would be unprofitable if all interviews are voice. Voice must be priced as premium or quota-limited.

### Phase 3 Exit Criteria
- [ ] Voice interviews available and used by 20%+ of customers
- [ ] Multi-user teams working for 5+ companies
- [ ] At least 1 ATS integration live with real customers
- [ ] MRR > $5,000
- [ ] Monthly churn < 8%
- [ ] Public API with 3+ customers using it

---

## Phase 4: Enterprise & Expansion — Month 10+

### Goal
Land first enterprise contracts. Build for compliance, scale, and expansion.

### Month 10–11: Enterprise Auth + Compliance

**Tasks:**
- [ ] SSO/SAML authentication (Okta, Azure AD)
- [ ] Multi-tenant data isolation (row-level security or schema per tenant)
- [ ] Audit logs: every action logged with timestamp, user, IP
- [ ] Data retention policies: configurable per company (auto-delete after X days)
- [ ] Right to deletion: candidate can request data removal
- [ ] GDPR consent management: explicit consent before interview
- [ ] SOC 2 Type 1 preparation:
  - Access controls documentation
  - Encryption at rest and in transit
  - Incident response procedures
  - Vendor risk management
- [ ] Security questionnaire template (pre-filled for enterprise sales)

### Month 12–13: Video + Advanced AI

**Tasks:**
- [ ] Video interview recording (candidate records video, AI evaluates transcript)
- [ ] Video playback in HR dashboard (marked at key moments)
- [ ] Multi-language interview support (Spanish, French, German, Portuguese)
- [ ] Self-hosted LLM option for data-sensitive clients (Llama 3 via Ollama/vLLM)
- [ ] A/B testing framework for interview prompts (optimize question quality)
- [ ] Fine-tuned evaluation model (trained on HR feedback from real interviews)

### Month 14+: Platform Expansion

**Tasks:**
- [ ] ATS marketplace listing (Greenhouse, Lever app stores)
- [ ] Channel partner program (HR consultancies resell)
- [ ] Interview analytics benchmarking (compare across industry)
- [ ] Diversity and inclusion metrics in evaluation reports
- [ ] Candidate CRM: track candidates across multiple job applications
- [ ] Internal mobility: use for internal promotions/transfers
- [ ] Assessment modules: skills tests, written exercises (beyond interviews)

### Enterprise Pricing

| Feature | Included |
|---------|---------|
| Unlimited interviews | Fair use (up to 5,000/month) |
| All integrations | ATS, SSO, webhooks, API |
| Dedicated support | Slack channel, SLA |
| Custom branding | Full white-label |
| Data residency | Choose region (US, EU) |
| SLA | 99.9% uptime guarantee |
| **Price** | **$1,500–$5,000/month** |

### Phase 4 Infrastructure Scale

| Component | Change | Monthly Cost |
|-----------|--------|-------------|
| Hosting | Dedicated servers / AWS | $500–1,000 |
| Database | RDS Multi-AZ | $200–400 |
| Redis | ElastiCache | $50–100 |
| CDN | CloudFront | $50–100 |
| Monitoring | Datadog/New Relic | $100–200 |
| Security | WAF, DDoS protection | $100–200 |
| **Total Infrastructure** | | **$1,000–2,000/month** |

### Phase 4 Exit Criteria
- [ ] 1+ enterprise customer signed ($1,500+/month)
- [ ] SSO working with at least 2 identity providers
- [ ] SOC 2 Type 1 report in progress
- [ ] MRR > $15,000
- [ ] Video interviews available
- [ ] Multi-language support live (2+ languages)

---

## Engineering Principles (All Phases)

### Code Quality
- Type hints on all Python code (mypy strict)
- TypeScript strict mode for frontend
- API-first: OpenAPI spec before implementation
- Every endpoint has integration tests
- CI runs tests + linting on every PR

### Security
- All user input validated and sanitized
- Parameterized queries only (no raw SQL)
- JWT with short expiry + refresh tokens
- File uploads scanned and type-validated
- Interview tokens are single-use, time-limited
- Rate limiting on all public endpoints
- OWASP Top 10 reviewed every phase

### Data
- Soft deletes on all models (never lose candidate data accidentally)
- Database backups: daily automated, tested monthly
- PII encrypted at rest
- Interview transcripts stored as structured JSON (queryable)

### DevOps
- Single command deploy (Git push → auto deploy)
- Environment-based config (no secrets in code)
- Health check endpoint monitored
- Error alerting via Sentry → Slack
- Database migrations are forward-only (no destructive changes)

---

## Risk Register Per Phase

| Phase | Risk | Likelihood | Impact | Mitigation |
|-------|------|-----------|--------|-----------|
| POC | AI questions are too generic | Medium | Blocks MVP | Iterate on prompts, test with real HR feedback |
| MVP | Candidates use ChatGPT to answer | High | Evaluation quality drops | Integrity Tier 1 (paste detection, timing, follow-up probes) |
| MVP | Pilot customers don't engage | Medium | No validation | Weekly check-ins, onboard personally, iterate fast |
| MVP | Interview completion rate <50% | Low | Product fails | A/B test UX, shorter interviews, mobile optimization |
| Post-MVP | Churn after trial expires | High | Low revenue | Prove value during trial, email sequences, human follow-up |
| Scale | Voice interview margins negative | High | Unsustainable | Premium pricing, voice quotas, self-hosted STT |
| Scale | Voice latency too high (>3s) | Medium | Voice unusable | Pre-process common phrases, optimize pipeline, fallback to text |
| Scale | ATS integration breaks | Medium | Customer churn | Webhook retry logic, customer alerting, dedicated support |
| Enterprise | SOC 2 takes too long | Medium | Blocks deals | Start early (Month 8), hire consultant |
| Enterprise | Self-hosted LLM quality too low | Low | Feature useless | Use only for basic screening, keep cloud LLM as primary |

---

## Milestone Summary

```
Week 1-3:   POC ✓ → "AI can interview and evaluate"
Week 4-11:  MVP ✓ → "Product works, 5-10 pilots"
Week 12-20: Post-MVP ✓ → "10+ paying customers, $1K+ MRR"
Month 5-9:  Scale ✓ → "Voice, integrations, $5K+ MRR"
Month 10+:  Enterprise → "Compliance, $15K+ MRR"
```
