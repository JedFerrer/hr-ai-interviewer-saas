# User Flow Plan — AI HR Interviewer SaaS

Complete user journey maps for all personas interacting with the platform.

---

## 👥 User Personas

| Persona | Role | Goal | Key Frustration |
|---------|------|------|----------------|
| **Sarah** | HR Manager (SMB) | Screen 50 applicants/week without burning out | Spends 60% of time on repetitive phone screens |
| **Mike** | Staffing Agency Recruiter | Screen 200+ candidates/week across clients | Can't scale screening without hiring more recruiters |
| **Alex** | Job Applicant | Get a fair shot at the role, fast response | Ghosted after applying, no feedback, long wait times |
| **Lisa** | HR Director | Standardize hiring, reduce bias, track metrics | Every recruiter screens differently, no data |

---

## 🔵 Flow 1: HR Manager — First-Time Setup

### 1.1 Signup & Onboarding

```
Landing Page
  │
  ├─ "Start Free Trial" button
  │
  ▼
Signup Form
  • Work email
  • Password
  • Company name
  • Company size (dropdown: 1-50, 51-200, 201-500, 500+)
  │
  ▼
Email Verification
  • Confirmation email with magic link
  • Click → lands in dashboard
  │
  ▼
Onboarding Wizard (3 steps, skippable)
  │
  ├─ Step 1: "Create your first job posting"
  │   • Job title
  │   • Copy-paste or type job description
  │   • Required skills (tag input)
  │
  ├─ Step 2: "Customize interview questions" (optional)
  │   • System shows AI-suggested questions based on JD
  │   • HR can add/remove/reorder questions
  │   • Toggle: "Let AI generate follow-ups" (default: ON)
  │
  └─ Step 3: "Share with candidates"
      • System generates unique interview link
      • Copy link / Send via email
      • Preview: "See what candidates will experience"
  │
  ▼
Dashboard — Job posting is live, waiting for candidates
```

**Key UX Decisions:**
- Time to first interview link: **under 5 minutes**
- No credit card required for trial (reduces friction)
- AI-suggested questions reduce blank-page anxiety
- Preview mode builds trust in the AI interview experience

---

### 1.2 Creating a Job Posting (Returning User)

```
Dashboard
  │
  ├─ "New Job Posting" button
  │
  ▼
Job Setup Form
  │
  ├─ Basic Info
  │   • Job title
  │   • Department (optional)
  │   • Location / Remote
  │   • Employment type (Full-time, Part-time, Contract)
  │
  ├─ Job Description
  │   • Rich text editor OR paste from existing JD
  │   • AI auto-extracts: required skills, experience level, key responsibilities
  │   • HR confirms/edits extracted data
  │
  ├─ Interview Configuration
  │   • Interview style: "Quick Screen" (5 questions) / "Standard" (8-10) / "Deep" (12-15)
  │   • Question categories toggle:
  │     ☑ Resume verification
  │     ☑ Role-specific skills
  │     ☑ Behavioral / situational
  │     ☐ Company knowledge (requires RAG setup — Phase 2)
  │   • Custom questions (add your own)
  │   • Evaluation criteria weights (sliders):
  │     - Skill match: 40%
  │     - Communication: 20%
  │     - Problem solving: 25%
  │     - Cultural fit: 15%
  │
  ├─ Candidate Settings
  │   • Resume required: Yes/No
  │   • Interview deadline (optional)
  │   • Max candidates (optional)
  │   • Language: English (more languages Phase 3+)
  │
  └─ Review & Publish
      • Preview interview as candidate
      • Publish → generates shareable link
      • Option: "Email invite list" (paste emails or CSV upload)
```

---

### 1.3 Managing Active Job Postings

```
Dashboard → Jobs Tab
  │
  ├─ Active Jobs List
  │   ┌────────────────────────────────────────────────┐
  │   │ Marketing Manager                              │
  │   │ Posted: Apr 10  •  Candidates: 23  •  Link: 🔗 │
  │   │ Status: Active   [Pause] [Edit] [Archive]      │
  │   └────────────────────────────────────────────────┘
  │   ┌────────────────────────────────────────────────┐
  │   │ Sales Development Rep                          │
  │   │ Posted: Apr 8   •  Candidates: 8   •  Link: 🔗 │
  │   │ Status: Active   [Pause] [Edit] [Archive]      │
  │   └────────────────────────────────────────────────┘
  │
  ├─ Quick Stats Per Job
  │   • Total applicants
  │   • Interviews completed vs pending
  │   • Average score
  │   • Top candidate preview
  │
  └─ Actions
      ├─ Pause → stops accepting new candidates, link shows "closed"
      ├─ Edit → update JD, questions (doesn't affect completed interviews)
      ├─ Archive → move to inactive, keep data for reference
      └─ Duplicate → create new posting from this template
```

