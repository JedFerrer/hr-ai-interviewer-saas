# AI HR Interviewer SaaS — Product Plan

An AI-powered HR interviewing platform that automates first-round candidate screening, conducts structured interviews, and generates evaluation reports for recruiters and hiring teams.

---

## 🧠 Problem Statement

Hiring managers spend **8–23 hours per hire** on first-round screening alone. For a company filling 10 roles/month with 50 applicants each, that's ~500 manual interviews. Most are unstructured, inconsistent, and produce subjective notes — leading to bad hires that cost 30–50% of annual salary.

**Our solution:** Replace manual first-round screening with an AI interviewer that is consistent, available 24/7, and produces data-driven evaluation reports — saving HR teams 70%+ of screening time.

---

## 🎯 Target Customers

### Primary — SMBs & Staffing Agencies (Launch Market)

| Segment | Size | Why They Buy | Willingness to Pay |
|---------|------|-------------|-------------------|
| **Staffing/recruitment agencies** | 10–200 employees | Screen 100s of candidates/week; time = money | High — direct ROI on recruiter hours |
| **SMB companies (50–500 employees)** | HR team of 1–5 | No bandwidth for proper screening; need structure | Medium — save headcount costs |
| **High-volume hiring** (retail, hospitality, BPOs) | Any size | 100+ hires/month; repetitive screening | High — clear unit economics |

### Secondary — Growth Market

| Segment | Why They Buy |
|---------|-------------|
| **Mid-market companies (500–2000)** | Standardize screening across departments |
| **Remote-first companies** | Async interviews across timezones |
| **Universities/bootcamps** | Mock interviews for students (B2B2C) |

### Who We Do NOT Target (Yet)
- Enterprise (>2000 employees) — long sales cycles, compliance requirements
- Technical coding interviews — saturated market (HackerRank, CodeSignal)

---

## 🛤️ Development Phases: POC → MVP → Scale

### Phase 0: Proof of Concept (POC) — 2–3 weeks

**Goal:** Validate that AI can conduct a useful screening interview and produce actionable output. No UI needed. Internal demo only.

**Build:**
- CLI or notebook-based flow
- Hardcoded job description + sample resume (PDF)
- LLM generates 5–8 screening questions from resume + JD
- Simulated text-based Q&A (you answer as candidate)
- LLM produces structured evaluation JSON (scores + summary)

**Tech:**
- Python script + OpenAI API (GPT-4.1-mini for cost)
- Simple PDF parsing (PyMuPDF or pdfplumber)
- No database, no frontend, no auth

**Validate:**
- Are the generated questions relevant?
- Is the evaluation useful to an HR person?
- What's the API cost per interview? (target: <$0.15)

**Cost:** ~$0/month (OpenAI API credits only, <$10 total)

---

### Phase 1: MVP — 6–8 weeks

**Goal:** Launchable product for 5–10 pilot customers. Text-based AI interviews with a working HR dashboard and candidate flow.

**Features:**

| Area | What's Included |
|------|----------------|
| **HR Portal** | Create job postings, define JD + required skills, add custom questions |
| **Candidate Flow** | Receive interview link via email, complete text-based AI interview in browser |
| **AI Interview** | Resume parsing → question generation → adaptive chat → follow-ups → evaluation |
| **Scoring** | Skill match, communication, reasoning scores (1–10) + AI summary |
| **HR Dashboard** | Candidate list with rankings, interview transcripts, shortlist/reject actions |
| **Auth** | Email/password login for HR users |

**NOT in MVP:**
- Voice/video interviews
- RAG company knowledge base
- ATS integrations
- Multi-tenant billing
- Advanced analytics

**Tech Stack:**
- **Frontend:** Next.js + TailwindCSS
- **Backend:** FastAPI + PostgreSQL + Redis
- **AI:** OpenAI GPT-4.1-mini (cost-optimized) with GPT-4.1 fallback
- **Resume parsing:** pdfplumber + LLM extraction
- **Email:** Resend (free tier: 3,000 emails/month)
- **Hosting:** Railway or Render ($25–50/month)
- **File storage:** Supabase Storage or S3-compatible (free tier)

