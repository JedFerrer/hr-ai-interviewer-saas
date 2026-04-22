# HR AI Interviewer SaaS — Feature Roadmap
**Generated:** April 22, 2026

---

## Tier 1 — Biggest Pain Points (Next Sprint)

### 1. Candidate Comparison & Ranking Board
HR's #1 job is deciding *who to move forward*. Right now candidates are viewed one-by-one. A side-by-side comparison view for a job's top candidates (scores, strengths, red flags in columns) would dramatically speed up decision-making.

**What to build:**
- Sortable table view on the job detail page
- Columns: name, overall score, skill_match, communication, problem_solving, cultural_fit, recommendation badge
- Select 2–4 candidates and open a comparison panel
- Quick shortlist/reject actions inline

**Why it matters:** Reduces time-to-decision from "review 10 profiles one-by-one" to "scan a ranked table in 30 seconds."

---

### 2. Shareable Evaluation Report (Read-Only Link)
Hiring managers and team leads who make the final call almost never have accounts in the screening tool. A "Share Report" button generates a time-limited, read-only link so the hiring manager can review the AI evaluation and transcript without logging in.

**What to build:**
- `POST /candidates/{id}/share` → returns a signed token + URL
- New public page `/report/{share_token}` — renders evaluation, scores, strengths, gaps, transcript
- Token expires after 7 days (configurable)
- No auth required to view, but token must be valid

**Why it matters:** Eliminates the #1 friction point in enterprise sales — *"my hiring manager can't see the results without creating an account."*

---

### 3. Candidate Status Emails (Accept / Reject / Next Steps)
Shortlisting or rejecting currently just flips a status badge. HR needs the system to automatically send a configurable email to the candidate when their status changes.

**What to build:**
- On shortlist → send "Congratulations, you're moving to the next round" email
- On reject → send "Thank you for your time" email
- Customizable email templates per company (stored in DB)
- Toggle per job: "Auto-send status emails: ON/OFF"

**Why it matters:** Without this, HR still has to manually email every candidate — defeating the automation purpose of the tool.

---

## Tier 2 — High Value, Medium Effort

### 4. Analytics Dashboard
Give HR managers data to justify the tool to leadership and optimize their hiring funnel.

**Metrics to display:**
- Funnel: applied → completed → shortlisted (conversion rates per job)
- Average time-to-complete (how long candidates take to finish)
- Score distribution histogram per job
- Average AI cost per interview (USD)
- Completion rate (% of invited candidates who actually finish)
- Top candidate sources (if UTM tracking added to interview links)

---

### 5. Team Collaboration (Multi-User + Notes)
Currently one admin per company. Real hiring teams need multiple people involved.

**What to build:**
- Invite team members via email (roles: admin, recruiter, viewer)
- Per-candidate notes/comments visible to the whole team
  - e.g., "I know this candidate from a previous role — strong communicator"
- Activity log: who shortlisted/rejected and when
- Email notifications to team when new candidate completes interview

---

### 6. Candidate Reminder Emails
Many candidates receive the interview link but never complete it. An automatic reminder would significantly increase completion rates.

**What to build:**
- Scheduled task: 48 hours after invite sent, check if status is still `ready`
- If not started → send one reminder email with the interview link
- Configurable delay (24h / 48h / 72h) per job
- Max 1 reminder per candidate (no spam)

**Why it matters:** Low effort — the email service and scheduling infrastructure already exist. High impact on completion rates.

---

## Tier 3 — Nice-to-Have for MVP+

| Feature | Why It Matters |
|---------|---------------|
| **CSV / PDF Export** | HR needs to share candidate lists in meetings without screen-sharing the app |
| **Custom scoring criteria** | Let HR define weights (e.g., "leadership matters more than cultural fit for this role") |
| **Kanban pipeline view** | Visual drag-and-drop board for candidate stages — familiar UX from Trello/Lever |
| **Webhook / ATS integration** | Push shortlisted candidates to Greenhouse, Lever, or Workday via webhook |
| **Interview scheduling for next round** | After AI screening, let HR schedule a human interview (calendar link or Cal.com integration) |
| **Bulk actions** | Select multiple candidates and shortlist/reject/export in one click |
| **Job templates** | Save a job posting as a template to reuse for future openings |
| **Password reset flow** | Currently no way for users to reset a forgotten password |

---

## Recommended Build Order

```
Sprint 1:  Shareable Evaluation Report  ← simplest, highest enterprise value
Sprint 2:  Candidate Status Emails      ← completes the automation loop
Sprint 3:  Candidate Comparison Board   ← speeds up HR decision-making
Sprint 4:  Analytics Dashboard          ← justifies the tool to leadership
Sprint 5:  Team Collaboration           ← enables enterprise team selling
Sprint 6:  Candidate Reminders          ← improves completion rates
Sprint 7+: Tier 3 features as needed
```

---

*Generated by GitHub Copilot — April 22, 2026*