---

## 🟢 Flow 2: Job Applicant — Interview Experience

### 2.1 Receiving the Interview Invitation

```
Candidate receives email / clicks link from job board
  │
  ▼
Interview Landing Page
  │
  ├─ Company logo + job title
  ├─ "You've been invited to complete a screening interview"
  ├─ Estimated time: "~15–20 minutes"
  ├─ What to expect:
  │   • "AI-assisted interview about your background and the role"
  │   • "Text-based conversation — answer at your own pace"
  │   • "Your responses will be reviewed by the hiring team"
  ├─ Privacy notice: "Your data is handled per our privacy policy"
  │
  └─ "Start Interview" button
```

**Key UX Decisions:**
- No account creation required for candidates (reduces drop-off)
- Clear disclosure: "AI-assisted" — builds trust
- Time estimate sets expectations
- Mobile-responsive — many candidates apply from phones

---

### 2.2 Pre-Interview: Resume Upload

```
"Start Interview" clicked
  │
  ▼
Resume Upload Screen
  │
  ├─ Drag & drop or file picker (PDF, DOCX)
  ├─ "Don't have a resume? Skip this step" (if HR allows)
  │
  ▼
Processing Screen (2–5 seconds)
  │
  ├─ "Reviewing your background..."
  ├─ Progress indicator
  │
  ▼
Confirmation
  ├─ "We found the following from your resume:"
  │   • Name: Alex Johnson
  │   • Current role: Marketing Coordinator at XYZ Corp
  │   • Experience: 3 years in digital marketing
  │   • Skills detected: SEO, Google Analytics, Content Strategy
  │
  ├─ "Is this correct?" → Yes / "Edit details"
  │
  └─ "Begin Interview" button
```

---

### 2.3 AI Interview — Chat Experience

```
Interview Chat Interface
  │
  ├─ Left side: Chat conversation
  ├─ Right side (desktop): Job title + progress indicator
  ├─ Mobile: Full-screen chat with progress bar at top
  │
  ▼
AI Welcome Message
  "Hi Alex! Thanks for taking the time to interview for the
   Marketing Manager role at Acme Corp. I'll ask you a series
   of questions about your background and the role. Take your
   time with each answer — there are no trick questions.
   Let's get started!"
  │
  ▼
Question Flow (8–10 questions typical)
  │
  ├─ Q1: Resume Verification
  │   AI: "I see you worked at XYZ Corp as a Marketing Coordinator.
  │        Can you walk me through your main responsibilities there?"
  │   Candidate types response...
  │   │
  │   ├─ [If answer is vague] AI Follow-up:
  │   │   "Interesting. Can you give me a specific example of a
  │   │    campaign you led and what results it achieved?"
  │   │
  │   └─ [If answer is detailed] AI moves to next topic
  │
  ├─ Q2–Q4: Role-Specific Skills
  │   AI: "This role requires experience with SEO strategy.
  │        How would you approach improving organic traffic for
  │        a B2B SaaS company with 10K monthly visitors?"
  │
  ├─ Q5–Q6: Behavioral Questions
  │   AI: "Tell me about a time you had to manage competing
  │        priorities with tight deadlines. How did you handle it?"
  │
  ├─ Q7–Q8: Problem Solving / Situational
  │   AI: "Imagine our marketing budget was cut by 40% mid-quarter.
  │        What would you prioritize and what would you cut?"
  │
  ├─ Q9: Candidate Questions (optional)
  │   AI: "Do you have any questions about the role or the company
  │        that I can help answer?"
  │   [If RAG enabled: AI answers from company knowledge base]
  │   [If not: "Great question! The hiring team will follow up
  │    on that in the next stage."]
  │
  └─ Q10: Closing
      AI: "Thanks so much, Alex! You've given some really
           thoughtful answers. The hiring team will review your
           interview and get back to you within [X days].
           Best of luck!"
```

**Candidate UX Features During Interview:**
- Type at their own pace (no timer pressure)
- "Thinking..." indicator shows AI is processing
- Progress bar: "Question 3 of 8"
- Can't go back to previous answers (prevents gaming)
- Auto-save — can close browser and resume within 24hrs
- Mobile keyboard-optimized input

---

### 2.4 Post-Interview: Candidate Thank You

```
Interview Complete
  │
  ▼
Thank You Screen
  ├─ "Interview Complete!"
  ├─ "Your responses have been submitted to the hiring team"
  ├─ "You'll hear back within [X business days]"
  ├─ Optional: Basic self-assessment
  │   "How was your interview experience?" → Great / Okay / Poor
  │
  └─ Candidate receives confirmation email:
      • "Thanks for completing your interview for [Role] at [Company]"
      • "The team is reviewing your responses"
      • "Expected response time: [X days]"
```