**MVP Cost:** ~$100–150/month infrastructure + ~$50–200/month OpenAI API

---

### Phase 2: Post-MVP — Weeks 9–16

**Goal:** Paying customers. Improve quality, add features that close deals.

**Features:**
- RAG-based company knowledge integration (policies, benefits, culture docs)
- Interview scheduling (calendar link generation)
- Email notifications and reminders for candidates
- Bias detection flags in evaluation reports
- CSV/PDF export of candidate reports
- Basic analytics (interviews/week, avg scores, time-to-screen)
- Stripe billing integration

**Tech Additions:**
- Vector DB: Supabase Vector (pgvector) — $0 additional cost
- Stripe for payments
- Cron jobs for email reminders (Celery or simple scheduler)

---

### Phase 3: Scale Features — Months 5–9

**Goal:** Grow revenue, reduce churn, expand market.

**Features:**
- Voice-based interviews (Daily.co or Twilio)
- Multi-user HR team access with roles (admin, recruiter, viewer)
- ATS integrations (Greenhouse, Lever, Workable via API)
- Custom branding (white-label interview pages)
- Candidate self-scheduling
- Interview templates library
- Webhook/API for customer integrations

---

### Phase 4: Enterprise & Expansion — Month 10+

**Features:**
- Video interview recording and playback
- Advanced analytics dashboard (hiring funnel, diversity metrics)
- SSO/SAML authentication
- Multi-tenant architecture with data isolation
- Self-hosted LLM option (Llama 3) for data-sensitive clients
- SOC 2 compliance preparation
- API marketplace for third-party integrations

---

## 💰 Unit Economics & Profitability Model

### Cost Per Interview Breakdown

| Cost Component | Per Interview | Notes |
|---------------|--------------|-------|
| **LLM API — Question Generation** | $0.02–0.04 | GPT-4.1-mini, ~2K input + 1K output tokens |
| **LLM API — Chat (8 turns avg)** | $0.06–0.12 | GPT-4.1-mini, ~800 tokens/turn |
| **LLM API — Evaluation** | $0.03–0.05 | GPT-4.1-mini, structured output |
| **Resume Parsing** | $0.01–0.02 | PDF extraction + LLM cleanup |
| **Infrastructure (amortized)** | $0.02–0.05 | Server, DB, storage per interview |
| **Email (invite + result)** | $0.001 | Resend/SES |
| **Total COGS per interview** | **$0.14–0.28** | Conservative estimate |

### Fixed Monthly Costs

| Item | MVP Phase | Scale Phase |
|------|-----------|-------------|
| Hosting (Railway/Render) | $50 | $200 |
| PostgreSQL (managed) | $0–15 | $50 |
| Redis | $0 | $30 |
| Domain + SSL | $2 | $2 |
| Email service | $0 (free tier) | $20 |
| Monitoring (Sentry) | $0 (free tier) | $26 |
| **Total Fixed** | **~$52–67/month** | **~$328/month** |

### Revenue Model

**Primary: Subscription + Usage Hybrid**

| Plan | Price/month | Included Interviews | Overage | Target Customer |
|------|------------|--------------------|---------|-----------------| 
| **Starter** | $79/month | 50 interviews | $1.50/each | Solo recruiters, small HR teams |
| **Growth** | $199/month | 200 interviews | $1.00/each | SMBs, growing companies |
| **Agency** | $499/month | 1,000 interviews | $0.50/each | Staffing agencies |
| **Enterprise** | Custom ($1,500+) | Unlimited | — | Mid-market+ |

**Why this pricing works:**
- A recruiter spending 30 min per phone screen at $35/hr costs **$17.50 per manual screen**
- Our cost per AI interview: **~$0.20**
- Customer price per interview: **$1.00–1.58**
- We deliver **10–17x savings** to the customer while running **5–8x margins**

### Break-Even Analysis

| Scenario | Monthly Revenue | Monthly Cost | Profit |
|----------|---------------|-------------|--------|
| **5 Starter customers** | $395 | $67 fixed + $35 API = **$102** | **+$293** |
| **10 Starter + 3 Growth** | $1,387 | $67 fixed + $195 API = **$262** | **+$1,125** |
| **20 Starter + 10 Growth + 2 Agency** | $4,578 | $328 fixed + $780 API = **$1,108** | **+$3,470** |

**Break-even point: 3–4 Starter customers** (covers all fixed costs + API).

### Path to $10K MRR

| Milestone | Customer Mix | MRR | Timeline |
|-----------|-------------|-----|----------|
| Break-even | 4 Starter | $316 | Month 2–3 |
| Sustainable | 15 Starter + 5 Growth | $2,180 | Month 4–6 |
| Growth | 20 Starter + 10 Growth + 5 Agency | $6,075 | Month 7–9 |
| Scale | 25 Starter + 15 Growth + 10 Agency + 2 Enterprise | $13,960 | Month 10–12 |

---

## 📊 Go-To-Market Strategy & Marketing Playbook

### Marketing Budget: $0 Phase (Month 1–3)

Your only costs are your time + the tools below. No paid ads until Month 6+.

| Channel | Cost | Expected Result | Time/Week |
|---------|------|----------------|-----------|
| LinkedIn personal outreach | $0 | 3–5 pilot signups | 5 hrs |
| Cold email to agencies | $0 (Apollo free tier) | 1–2 agency pilots | 3 hrs |
| Reddit/IndieHackers posts | $0 | Brand awareness, 50–100 signups | 2 hrs |
| 2 SEO blog articles/month | $0 | Long-term inbound (starts Month 3+) | 4 hrs |
| Product Hunt prep | $0 | 500–2000 signups on launch day | 2 hrs (prep) |
| **Total** | **$0** | **5–10 pilot companies** | **~16 hrs/week** |

### Phase 1: Founder-Led Sales (Month 1–3)

**Week 1–2: Build Your Hit List**
- Use LinkedIn Sales Navigator free trial → search "Recruiter", "Talent Acquisition", "Staffing Agency Owner"
- Export 200 names from Apollo.io (free 25 credits/month) with emails
- Prioritize: staffing agencies (highest pain), then SMB HR managers

**Week 2–4: LinkedIn Outreach (10 DMs/day)**

Script template:
> "Hey [Name], I noticed you run a staffing agency / manage recruiting at [Company]. I built an AI tool that does first-round phone screens for $1.50/interview instead of $17.50 manually. Early customers are screening 50+ candidates/week hands-free. Would you want to try it free for 2 weeks? Happy to set up a 10-min demo."

**Conversion expectations:**
- 10 DMs/day × 5 days = 50/week
- 15–20% reply rate = 8–10 conversations
- 30% of conversations → demo = 3 demos/week
- 50% demo → pilot signup = 1–2 pilots/week
- **After 4 weeks: 5–8 pilot companies**

**Week 3–4: Cold Email Outreach to Staffing Agencies**

Tools (all free or near-free):
- **Apollo.io** — find staffing agency contacts (free tier: 25 leads/month)
- **Resend** — send emails (free tier: 3K/month)
- **Google Sheets** — track pipeline

Email template:
> Subject: Screening 100 candidates/week without hiring more recruiters
>
> Hi [Name],
>
> I built [Product Name] — an AI that screens candidates for you via text chat. It reads their resume, asks adaptive questions based on the job description, and generates a scored evaluation report.
>
> Your recruiters get back 70% of their screening time. It costs $0.20 per screen vs $17.50 manually.
>
> I'm offering 10 agencies a free 30-day pilot. Want in?
>
> [Demo link / Calendly link]

**Free Pilot Program (5–10 companies)**
- 30 days free, 50 interviews included
- Requirements from them: weekly 15-min feedback call + written testimonial if satisfied
- At day 21: share pricing, offer 20% early-bird discount for annual commitment
- Target: 30–50% pilot-to-paid conversion

### Phase 2: Content + Product Hunt (Month 3–5)

**Content Marketing (SEO Play)**