---

### 2.5 Candidate Status Updates (Automated Emails)

```
Post-Interview Email Timeline
  │
  ├─ Immediately: "Interview received" confirmation
  │
  ├─ If shortlisted (HR action):
  │   "Great news! You've been shortlisted for [Role].
  │    The hiring team will reach out to schedule the next step."
  │
  ├─ If rejected (HR action):
  │   "Thank you for your interest in [Role] at [Company].
  │    After careful review, we've decided to move forward
  │    with other candidates. We appreciate your time."
  │
  └─ If no action after 7 days:
      HR receives nudge: "23 candidates awaiting review for [Role]"
```

---

## 🟣 Flow 3: HR Manager — Reviewing Candidates

### 3.1 Dashboard — Candidate Pipeline

```
HR Dashboard
  │
  ├─ Tab: Jobs (list of active postings)
  │   └─ Click job → Candidate Pipeline
  │
  ▼
Candidate Pipeline View
  │
  ├─ Filter bar: Status (All | Completed | In Progress | Not Started)
  ├─ Sort: Score (high→low) | Date | Name
  ├─ Search: by name or keyword
  │
  ├─ Candidate Cards (list view):
  │   ┌──────────────────────────────────────────────┐
  │   │ Alex Johnson          Score: 8.2/10          │
  │   │ Marketing Coordinator, 3 yrs exp             │
  │   │ Skills: SEO ✅  Analytics ✅  Content ✅      │
  │   │ Completed: Apr 15, 2026                       │
  │   │ Status: [Shortlist] [Reject] [Review]         │
  │   └──────────────────────────────────────────────┘
  │   ┌──────────────────────────────────────────────┐
  │   │ Jordan Lee            Score: 6.1/10          │
  │   │ Digital Marketer, 1 yr exp                    │
  │   │ Skills: SEO ✅  Analytics ❌  Content ✅      │
  │   │ Completed: Apr 14, 2026                       │
  │   │ Status: [Shortlist] [Reject] [Review]         │
  │   └──────────────────────────────────────────────┘
  │
  └─ Bulk actions: "Reject all below score 5" / "Export CSV"
```

---

### 3.2 Individual Candidate Review

```
Click "Review" on candidate card
  │
  ▼
Candidate Detail Page
  │
  ├─ Header: Name, applied role, overall score, status
  │
  ├─ Tab 1: AI Evaluation Summary
  │   ┌─────────────────────────────────────┐
  │   │ Overall Score: 8.2 / 10             │
  │   │                                     │
  │   │ Skill Match:      ████████░░  8/10  │
  │   │ Communication:    █████████░  9/10  │
  │   │ Problem Solving:  ███████░░░  7/10  │
  │   │ Cultural Fit:     ████████░░  8/10  │
  │   │                                     │
  │   │ AI Summary:                         │
  │   │ "Strong candidate with solid SEO    │
  │   │  experience. Demonstrated clear     │
  │   │  strategic thinking in budget       │
  │   │  scenario. Communication is         │
  │   │  excellent. Minor gap: limited      │
  │   │  experience with enterprise B2B."   │
  │   │                                     │
  │   │ Flags: None                         │
  │   │ Strengths: SEO depth, strategic     │
  │   │    thinking, clear communication    │
  │   │ Gaps: B2B enterprise experience     │
  │   └─────────────────────────────────────┘
  │
  ├─ Tab 2: Full Interview Transcript
  │   • Full Q&A conversation
  │   • Each answer has inline mini-score
  │   • Highlights on strong/weak answers
  │
  ├─ Tab 3: Resume
  │   • Uploaded resume (PDF viewer)
  │   • Extracted skills vs. required skills comparison
  │
  └─ Actions:
      ├─ "Shortlist" → moves to shortlisted pipeline
      ├─ "Reject" → optional: send rejection email (template)
      ├─ "Schedule Next Interview" → (Phase 2: calendar integration)
      └─ "Add Note" → internal HR notes on this candidate
```

---

### 3.3 Taking Action on Candidates

```
Shortlist Action
  │
  ├─ Candidate moved to "Shortlisted" column
  ├─ Optional: Send email to candidate
  │   "Congratulations! You've been shortlisted for the
  │    [Role] position. Our team will reach out to schedule
  │    the next step."
  │
  └─ HR can schedule human interview (Phase 2+)

Reject Action
  │
  ├─ Confirmation: "Reject Alex Johnson for Marketing Manager?"
  ├─ Optional: Select rejection reason (dropdown)
  │   • Not enough experience
  │   • Skills mismatch
  │   • Poor communication
  │   • Other (free text)
  ├─ Optional: Send rejection email (customizable template)
  │   "Thank you for your interest in [Role] at [Company].
  │    After careful review, we've decided to move forward
  │    with other candidates. We appreciate your time."
  │
  └─ Candidate moved to "Rejected" — can be undone within 24hrs
```