Write 2 articles/month targeting these keywords:
1. "AI interview tool for recruiters" (low competition, high intent)
2. "how to screen 100 candidates fast" (problem-aware)
3. "automated candidate screening software" (comparison/buying intent)
4. "AI vs manual phone screen cost comparison" (data-driven, shareable)
5. "how to reduce time-to-hire" (broad awareness)
6. "staffing agency automation tools 2026" (niche, high intent)

Publish on: your blog (Next.js /blog route, SEO-optimized) + cross-post to LinkedIn + Medium

**Product Hunt Launch (Month 3–4)**

Prep checklist:
- [ ] 3-min demo video (Loom or screen recording)
- [ ] Landing page with clear value prop + pricing
- [ ] "Maker" story: why you built it, early results from pilots
- [ ] Pre-launch: tell your LinkedIn network, get 50+ people ready to upvote at launch
- [ ] Launch on Tuesday (best day for PH)
- [ ] Expected: 300–2,000 signups, 5–15 convert to paid within 30 days

**Reddit/IndieHackers**
- Post build-in-public updates on r/SaaS, r/startups, r/recruiting, r/humanresources
- Share transparent revenue numbers on IndieHackers
- Avoid being salesy — share what you learned, let people discover the product

### Phase 3: Referral + Partnerships (Month 5–8)

**Referral Program**
- Existing customer refers → they get 1 month free
- Referred company → gets 14-day extended trial (vs standard 7-day)
- Track via unique referral links in dashboard
- Expected: 10–15% of customers refer at least once

**ATS Integration Partnerships**
- Build integrations with: Greenhouse, Lever, JazzHR, BambooHR
- Get listed in their marketplace/app directory (free distribution)
- Each marketplace listing = 50–200 monthly visitors with high purchase intent

**Staffing Industry Communities**
- ASA (American Staffing Association) membership — attend virtual events
- TechServe Alliance (IT staffing niche)
- LinkedIn Groups for HR professionals (share content, not pitches)

### Phase 4: Paid Acquisition (Month 6+ only if MRR > $3K)