---

### 3.4 Comparing Candidates Side-by-Side (Phase 2+)

```
Select 2–4 candidates → "Compare"
  │
  ▼
Comparison View
  ┌──────────────┬────────────┬────────────┐
  │              │ Alex J.    │ Jordan L.  │
  ├──────────────┼────────────┼────────────┤
  │ Overall      │ 8.2        │ 6.1        │
  │ Skill Match  │ 8          │ 5          │
  │ Communication│ 9          │ 7          │
  │ Problem Solv.│ 7          │ 6          │
  │ Cultural Fit │ 8          │ 7          │
  ├──────────────┼────────────┼────────────┤
  │ Experience   │ 3 years    │ 1 year     │
  │ Key Strength │ SEO expert │ Creative   │
  │ Key Gap      │ B2B exp    │ Analytics  │
  └──────────────┴────────────┴────────────┘
```

---

## 🔴 Flow 4: Staffing Agency Recruiter (Multi-Client)

```
Agency Dashboard
  │
  ├─ Clients (list of companies they recruit for)
  │   ├─ Acme Corp — 3 active roles, 45 candidates
  │   ├─ TechStart Inc — 1 active role, 12 candidates
  │   └─ Retail Giant — 5 active roles, 200+ candidates
  │
  ├─ Click client → Client workspace
  │   ├─ Create job postings for this client
  │   ├─ Review candidates per role
  │   └─ Export reports to send to client
  │
  ├─ Global Search
  │   • Search across all clients for candidates by skill
  │   • "Show me all candidates with 5+ years Java experience"
  │
  └─ Analytics (Agency-wide)
      • Interviews this month: 342
      • Average score: 6.8
      • Completion rate: 82%
      • Time saved: ~171 hours (vs manual screening)
```

---

## 🟡 Flow 5: Edge Cases & Error States

### 5.1 Candidate Abandons Interview Mid-Way

```
Candidate closes browser during interview
  │
  ├─ Session saved automatically
  ├─ 1 hour later: Reminder email
  │   "You have an unfinished interview for [Role] at [Company].
  │    Pick up where you left off: [Resume Link]"
  │
  ├─ Candidate clicks link → resumes from last answered question
  │
  ├─ If not completed within 72 hours:
  │   • Marked "Incomplete" in HR dashboard
  │   • HR can: Send another reminder / Mark as withdrawn
  │
  └─ Partial interviews are still scored (with "incomplete" flag)
```

### 5.2 Resume Upload Fails

```
Upload fails (corrupt file, wrong format, too large)
  │
  ├─ Error: "We couldn't process your file. Please upload a PDF
  │          or DOCX under 10MB."
  ├─ Retry option
  ├─ Fallback: "Continue without resume" (if HR allows)
  │   • AI adjusts questions to be more exploratory
  │   • Evaluation notes: "Resume not provided"
  │
  └─ HR sees flag: "No resume uploaded" on candidate card
```

### 5.3 AI Interview Takes Too Long / Errors

```
AI response takes >10 seconds
  │
  ├─ Show: "Thinking about your answer..." animation
  ├─ If >30 seconds: "Taking a bit longer than usual. Hang tight!"
  ├─ If fails: "Sorry, we hit a small hiccup. Let me rephrase..."
  │   → Retry with simpler prompt
  │
  └─ If persistent failure:
      • "We're experiencing technical difficulties. Your progress
         has been saved. Please try again in a few minutes."
      • HR notified of technical issue
```

### 5.4 Candidate Provides Off-Topic / Harmful Responses

```
AI detects off-topic, nonsensical, or harmful input
  │
  ├─ Gentle redirect: "I appreciate your response! Let me rephrase
  │   the question to make sure we're on the same page..."
  │
  ├─ If repeated (3+ times):
  │   AI: "It seems like some of my questions aren't connecting.
  │        That's okay — let's move on to the next topic."
  │
  ├─ Harmful/abusive content:
  │   AI: "I want to keep this conversation professional.
  │        Let's focus on the role and your experience."
  │   → Flagged in evaluation: "Unprofessional responses detected"
  │
  └─ All flagged for HR review in transcript
```

### 5.5 Interview Link Expired / Job Closed

```
Candidate clicks old interview link
  │
  ├─ If job paused/archived:
  │   "This position is no longer accepting applications.
  │    Check [Company]'s careers page for open roles."
  │
  ├─ If link expired (past deadline):
  │   "The deadline for this interview has passed.
  │    Please contact the hiring team if you have questions."
  │
  └─ If candidate already completed:
      "You've already completed this interview.
       The hiring team is reviewing your responses."
```

---

## 📱 Flow 6: Mobile Experience

### Candidate on Mobile

```
• Interview link opens in mobile browser (no app needed)
• Full-screen chat interface
• Large touch-friendly input field
• Auto-scroll to latest message
• Resume upload via camera (photo of resume) or file picker
• Progress bar at top (minimal chrome)
• Keyboard doesn't obscure chat history
```

### HR on Mobile (Phase 3+)

```
• Responsive dashboard
• Swipe to shortlist/reject candidates
• Push notifications: "New candidate completed interview"
• Quick review: AI summary + score (tap for full details)
```

---

## 📊 Flow Metrics to Track Per Step

| Flow Step | Metric | Target |
|-----------|--------|--------|
| Landing page → Start Interview | Click-through rate | >80% |
| Resume upload → Complete | Upload success rate | >95% |
| Interview start → Complete | Completion rate | >75% |
| Interview complete → HR review | Time to first review | <24 hrs |
| HR review → Action (shortlist/reject) | Decision rate | >90% within 48hrs |
| Rejection → Candidate notified | Notification sent | 100% (automated) |
| Abandoned → Resumed | Resume rate (after reminder) | >30% |

---

## 🔑 Key UX Principles Across All Flows

1. **Speed to value** — HR should have their first interview link in under 5 minutes
2. **Zero friction for candidates** — no account, no app, no timer
3. **Transparency** — always disclose AI involvement, show what data is collected
4. **Mobile-first candidate experience** — most applicants apply from phones
5. **Actionable outputs** — every screen answers "what should I do next?"
6. **Graceful degradation** — errors don't lose data, sessions auto-save
7. **Progressive disclosure** — show simple first, details on demand
# User Flow Plan — AI HR Interviewer SaaS

Complete user journey maps for all personas interacting with the platform.

---

## 👥 User Personas

| Persona | Role | Goal | Key Frustration |
|---------|------|------|----------------|
| **Sarah** | HR Manager (SMB) | Screen 50 applicants/week without burning out | Spends 60% of time on repetitive phone screens |
| **Mike** | Staffing Agency Recruiter | Screen 200+ candidates/week across clients | Can't scale screening without hiring more recruiters |
| **Alex** | Job Applicant | Get a fair shot at the role, fast response | Ghosted after applying, no feedback, long wait times |
| **Lisa** | HR Director | Standardize hiring, reduce bias, track metrics | Every recruiter screens differently, no data |

---

## 🔵 Flow 1: HR Manager — First-Time Setup

### 1.1 Signup & Onboarding

```
Landing Page
  │
  ├─ "Start Free Trial" button
  │
  ▼
Signup Form
  • Work email
  • Password
  • Company name
  • Company size (dropdown: 1-50, 51-200, 201-500, 500+)
  │
  ▼
Email Verification
  • Confirmation email with magic link
  • Click → lands in dashboard
  │
  ▼
Onboarding Wizard (3 steps, skippable)
  │
  ├─ Step 1: "Create your first job posting"
  │   • Job title
  │   • Copy-paste or type job description
  │   • Required skills (tag input)
  │
  ├─ Step 2: "Customize interview questions" (optional)
  │   • System shows AI-suggested questions based on JD
  │   • HR can add/remove/reorder questions
  │   • Toggle: "Let AI generate follow-ups" (default: ON)
  │
  └─ Step 3: "Share with candidates"
      • System generates unique interview link
      • Copy link / Send via email
      • Preview: "See what candidates will experience"
  │
  ▼
Dashboard — Job posting is live, waiting for candidates
```

**Key UX Decisions:**
- Time to first interview link: **under 5 minutes**
- No credit card required for trial (reduces friction)
- AI-suggested questions reduce blank-page anxiety
- Preview mode builds trust in the AI interview experience

---

### 1.2 Creating a Job Posting (Returning User)

```
Dashboard
  │
  ├─ "New Job Posting" button
  │
  ▼
Job Setup Form
  │
  ├─ Basic Info
  │   • Job title
  │   • Department (optional)
  │   • Location / Remote
  │   • Employment type (Full-time, Part-time, Contract)
  │
  ├─ Job Description
  │   • Rich text editor OR paste from existing JD
  │   • AI auto-extracts: required skills, experience level, key responsibilities
  │   • HR confirms/edits extracted data
  │
  ├─ Interview Configuration
  │   • Interview style: "Quick Screen" (5 questions) / "Standard" (8-10) / "Deep" (12-15)
  │   • Question categories toggle:
  │     ☑ Resume verification
  │     ☑ Role-specific skills
  │     ☑ Behavioral / situational
  │     ☐ Company knowledge (requires RAG setup — Phase 2)
  │   • Custom questions (add your own)
  │   • Evaluation criteria weights (sliders):
  │     - Skill match: 40%
  │     - Communication: 20%
  │     - Problem solving: 25%
  │     - Cultural fit: 15%
  │
  ├─ Candidate Settings
  │   • Resume required: Yes/No
  │   • Interview deadline (optional)
  │   • Max candidates (optional)
  │   • Language: English (more languages Phase 3+)
  │
  └─ Review & Publish
      • Preview interview as candidate
      • Publish → generates shareable link
      • Option: "Email invite list" (paste emails or CSV upload)
```