| Channel | Monthly Budget | Expected CAC | Target |
|---------|---------------|-------------|--------|
| Google Ads ("AI interview tool") | $500–1,000 | $150–250 | 3–5 customers |
| LinkedIn Ads (HR managers) | $500 | $200–400 | 1–3 customers |
| Retargeting (visitors who didn't convert) | $200 | $80–120 | 2–3 customers |

**Only start paid ads when:**
- You have 10+ paying customers (product-market fit signal)
- Gross margins are >70%
- LTV:CAC ratio is >3:1
- You can track attribution end-to-end

### Marketing KPIs by Month

| Month | Target MRR | Customers | Primary Channel |
|-------|-----------|-----------|----------------|
| 1 | $0 | 5–8 free pilots | LinkedIn DMs |
| 2 | $237–395 | 3–5 paid | Pilot conversions |
| 3 | $800–1,200 | 10–15 paid | Cold email + referrals |
| 4 | $1,500–2,500 | 18–25 paid | Product Hunt + SEO starting |
| 5 | $2,500–4,000 | 25–35 paid | Referrals + content + ATS integrations |
| 6 | $4,000–6,000 | 35–50 paid | All channels + first paid ads |

### Free Tools for Marketing

| Tool | Purpose | Cost |
|------|---------|------|
| **Apollo.io** | Lead search + email finding | Free (25 leads/month) |
| **Resend** | Transactional + cold email | Free (3K/month) |
| **Canva** | Social media graphics, PH assets | Free |
| **Loom** | Demo videos, async pitches | Free (25 videos) |
| **Google Search Console** | SEO tracking | Free |
| **PostHog** | Product analytics + conversion tracking | Free (1M events/month) |
| **Calendly** | Demo scheduling | Free |
| **Notion** | CRM/pipeline tracking (early stage) | Free |

---

## 🏗️ System Architecture

### Tech Stack Summary

| Layer | Technology | Why |
|-------|-----------|-----|
| **Frontend** | Next.js + TailwindCSS | Fast, SEO-friendly, great DX |
| **Backend** | FastAPI + PostgreSQL | Async-native, fast, type-safe |
| **Cache/Queue** | Redis + Celery | Background jobs, rate limiting |
| **AI** | OpenAI GPT-4.1-mini (primary) | Best cost/quality ratio |
| **AI Fallback** | GPT-4.1 or Claude | Complex evaluations |
| **Resume Parsing** | pdfplumber + LLM | No expensive third-party service |
| **Vector DB** | pgvector (Supabase) | RAG for company docs, no extra service |
| **Email** | Resend | Great DX, generous free tier |
| **File Storage** | S3-compatible | Resume and transcript storage |
| **Payments** | Stripe | Industry standard |
| **Monitoring** | Sentry + PostHog | Error tracking + product analytics |

### End-to-End Workflow

```
1. HR creates job posting → defines JD + skills + custom questions
2. System generates shareable interview link
3. Candidate clicks link → uploads resume → enters AI interview
4. AI parses resume → generates adaptive questions → conducts chat interview
5. AI evaluates responses → generates structured scores + summary
6. HR reviews candidates in dashboard → shortlist/reject → schedule next round
```

---

## 🆚 Competitive Landscape

| Feature | Us | HireVue | Paradox AI | HackerRank |
|---------|-----|---------|-----------|------------|
| Text AI interview | ✅ | ❌ | ✅ (basic chatbot) | ❌ |
| Adaptive follow-ups | ✅ | ❌ | ❌ | ❌ |
| Resume verification | ✅ | ❌ | ❌ | ❌ |
| Company knowledge RAG | ✅ | ❌ | ❌ | ❌ |
| Structured scoring | ✅ | ✅ | ❌ | ✅ (coding only) |
| SMB-friendly pricing | ✅ ($79+) | ❌ ($25K+/yr) | ❌ ($1K+/mo) | ❌ ($300+/mo) |
| Self-serve onboarding | ✅ | ❌ | ❌ | ✅ |

**Our wedge:** Affordable, self-serve AI screening for SMBs and staffing agencies — a market HireVue and Paradox ignore because of their enterprise focus.

---

## 🛡️ Interview Integrity — Anti-Cheating System

### The Problem

With text-based AI interviews, candidates can copy questions into ChatGPT and paste answers back. This undermines the evaluation quality and HR trust in the platform.

### Strategy: Detection Over Prevention

We do **not block cheating** — we **detect and surface signals** to HR. The goal is to raise the cost of cheating so it's easier to just answer honestly, and give HR the data to make informed decisions.

### Tier 1: Built Into MVP (Low Effort, High Impact)

| Signal | How It Works | Shown to HR |
|--------|-------------|-------------|
| **Paste detection** | JavaScript `paste` event listener on input field. Log whether answer was typed character-by-character or pasted as a block. | "3 of 8 answers were pasted" |
| **Response timing** | Log time between question shown → answer submitted. Flag answers with long delay then instant wall of text (>3 min pause + 200+ words at once). | Per-answer timing graph |
| **Adaptive follow-up probes** | After every answer, AI asks a specific follow-up referencing details from the candidate's own response. AI-generated answers fall apart under specificity. | Follow-up quality visible in transcript |
| **Conversational pacing** | Break complex questions into 2-part exchanges. Forces candidate to answer incrementally — makes copy-paste workflow 2x slower. | Natural conversation flow |
| **Response length variance** | Humans write answers of varying length (20–200 words). AI outputs are unnaturally consistent (~150 words each). Flag low variance. | "Answer length suspiciously uniform" |

### Tier 2: Post-MVP

| Signal | How It Works | Shown to HR |
|--------|-------------|-------------|
| **Tab/focus detection** | `document.visibilitychange` + `blur` events detect when candidate switches browser tabs during interview. | "Candidate left interview tab 6 times" |
| **AI-text classifier** | Run answers through detection model. Score likelihood of AI-generated text. | "Answer #5: 78% likely AI-generated" |
| **Resume-anchored questions** | Questions reference specific resume details (company names, dates, project names) that ChatGPT can't fabricate without context. | Higher specificity = harder to fake |
| **Writing style consistency** | Compare linguistic fingerprint across all answers. Flag dramatic shifts in vocabulary or structure between answers. | "Inconsistent writing style detected" |

### Tier 3: Voice Interviews (Solves 80% of Cheating)

Real-time voice conversation makes it nearly impossible to copy-paste from ChatGPT. The natural pressure of speaking eliminates most AI-assistance vectors.

Additional voice-phase options:
- **Optional timed responses** — visible countdown creates natural pressure
- **Proctored mode** (enterprise) — webcam + screen recording with candidate consent

### HR Dashboard: Integrity Score

```
Candidate: Alex Johnson
Interview Integrity: ⚠️ Medium Confidence

Flags:
• 3 of 8 answers were pasted (not typed)
• Switched browser tabs 4 times
• Answer #5 flagged as potentially AI-generated (78%)
• Average response time: 3.2 min (above normal 1.5 min)

Note: These are signals, not proof. Review transcript for final judgment.
```

**Key principle:** Integrity signals are always advisory — HR makes the final call. We never auto-reject candidates based on detection signals alone.

---

## 🎙️ Voice Interviews — Cost & Trade-off Analysis

### Voice Cost Per Interview Breakdown

| Component | Cost | Notes |
|-----------|------|-------|
| **Speech-to-Text (STT)** | $0.15–0.25 | Deepgram: ~$0.01/min × 15–25 min interview |
| **LLM Processing** | $0.10–0.15 | Same as text (processes transcribed text) |
| **Text-to-Speech (TTS)** | $0.20–0.40 | OpenAI TTS: $15/1M chars, ~15K chars AI responses |
| **Voice infrastructure** | $0.05–0.10 | Daily.co/WebRTC server costs per session |
| **Audio storage** | $0.01 | ~30MB per recording |
| **Total Voice Interview** | **$0.51–0.91** | vs **$0.14–0.28** for text |

### Text vs Voice: Full Comparison

| Factor | Text Interview | Voice Interview |
|--------|---------------|----------------|
| **Cost per interview** | $0.14–0.28 | $0.51–0.91 |
| **Cost multiplier** | 1x (baseline) | **3–4x more expensive** |
| **Cheating resistance** | Low–Medium (with integrity signals) | **High** (very hard to cheat) |
| **Candidate experience** | Good (async, own pace) | Great (natural, conversational) |
| **Accessibility** | Better for non-native speakers (time to compose) | Harder for non-native speakers |
| **Completion rate** | ~75–85% | ~60–75% (higher drop-off) |
| **Mobile friendly** | Excellent | Good (needs microphone permission) |
| **Interview duration** | 15–20 min | 15–25 min |
| **Evaluation quality** | Good | Better (tone, confidence, fluency signals) |
| **Technical complexity** | Low | **High** (real-time audio pipeline) |
| **Latency requirement** | None (async) | **<2s end-to-end** (critical UX) |
| **Scaling cost at 1K interviews/month** | ~$200 | ~$700 |
| **Infrastructure** | Standard web server | WebRTC/TURN servers, audio processing |

### Voice Impact on Unit Economics

| Plan | Text Cost | Voice Cost | Margin (Text) | Margin (Voice) |
|------|-----------|-----------|---------------|---------------|
| Starter ($79/50 interviews) | $10 | $35 | **87%** | **56%** |
| Growth ($199/200 interviews) | $40 | $140 | **80%** | **30%** |
| Agency ($499/1000 interviews) | $200 | $700 | **60%** | **-40% (loss!)** |

### Key Insight

Voice **destroys margins on high-volume plans** (Agency tier loses money). Solutions:

1. **Voice as premium add-on** — charge $20–30/month extra for voice-enabled plans
2. **Voice interview surcharge** — voice interviews count as 2–3x against quota
3. **Hybrid default** — text-based screening first, voice only for shortlisted candidates
4. **Tiered pricing** — Agency plan includes text only; voice is Growth+ feature
5. **Cost optimization over time** — self-hosted Whisper for STT ($0 marginal), open-source TTS

### Recommended Pricing Adjustment for Voice

| Plan | Price | Text Interviews | Voice Interviews | Overage |
|------|-------|----------------|-----------------|---------|
| **Starter** | $79/month | 50 | 0 (text only) | $1.50/text |
| **Growth** | $249/month | 200 text | 20 voice | $1.00/text, $3.00/voice |
| **Agency** | $599/month | 1,000 text | 50 voice | $0.50/text, $2.50/voice |
| **Enterprise** | Custom | Unlimited text | Unlimited voice | — |

### Voice Disadvantages Summary

1. **3–4x higher COGS** — STT + TTS add $0.35–0.65 per interview
2. **Latency sensitivity** — >2s delay makes conversation feel broken; needs real-time infra
3. **Lower completion rate** — candidates in noisy environments or public places can't do voice
4. **Accessibility concerns** — non-native speakers, hearing-impaired candidates disadvantaged
5. **Higher infrastructure complexity** — WebRTC, TURN servers, audio encoding/decoding
6. **Storage costs** — audio files are 100x larger than text transcripts
7. **Harder to review** — HR must listen to audio vs quickly scanning text (mitigated with transcription)
8. **Regulatory risk** — voice recording consent laws vary by jurisdiction (two-party consent states)
9. **Mobile battery/bandwidth** — voice drains battery and data faster

### When Voice Makes Sense

- **High-trust roles** where cheating risk is unacceptable (finance, healthcare, legal)
- **Customer-facing roles** where verbal communication IS the skill being tested
- **Shortlist-stage screening** — use text for first pass, voice for top 10 candidates
- **Enterprise customers** who expect voice and will pay premium pricing

---

## ⚠️ Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| AI generates biased evaluations | Legal, reputational | Bias detection layer, human-in-the-loop, audit logs |
| LLM costs spike with scale | Margin compression | Use GPT-4.1-mini, implement caching, batch evaluations |
| Candidates use ChatGPT to answer | Evaluation quality drops | Integrity detection system (Tier 1–3), voice interviews |
| Candidates distrust AI interviews | Low completion rates | Friendly UX, transparency ("AI-assisted"), optional opt-out |
| Voice interview margins negative | Unsustainable at scale | Premium pricing for voice, hybrid text+voice model |
| Competitors copy features | Market share loss | Fast iteration, deep integrations, brand trust |
| Data privacy regulations | Compliance burden | GDPR/SOC 2 roadmap, data retention policies, EU hosting option |
| Low initial conversion | Cash flow | Keep fixed costs <$100/month, founder-led sales, free pilots |

---

## ⚠️ Compliance & Ethics

- AI assists HR — **never replaces final hiring decisions**
- Bias mitigation: evaluate scoring variance across demographics
- Full audit logs for every interview (transcript, scores, reasoning)
- GDPR-aligned: data retention policies, right to deletion, consent management
- Candidate transparency: clear disclosure that interview is AI-conducted
- No facial analysis or emotion detection (ethical boundary)

---

## 📐 Key Metrics to Track

| Metric | Target (MVP) | Target (Scale) |
|--------|-------------|----------------|
| Interview completion rate | >70% | >85% |
| HR satisfaction score (NPS) | >30 | >50 |
| Time-to-screen (vs manual) | 70% reduction | 80% reduction |
| Cost per interview | <$0.30 | <$0.15 |
| Monthly churn rate | <10% | <5% |
| Customer acquisition cost (CAC) | <$200 | <$500 |
| LTV:CAC ratio | >3:1 | >5:1 |

---

## 📌 Summary

| Phase | Timeline | Goal | Revenue Target |
|-------|---------|------|---------------|
| **POC** | Weeks 1–3 | Validate AI interview quality | $0 |
| **MVP** | Weeks 4–11 | Launch with 5–10 pilot customers | $0–500/month |
| **Post-MVP** | Months 3–4 | First paying customers, iterate on feedback | $1,000–2,000/month |
| **Scale** | Months 5–9 | Voice, integrations, grow customer base | $5,000–10,000/month |
| **Enterprise** | Month 10+ | Multi-tenant, compliance, enterprise deals | $10,000+/month |

The platform replaces manual first-round screening at **1/10th the cost** of a human recruiter, while delivering **more consistent, data-driven evaluations**. With break-even at just 3–4 customers and 80%+ gross margins at scale, the business model is sustainable from day one.