---

## 🟢 Flow 2: Job Applicant — Interview Experience

### 2.1 Receiving the Interview Invitation

```
Candidate receives email / clicks link from job board
  │
  ▼
Interview Landing Page
  │
  ├─ Company logo + job title
  ├─ "You've been invited to complete a screening interview"
  ├─ Estimated time: "~15–20 minutes"
  ├─ What to expect:
  │   • "AI-assisted interview about your background and the role"
  │   • "Text-based conversation — answer at your own pace"
  │   • "Your responses will be reviewed by the hiring team"
  ├─ Privacy notice: "Your data is handled per our privacy policy"
  │
  └─ "Start Interview" button
```

**Key UX Decisions:**
- No account creation required for candidates (reduces drop-off)
- Clear disclosure: "AI-assisted" — builds trust
- Time estimate sets expectations
- Mobile-responsive — many candidates apply from phones

---

### 2.2 Pre-Interview: Resume Upload

```
"Start Interview" clicked
  │
  ▼
Resume Upload Screen
  │
  ├─ Drag & drop or file picker (PDF, DOCX)
  ├─ "Don't have a resume? Skip this step" (if HR allows)
  │
  ▼
Processing Screen (2–5 seconds)
  │
  ├─ "Reviewing your background..."
  ├─ Progress indicator
  │
  ▼
Confirmation
  ├─ "We found the following from your resume:"
  │   • Name: Alex Johnson
  │   • Current role: Marketing Coordinator at XYZ Corp
  │   • Experience: 3 years in digital marketing
  │   • Skills detected: SEO, Google Analytics, Content Strategy
  │
  ├─ "Is this correct?" → Yes / "Edit details"
  │
  └─ "Begin Interview" button
```

---

### 2.3 AI Interview — Chat Experience

```
Interview Chat Interface
  │
  ├─ Left side: Chat conversation
  ├─ Right side (desktop): Job title + progress indicator
  ├─ Mobile: Full-screen chat with progress bar at top
  │
  ▼
AI Welcome Message
  "Hi Alex! Thanks for taking the time to interview for the
   Marketing Manager role at Acme Corp. I'll ask you a series
   of questions about your background and the role. Take your
   time with each answer — there are no trick questions.
   Let's get started!"
  │
  ▼
Question Flow (8–10 questions typical)
  │
  ├─ Q1: Resume Verification
  │   AI: "I see you worked at XYZ Corp as a Marketing Coordinator.
  │        Can you walk me through your main responsibilities there?"
  │   Candidate types response...
  │   │
  │   ├─ [If answer is vague] AI Follow-up:
  │   │   "Interesting. Can you give me a specific example of a
  │   │    campaign you led and what results it achieved?"
  │   │
  │   └─ [If answer is detailed] AI moves to next topic
  │
  ├─ Q2–Q4: Role-Specific Skills
  │   AI: "This role requires experience with SEO strategy.
  │        How would you approach improving organic traffic for
  │        a B2B SaaS company with 10K monthly visitors?"
  │
  ├─ Q5–Q6: Behavioral Questions
  │   AI: "Tell me about a time you had to manage competing
  │        priorities with tight deadlines. How did you handle it?"
  │
  ├─ Q7–Q8: Problem Solving / Situational
  │   AI: "Imagine our marketing budget was cut by 40% mid-quarter.
  │        What would you prioritize and what would you cut?"
  │
  ├─ Q9: Candidate Questions (optional)
  │   AI: "Do you have any questions about the role or the company
  │        that I can help answer?"
  │   [If RAG enabled: AI answers from company knowledge base]
  │   [If not: "Great question! The hiring team will follow up
  │    on that in the next stage."]
  │
  └─ Q10: Closing
      AI: "Thanks so much, Alex! You've given some really
           thoughtful answers. The hiring team will review your
           interview and get back to you within [X days].
           Best of luck!"
```

**Candidate UX Features During Interview:**
- Type at their own pace (no timer pressure)
- "Thinking..." indicator shows AI is processing
- Progress bar: "Question 3 of 8"
- Can't go back to previous answers (prevents gaming)
- Auto-save — can close browser and resume within 24hrs
- Mobile keyboard-optimized input

---

### 2.4 Post-Interview: Candidate Thank You

```
Interview Complete
  │
  ▼
Thank You Screen
  ├─ "Interview Complete! 🎉"
  ├─ "Your responses have been submitted to the hiring team"
  ├─ "You'll hear back within [X business days]"
  ├─ Optional: Basic self-assessment
  │   "How was your interview experience?" → 😀 😐 😞
  │
  └─ Candidate receives confirmation email:
      • "Thanks for completing your interview for [Role] at [Company]"
      • "The team is reviewing your responses"
      • "Expected response time: [X days]"
```

---

## 🟣 Flow 3: HR Manager — Reviewing Candidates

### 3.1 Dashboard — Candidate Pipeline

```
HR Dashboard
  │
  ├─ Tab: Jobs (list of active postings)
  │   └─ Click job → Candidate Pipeline
  │
  ▼
Candidate Pipeline View
  │
  ├─ Filter bar: Status (All | Completed | In Progress | Not Started)
  ├─ Sort: Score (high→low) | Date | Name
  ├─ Search: by name or keyword
  │
  ├─ Candidate Cards (list view):
  │   ┌──────────────────────────────────────────────┐
  │   │ Alex Johnson          Score: 8.2/10   ⭐⭐⭐⭐ │
  │   │ Marketing Coordinator, 3 yrs exp             │
  │   │ Skills: SEO ✅  Analytics ✅  Content ✅      │
  │   │ Completed: Apr 15, 2026                       │
  │   │ Status: [Shortlist] [Reject] [Review]         │
  │   └──────────────────────────────────────────────┘
  │   ┌──────────────────────────────────────────────┐
  │   │ Jordan Lee            Score: 6.1/10   ⭐⭐⭐   │
  │   │ Digital Marketer, 1 yr exp                    │
  │   │ Skills: SEO ✅  Analytics ❌  Content ✅      │
  │   │ Completed: Apr 14, 2026                       │
  │   │ Status: [Shortlist] [Reject] [Review]         │
  │   └──────────────────────────────────────────────┘
  │
  └─ Bulk actions: "Reject all below score 5" / "Export CSV"
```

---

### 3.2 Individual Candidate Review

```
Click "Review" on candidate card
  │
  ▼
Candidate Detail Page
  │
  ├─ Header: Name, applied role, overall score, status
  │
  ├─ Tab 1: AI Evaluation Summary
  │   ┌─────────────────────────────────────┐
  │   │ Overall Score: 8.2 / 10             │
  │   │                                     │
  │   │ Skill Match:      ████████░░  8/10  │
  │   │ Communication:    █████████░  9/10  │
  │   │ Problem Solving:  ███████░░░  7/10  │
  │   │ Cultural Fit:     ████████░░  8/10  │
  │   │                                     │
  │   │ AI Summary:                         │
  │   │ "Strong candidate with solid SEO    │
  │   │  experience. Demonstrated clear     │
  │   │  strategic thinking in budget       │
  │   │  scenario. Communication is         │
  │   │  excellent. Minor gap: limited      │
  │   │  experience with enterprise B2B."   │
  │   │                                     │
  │   │ ⚠️ Flags: None                      │
  │   │ ✅ Strengths: SEO depth, strategic  │
  │   │    thinking, clear communication    │
  │   │ ⚡ Gaps: B2B enterprise experience  │
  │   └─────────────────────────────────────┘
  │
  ├─ Tab 2: Full Interview Transcript
  │   • Full Q&A conversation
  │   • Each answer has inline mini-score
  │   • Highlights on strong/weak answers
  │
  ├─ Tab 3: Resume
  │   • Uploaded resume (PDF viewer)
  │   • Extracted skills vs. required skills comparison
  │
  └─ Actions:
      ├─ "Shortlist" → moves to shortlisted pipeline
      ├─ "Reject" → optional: send rejection email (template)
      ├─ "Schedule Next Interview" → (Phase 2: calendar integration)
      └─ "Add Note" → internal HR notes on this candidate
```

---

### 3.3 Taking Action on Candidates

```
Shortlist Action
  │
  ├─ Candidate moved to "Shortlisted" column
  ├─ Optional: Send email to candidate
  │   "Congratulations! You've been shortlisted for the
  │    [Role] position. Our team will reach out to schedule
  │    the next step."
  │
  └─ HR can schedule human interview (Phase 2+)

Reject Action
  │
  ├─ Confirmation: "Reject Alex Johnson for Marketing Manager?"
  ├─ Optional: Select rejection reason (dropdown)
  │   • Not enough experience
  │   • Skills mismatch
  │   • Poor communication
  │   • Other (free text)
  ├─ Optional: Send rejection email (customizable template)
  │   "Thank you for your interest in [Role] at [Company].
  │    After careful review, we've decided to move forward
  │    with other candidates. We appreciate your time."
  │
  └─ Candidate moved to "Rejected" — can be undone within 24hrs
```

---

## 🔴 Flow 4: Staffing Agency Recruiter (Multi-Client)

```
Agency Dashboard
  │
  ├─ Clients (list of companies they recruit for)
  │   ├─ Acme Corp — 3 active roles, 45 candidates
  │   ├─ TechStart Inc — 1 active role, 12 candidates
  │   └─ Retail Giant — 5 active roles, 200+ candidates
  │
  ├─ Click client → Client workspace
  │   ├─ Create job postings for this client
  │   ├─ Review candidates per role
  │   └─ Export reports to send to client
  │
  ├─ Global Search
  │   • Search across all clients for candidates by skill
  │   • "Show me all candidates with 5+ years Java experience"
  │
  └─ Analytics (Agency-wide)
      • Interviews this month: 342
      • Average score: 6.8
      • Completion rate: 82%
      • Time saved: ~171 hours (vs manual screening)
```

---

## 🟡 Flow 5: Edge Cases & Error States

### 5.1 Candidate Abandons Interview Mid-Way

```
Candidate closes browser during interview
  │
  ├─ Session saved automatically
  ├─ 1 hour later: Reminder email
  │   "You have an unfinished interview for [Role] at [Company].
  │    Pick up where you left off: [Resume Link]"
  │
  ├─ Candidate clicks link → resumes from last answered question
  │
  ├─ If not completed within 72 hours:
  │   • Marked "Incomplete" in HR dashboard
  │   • HR can: Send another reminder / Mark as withdrawn
  │
  └─ Partial interviews are still scored (with "incomplete" flag)
```

### 5.2 Resume Upload Fails

```
Upload fails (corrupt file, wrong format, too large)
  │
  ├─ Error: "We couldn't process your file. Please upload a PDF
  │          or DOCX under 10MB."
  ├─ Retry option
  ├─ Fallback: "Continue without resume" (if HR allows)
  │   • AI adjusts questions to be more exploratory
  │   • Evaluation notes: "Resume not provided"
  │
  └─ HR sees flag: "No resume uploaded" on candidate card
```

### 5.3 AI Interview Takes Too Long / Errors

```
AI response takes >10 seconds
  │
  ├─ Show: "Thinking about your answer..." animation
  ├─ If >30 seconds: "Taking a bit longer than usual. Hang tight!"
  ├─ If fails: "Sorry, we hit a small hiccup. Let me rephrase..."
  │   → Retry with simpler prompt
  │
  └─ If persistent failure:
      • "We're experiencing technical difficulties. Your progress
         has been saved. Please try again in a few minutes."
      • HR notified of technical issue
```

### 5.4 Candidate Provides Off-Topic / Harmful Responses

```
AI detects off-topic, nonsensical, or harmful input
  │
  ├─ Gentle redirect: "I appreciate your response! Let me rephrase
  │   the question to make sure we're on the same page..."
  │
  ├─ If repeated (3+ times):
  │   AI: "It seems like some of my questions aren't connecting.
  │        That's okay — let's move on to the next topic."
  │
  ├─ Harmful/abusive content:
  │   AI: "I want to keep this conversation professional.
  │        Let's focus on the role and your experience."
  │   → Flagged in evaluation: "⚠️ Unprofessional responses detected"
  │
  └─ All flagged for HR review in transcript
```

---

## 📱 Flow 6: Mobile Experience

### Candidate on Mobile

```
• Interview link opens in mobile browser (no app needed)
• Full-screen chat interface
• Large touch-friendly input field
• Auto-scroll to latest message
• Resume upload via camera (photo of resume) or file picker
• Progress bar at top (minimal chrome)
• Keyboard doesn't obscure chat history
```

### HR on Mobile (Phase 3+)

```
• Responsive dashboard
• Swipe to shortlist/reject candidates
• Push notifications: "New candidate completed interview"
• Quick review: AI summary + score (tap for full details)
```

---

## 📊 Flow Metrics to Track Per Step

| Flow Step | Metric | Target |
|-----------|--------|--------|
| Landing page → Start Interview | Click-through rate | >80% |
| Resume upload → Complete | Upload success rate | >95% |
| Interview start → Complete | Completion rate | >75% |
| Interview complete → HR review | Time to first review | <24 hrs |
| HR review → Action (shortlist/reject) | Decision rate | >90% within 48hrs |
| Rejection → Candidate notified | Notification sent | 100% (automated) |
| Abandoned → Resumed | Resume rate (after reminder) | >30% |
