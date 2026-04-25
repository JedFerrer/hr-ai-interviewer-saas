"""Seed the database with realistic dummy data for development/testing."""

from __future__ import annotations

import asyncio
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database import async_session_factory, engine
from app.models import Base
from app.models.candidate import Candidate
from app.models.company import Company
from app.models.evaluation import EvaluationRecord
from app.models.interview import Interview
from app.models.job_posting import JobPosting
from app.models.user import User
from app.utils.security import hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _token(n: int = 32) -> str:
    return secrets.token_urlsafe(n)[:n]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _days_ago(n: int) -> datetime:
    return _utc_now() - timedelta(days=n)


# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

COMPANIES = [
    {"name": "TechCorp Solutions", "logo_url": None},
    {"name": "InnovateLab Inc.", "logo_url": None},
]

# password for all seeded users is "Password123!"
PASSWORD_HASH = hash_password("Password123!")

USERS = [
    # company_index, email, name, role
    (0, "admin@techcorp.com", "Sarah Chen", "admin"),
    (0, "recruiter@techcorp.com", "Mike Johnson", "recruiter"),
    (1, "admin@innovatelab.com", "Emily Davis", "admin"),
]

JOBS = [
    # company_idx, creator_idx, title, description, department, location, emp_type, skills, status
    (
        0, 0,
        "Senior Full-Stack Engineer",
        "We are looking for an experienced Full-Stack Engineer to join our growing engineering team. "
        "You will design, build, and maintain scalable web applications using React, Node.js, and PostgreSQL. "
        "Ideal candidates have 5+ years of professional experience and a passion for clean code.",
        "Engineering",
        "San Francisco, CA (Hybrid)",
        "full_time",
        ["React", "TypeScript", "Node.js", "PostgreSQL", "AWS"],
        "active",
    ),
    (
        0, 0,
        "Product Designer",
        "Join our design team and shape the user experience of products used by millions. "
        "You will collaborate closely with engineering and product management to create intuitive, "
        "beautiful interfaces. Requires strong Figma skills and a portfolio demonstrating UX thinking.",
        "Design",
        "Remote",
        "full_time",
        ["Figma", "UX Research", "Prototyping", "Design Systems"],
        "active",
    ),
    (
        0, 1,
        "DevOps Engineer",
        "We need a DevOps Engineer to build and maintain our CI/CD pipelines, manage Kubernetes clusters, "
        "and ensure 99.9%+ uptime across our cloud infrastructure. Experience with Terraform, Docker, "
        "and AWS/GCP required. On-call rotation participation expected.",
        "Engineering",
        "New York, NY",
        "full_time",
        ["Kubernetes", "Docker", "Terraform", "AWS", "CI/CD"],
        "active",
    ),
    (
        1, 2,
        "Machine Learning Engineer",
        "InnovateLab is building next-generation AI products and needs a Machine Learning Engineer "
        "who can take models from research to production. You will work with PyTorch, design training "
        "pipelines, and deploy models at scale. PhD or equivalent experience preferred.",
        "AI/ML",
        "Boston, MA (Hybrid)",
        "full_time",
        ["Python", "PyTorch", "MLOps", "SQL", "Docker"],
        "active",
    ),
    (
        0, 0,
        "Frontend Developer (Contract)",
        "6-month contract for a skilled frontend developer to help migrate our legacy Angular app to React. "
        "Strong TypeScript skills required, along with experience in building accessible, responsive UIs. "
        "This is a great opportunity to work on a large-scale migration project.",
        "Engineering",
        "Remote",
        "contract",
        ["React", "TypeScript", "CSS", "Accessibility", "Testing"],
        "active",
    ),
    (
        1, 2,
        "Data Analyst",
        "We are looking for a Data Analyst to help drive business decisions through data. "
        "You will build dashboards, run A/B test analyses, and present findings to stakeholders. "
        "Proficiency in SQL, Python (pandas), and BI tools like Metabase or Looker is required.",
        "Data",
        "Remote",
        "full_time",
        ["SQL", "Python", "Pandas", "Metabase", "Statistics"],
        "active",
    ),
]

# Candidates: job_idx, name, email, status, resume_parsed, has_interview, has_evaluation
CANDIDATES = [
    # -- Job 0: Senior Full-Stack Engineer (4 candidates) --
    (0, "Alex Rivera", "alex.r@gmail.com", "completed", {
        "name": "Alex Rivera", "email": "alex.r@gmail.com",
        "experience_years": 7,
        "skills": ["React", "TypeScript", "Node.js", "PostgreSQL", "AWS", "GraphQL"],
        "education": "B.S. Computer Science, Stanford University",
        "current_role": "Senior Software Engineer at Stripe",
        "summary": "Full-stack engineer with 7 years of experience building payment infrastructure and web applications.",
    }, True, True),

    (0, "Priya Sharma", "priya.s@outlook.com", "completed", {
        "name": "Priya Sharma", "email": "priya.s@outlook.com",
        "experience_years": 5,
        "skills": ["React", "TypeScript", "Python", "Django", "PostgreSQL"],
        "education": "M.S. Software Engineering, Carnegie Mellon University",
        "current_role": "Software Engineer at Shopify",
        "summary": "Full-stack developer specializing in e-commerce platforms and payment systems.",
    }, True, True),

    (0, "Jordan Lee", "jordan.lee@protonmail.com", "in_progress", {
        "name": "Jordan Lee", "email": "jordan.lee@protonmail.com",
        "experience_years": 4,
        "skills": ["React", "JavaScript", "Node.js", "MongoDB", "Docker"],
        "education": "B.S. Computer Science, UC Berkeley",
        "current_role": "Software Engineer at Notion",
        "summary": "Frontend-focused full-stack engineer passionate about developer tools.",
    }, True, False),

    (0, "Sam Taylor", "sam.t@yahoo.com", "ready", None, False, False),

    # -- Job 1: Product Designer (3 candidates) --
    (1, "Maya Patel", "maya.p@gmail.com", "completed", {
        "name": "Maya Patel", "email": "maya.p@gmail.com",
        "experience_years": 6,
        "skills": ["Figma", "Sketch", "UX Research", "Design Systems", "Prototyping"],
        "education": "BFA Interaction Design, RISD",
        "current_role": "Senior Product Designer at Airbnb",
        "summary": "Product designer with 6 years of experience creating consumer-facing digital products.",
    }, True, True),

    (1, "Chris Kim", "chris.k@gmail.com", "in_progress", {
        "name": "Chris Kim", "email": "chris.k@gmail.com",
        "experience_years": 3,
        "skills": ["Figma", "UX Research", "Usability Testing", "Wireframing"],
        "education": "M.A. HCI, University of Michigan",
        "current_role": "UX Designer at Meta",
        "summary": "UX designer focused on research-driven design for social platforms.",
    }, True, False),

    (1, "Taylor Morgan", "taylor.m@outlook.com", "ready", None, False, False),

    # -- Job 2: DevOps Engineer (2 candidates) --
    (2, "Raj Gupta", "raj.g@gmail.com", "shortlisted", {
        "name": "Raj Gupta", "email": "raj.g@gmail.com",
        "experience_years": 8,
        "skills": ["Kubernetes", "Docker", "Terraform", "AWS", "CI/CD", "Prometheus"],
        "education": "B.Tech Computer Science, IIT Bombay",
        "current_role": "Senior DevOps Engineer at Netflix",
        "summary": "Infrastructure engineer with 8 years of experience managing large-scale cloud deployments.",
    }, True, True),

    (2, "Emma Wilson", "emma.w@hotmail.com", "in_progress", {
        "name": "Emma Wilson", "email": "emma.w@hotmail.com",
        "experience_years": 4,
        "skills": ["Docker", "AWS", "CI/CD", "Linux", "Python"],
        "education": "B.S. Information Systems, Georgia Tech",
        "current_role": "Cloud Engineer at Datadog",
        "summary": "Cloud engineer transitioning into a DevOps role with strong automation skills.",
    }, True, False),

    # -- Job 3: ML Engineer (3 candidates) --
    (3, "Dr. Liam Zhang", "liam.z@stanford.edu", "completed", {
        "name": "Dr. Liam Zhang", "email": "liam.z@stanford.edu",
        "experience_years": 5,
        "skills": ["Python", "PyTorch", "TensorFlow", "MLOps", "Kubernetes"],
        "education": "Ph.D. Computer Science (NLP), Stanford University",
        "current_role": "Research Scientist at OpenAI",
        "summary": "ML researcher and engineer with publications in top NLP venues, experience shipping production models.",
    }, True, True),

    (3, "Aisha Johnson", "aisha.j@gmail.com", "in_progress", {
        "name": "Aisha Johnson", "email": "aisha.j@gmail.com",
        "experience_years": 3,
        "skills": ["Python", "PyTorch", "SQL", "Docker", "Hugging Face"],
        "education": "M.S. Machine Learning, Georgia Tech",
        "current_role": "ML Engineer at Hugging Face",
        "summary": "Machine learning engineer specializing in NLP model fine-tuning and deployment.",
    }, True, False),

    (3, "Carlos Mendez", "carlos.m@gmail.com", "rejected", {
        "name": "Carlos Mendez", "email": "carlos.m@gmail.com",
        "experience_years": 2,
        "skills": ["Python", "scikit-learn", "SQL", "Tableau"],
        "education": "B.S. Statistics, UCLA",
        "current_role": "Junior Data Scientist at Lyft",
        "summary": "Data scientist with basic ML experience, limited production engineering background.",
    }, True, True),

    # -- Job 4: Frontend Developer Contract (2 candidates) --
    (4, "Nina Kowalski", "nina.k@gmail.com", "in_progress", {
        "name": "Nina Kowalski", "email": "nina.k@gmail.com",
        "experience_years": 6,
        "skills": ["React", "TypeScript", "Angular", "CSS", "Testing", "Accessibility"],
        "education": "B.S. Computer Science, University of Warsaw",
        "current_role": "Frontend Architect at Zalando",
        "summary": "Frontend specialist with deep experience migrating legacy Angular apps to React.",
    }, True, False),

    (4, "David Park", "david.p@gmail.com", "ready", None, False, False),

    # -- Job 5: Data Analyst (2 candidates) --
    (5, "Sophie Chen", "sophie.c@gmail.com", "completed", {
        "name": "Sophie Chen", "email": "sophie.c@gmail.com",
        "experience_years": 4,
        "skills": ["SQL", "Python", "Pandas", "Metabase", "Looker", "dbt"],
        "education": "M.S. Data Science, Columbia University",
        "current_role": "Senior Data Analyst at Spotify",
        "summary": "Data analyst driving product decisions through experimentation and dashboarding.",
    }, True, True),

    (5, "Omar Hassan", "omar.h@gmail.com", "ready", None, False, False),
]

# Evaluation templates for candidates that have evaluations
EVALUATIONS = {
    # candidate name -> evaluation data
    "Alex Rivera": {
        "overall_score": 8.5,
        "skill_match": 9.2,
        "communication": 7.8,
        "problem_solving": 8.6,
        "cultural_fit": 8.0,
        "summary": (
            "Strong full-stack engineer with exceptional technical depth across the entire stack. "
            "Demonstrated expert-level React/TypeScript and confident system design thinking. "
            "Communication was clear and concise throughout. Minor gaps in AWS infrastructure depth "
            "but compensated by strong production debugging instincts."
        ),
        "strengths": [
            "Deep React/TypeScript expertise with measurable production impact",
            "Strong system design intuition — correctly identified the N+1 trap in the live coding exercise",
            "7 years at Stripe gives credible experience with payment-grade reliability requirements",
        ],
        "gaps": [
            "AWS knowledge is breadth-level; hasn't owned infrastructure provisioning end-to-end",
            "Slightly verbose in answers — could sharpen concision",
        ],
        "red_flags": [],
        "recommendation": "strong_yes",
    },
    "Priya Sharma": {
        "overall_score": 6.8,
        "skill_match": 7.2,
        "communication": 7.5,
        "problem_solving": 6.4,
        "cultural_fit": 6.2,
        "summary": (
            "Competent engineer with solid e-commerce domain knowledge and a clean technical foundation. "
            "Answers showed familiarity with the stack but lacked depth expected at the senior level. "
            "Problem-solving approach was somewhat linear — didn't explore edge cases unprompted. "
            "Good team player by reputation but interview didn't surface strong technical leadership signals."
        ),
        "strengths": [
            "Good breadth across frontend and backend",
            "Strong familiarity with e-commerce patterns and Shopify-scale traffic",
            "Clear, professional communicator",
        ],
        "gaps": [
            "Problem-solving was surface-level — needed significant prompting for follow-up depth",
            "Limited AWS infrastructure experience; hasn't worked with IAM/VPC at a team level",
            "Senior-level bar is marginal — may need 12–18 months more scope",
        ],
        "red_flags": [],
        "recommendation": "maybe",
    },
    "Maya Patel": {
        "overall_score": 9.1,
        "skill_match": 9.4,
        "communication": 9.2,
        "problem_solving": 8.8,
        "cultural_fit": 8.8,
        "summary": (
            "Exceptional product designer with a portfolio that sets the bar for the role. "
            "Articulated every design decision with clarity, grounding aesthetic choices in user research. "
            "The Airbnb booking flow redesign case study showed rare end-to-end ownership — from ethnographic "
            "research through to shipped product. Only minor gap is limited B2B product exposure."
        ),
        "strengths": [
            "World-class portfolio demonstrating systems thinking at Airbnb scale",
            "Outstanding communication and design storytelling",
            "Research-driven process — doesn't design in a vacuum",
            "Ownership mindset: shipped a design system adopted by 40+ engineers",
        ],
        "gaps": [
            "Limited exposure to B2B/enterprise UX patterns",
        ],
        "red_flags": [],
        "recommendation": "strong_yes",
    },
    "Raj Gupta": {
        "overall_score": 8.7,
        "skill_match": 9.1,
        "communication": 8.3,
        "problem_solving": 9.0,
        "cultural_fit": 8.2,
        "summary": (
            "Highly skilled DevOps engineer who solved the live infrastructure scenario without hints. "
            "Kubernetes depth is genuine — described CRD patterns and operator model fluently. "
            "Strong incident-response mindset built from Netflix on-call experience. "
            "Salary expectations are above the budgeted band; flagged for hiring manager review."
        ),
        "strengths": [
            "Expert-level Kubernetes — described controller reconciliation loops accurately",
            "Netflix-scale production experience (managed 3,000-node EKS cluster)",
            "Incident-management mindset: proactive runbook culture, automated escalation",
        ],
        "gaps": [
            "Salary expectations (~$210k TC) likely above our band",
            "Communication style is direct to the point of brusqueness — may need onboarding support",
        ],
        "red_flags": [],
        "recommendation": "yes",
    },
    "Dr. Liam Zhang": {
        "overall_score": 9.3,
        "skill_match": 9.5,
        "communication": 8.7,
        "problem_solving": 9.6,
        "cultural_fit": 8.5,
        "summary": (
            "Outstanding ML engineer with a rare combination of research rigour and production delivery. "
            "Answered every technical question with exceptional clarity, including a live CUDA kernel optimisation "
            "question that caught previous candidates out. Published NLP researcher at OpenAI level who clearly "
            "also cares about shipping. Primary risk is preference drift back to pure research."
        ),
        "strengths": [
            "PhD-level NLP expertise with 4 published papers in top venues (ACL, NeurIPS)",
            "Production ML delivery at OpenAI scale — owned model serving infra for GPT-3.5 finetuning",
            "Rare combination: researcher who writes production-quality code",
        ],
        "gaps": [
            "Expressed ambivalence about product vs. research work — needs clarity on role scope before offer",
        ],
        "red_flags": [],
        "recommendation": "strong_yes",
    },
    "Carlos Mendez": {
        "overall_score": 3.8,
        "skill_match": 3.5,
        "communication": 5.5,
        "problem_solving": 3.2,
        "cultural_fit": 4.0,
        "summary": (
            "Candidate presents as a Data Scientist but the role requires production ML engineering. "
            "Could not explain gradient checkpointing, had no answer on MLOps tooling beyond 'I've heard of MLflow', "
            "and the PyTorch exercise revealed only scikit-learn familiarity. "
            "Communication was good but doesn't compensate for the technical gap. "
            "Resume materially overstated experience level."
        ),
        "strengths": [
            "Good interpersonal communication — would represent the team well externally",
            "Genuine enthusiasm for learning",
        ],
        "gaps": [
            "No working knowledge of PyTorch beyond tutorials",
            "Zero production MLOps experience (no CI for models, no serving infra)",
            "System design question produced a Jupyter notebook as 'the production system'",
        ],
        "red_flags": [
            "Resume lists 'ML Engineer at Lyft' but role was purely BI reporting per LinkedIn",
            "Could not name a single paper from the team's research area despite claiming familiarity",
        ],
        "recommendation": "no",
    },
    "Sophie Chen": {
        "overall_score": 7.6,
        "skill_match": 8.0,
        "communication": 8.1,
        "problem_solving": 7.2,
        "cultural_fit": 7.2,
        "summary": (
            "Strong data analyst with excellent SQL fluency and a mature experimentation mindset. "
            "Walked through a complex multi-variate A/B test interpretation correctly without prompting. "
            "Dashboarding skills are best-in-class — has shipped dbt models used by a 200-person org. "
            "Python is functional but not deep; data engineering tasks would require pairing with the platform team."
        ),
        "strengths": [
            "Expert SQL — window functions, CTEs, and query optimisation all fluent",
            "Sound statistical reasoning on A/B tests (identified Simpson's Paradox in the test case)",
            "Experience with our exact BI stack (Metabase + dbt)",
        ],
        "gaps": [
            "Python is analytical-only (pandas/numpy); no experience with pipelines or orchestration",
            "Less strong on defining metric frameworks from scratch — better at executing established ones",
        ],
        "red_flags": [],
        "recommendation": "yes",
    },
}


# ---------------------------------------------------------------------------
# Seed logic
# ---------------------------------------------------------------------------

async def seed() -> None:
    """Create all seed data in the database."""

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # Check if data already exists
        existing = (await db.execute(select(Company))).scalars().first()
        if existing:
            print("⚠️  Database already has data. Skipping seed.")
            print("   To re-seed, delete backend/hr_interviewer.db and run again.")
            return

        # ---- Companies ----
        companies: list[Company] = []
        for c in COMPANIES:
            company = Company(**c)
            db.add(company)
            companies.append(company)
        await db.flush()
        print(f"✅ Created {len(companies)} companies")

        # ---- Users ----
        users: list[User] = []
        for cidx, email, name, role in USERS:
            user = User(
                company_id=companies[cidx].id,
                email=email,
                password_hash=PASSWORD_HASH,
                name=name,
                role=role,
            )
            db.add(user)
            users.append(user)
        await db.flush()
        print(f"✅ Created {len(users)} users")

        # ---- Job Postings ----
        jobs: list[JobPosting] = []
        for cidx, uidx, title, desc, dept, loc, etype, skills, status in JOBS:
            job = JobPosting(
                company_id=companies[cidx].id,
                created_by=users[uidx].id,
                title=title,
                description=desc,
                department=dept,
                location=loc,
                employment_type=etype,
                required_skills=skills,
                status=status,
                interview_link_token=_token(32),
                interview_config={"num_questions": 8, "style": "standard"},
            )
            db.add(job)
            jobs.append(job)
        await db.flush()
        print(f"✅ Created {len(jobs)} job postings")

        # ---- Candidates, Interviews, Evaluations ----
        n_candidates = 0
        n_interviews = 0
        n_evaluations = 0

        for jidx, name, email, status, resume, has_interview, has_eval in CANDIDATES:
            candidate = Candidate(
                job_posting_id=jobs[jidx].id,
                name=name,
                email=email,
                status=status,
                resume_parsed_data=resume,
                interview_token=_token(32),
            )
            db.add(candidate)
            await db.flush()
            n_candidates += 1

            if has_interview:
                # Varied, candidate-specific transcript samples
                role_name = resume["current_role"].split(" at ")[-1] if resume else "my company"
                exp = resume["experience_years"] if resume else 3

                transcripts_by_name: dict[str, list[dict]] = {
                    "Alex Rivera": [
                        {"role": "ai", "content": "Tell me about the most technically challenging project you've shipped at Stripe."},
                        {"role": "candidate", "content": f"The most challenging was rebuilding our payment-retry orchestration. We had cascading failures causing a 2% revenue loss on partial network outages. I redesigned the state machine from a polling model to event-driven using Kafka, reduced retry latency by 60%, and eliminated the thundering-herd problem with exponential back-off with jitter."},
                        {"role": "ai", "content": "How do you approach debugging a production incident where the symptoms point to multiple possible causes?"},
                        {"role": "candidate", "content": "I start with the 'blast radius' question — which users are affected and in what percentage. Then I correlate deployment timestamps with the symptom onset. If those don't align I look at upstream dependencies via distributed traces. I avoid hypothesis-driven debugging early; data first."},
                        {"role": "ai", "content": "Design a URL shortener that needs to handle 10,000 writes and 1 million reads per second."},
                        {"role": "candidate", "content": "For writes I'd use a Snowflake-style ID generator for globally unique short codes without coordination. A Redis cluster handles hot reads with an 8-hour TTL. Persistent storage is Cassandra partitioned by short code. CDN sits in front for the top 1% of links. The write path is async — the client gets a response once the ID is generated, Cassandra write is fire-and-forget with dead-letter retry."},
                        {"role": "ai", "content": "What's your approach to code review?"},
                        {"role": "candidate", "content": "I split reviews into two passes: correctness and then style/architecture. Correctness blockers are non-negotiable — everything else I frame as suggestions with reasoning attached. I also use automated linting to avoid bikeshedding on formatting."},
                        {"role": "ai", "content": "Where do you see the biggest risk in your own skill set for this role?"},
                        {"role": "candidate", "content": "Honestly, deep AWS infrastructure ownership. I've consumed services extensively but haven't provisioned VPCs or designed multi-account architectures from scratch. I'd plan to pair with whoever owns infra in the first month to close that gap."},
                    ],
                    "Priya Sharma": [
                        {"role": "ai", "content": "Walk me through a high-impact feature you owned end-to-end at Shopify."},
                        {"role": "candidate", "content": "I built the instalment payment UI for Shopify Pay in 2023. I owned the frontend in React, integrated the backend instalment-calculation API, and coordinated with the compliance team for the disclosure copy. It launched to 40% of US merchants in the first week."},
                        {"role": "ai", "content": "Describe a time you had to make a technology trade-off under time pressure."},
                        {"role": "candidate", "content": "We needed real-time stock indicators on product pages for a Black Friday deadline. The 'right' solution was WebSockets but we had 2 weeks. I shipped polling at 30-second intervals with stale-while-revalidate, then replaced it with SSE three sprints later. Not perfect but it shipped on time and the UX was acceptable."},
                        {"role": "ai", "content": "How would you design the backend for a multi-tenant SaaS billing system?"},
                        {"role": "candidate", "content": "Row-level tenant isolation in PostgreSQL with a tenant_id on every table and RLS policies. Billing events land in an append-only ledger table. A separate billing-calculation service aggregates on a cron. Stripe handles the payment method vault — we never touch raw card data."},
                        {"role": "ai", "content": "What would you want to learn in this role that you haven't been able to at Shopify?"},
                        {"role": "candidate", "content": "More infrastructure ownership. At Shopify the platform team owns everything below the application layer. I'd like to get comfortable with Terraform and understand what it actually costs to run at scale."},
                    ],
                    "Maya Patel": [
                        {"role": "ai", "content": "Walk me through a design decision you made at Airbnb where you had to push back on stakeholder requests."},
                        {"role": "candidate", "content": "The growth team wanted to add a pop-up nudge on the booking confirmation screen to upsell experiences. My research showed it would reduce booking completion by an estimated 8% based on a similar pattern we'd tested. I presented the data, proposed an alternative placement in the post-booking email series, and we ended up with higher upsell revenue without the conversion loss."},
                        {"role": "ai", "content": "How do you approach a design problem when user research is contradicting stakeholder assumptions?"},
                        {"role": "candidate", "content": "I make the research visible first — share the session recordings, not just the synthesis. People trust what they see more than summaries. Then I frame the conversation around user goals rather than feature requests: 'The user needs X. This feature solves Y. Here's the gap.'"},
                        {"role": "ai", "content": "Describe your process for building a design system from scratch."},
                        {"role": "candidate", "content": "Start with an audit of existing UI — screenshot everything, group by pattern. Identify the top 20% of components that cover 80% of UI surface. Define tokens first (colour, spacing, typography) because they cascade into everything else. Get one engineering champion early so adoption isn't a fight later. Ship the system incrementally — a design system that isn't used is a failure."},
                        {"role": "ai", "content": "How do you measure the success of a design change?"},
                        {"role": "candidate", "content": "Depends on the goal. For conversion changes I look at funnel metrics in a controlled experiment. For usability changes I run moderated sessions with think-aloud protocol and track task completion rate and error rate. For systemic changes like a design system rollout, adoption rate by component and reduction in inconsistency bugs."},
                        {"role": "ai", "content": "What's your weakest area as a designer?"},
                        {"role": "candidate", "content": "Data visualisation for dense B2B dashboards. I've mostly worked on consumer products where simplicity is the default. I've been doing deliberate practice with Nightingale charts and complex table design but it's not yet at the same level as my consumer-product work."},
                    ],
                    "Raj Gupta": [
                        {"role": "ai", "content": "Describe the largest Kubernetes cluster you've operated in production."},
                        {"role": "candidate", "content": "At Netflix, a 3,200-node EKS cluster across three AZs, running about 800 deployments. We used Karpenter for autoscaling and custom admission controllers to enforce resource-limit policies. Average pod churn was around 15,000 per day."},
                        {"role": "ai", "content": "Walk me through how you'd respond to a situation where 30% of pods in a deployment are crash-looping."},
                        {"role": "candidate", "content": "First I'd check if it's a new deployment — if yes, roll back immediately while I investigate. If it's a running deployment I'd cordon the affected nodes to stop new scheduling, capture a heap dump and thread dump from a healthy pod for comparison, then check OOMKill events in the node conditions. Most crash loops I've seen are either OOM or misconfigured readiness probes blocking traffic that's already arriving."},
                        {"role": "ai", "content": "How do you approach secrets management at scale?"},
                        {"role": "candidate", "content": "External Secrets Operator syncing from AWS Secrets Manager or HashiCorp Vault, never hardcoded or in ConfigMaps. Secret rotation is automated with a lease-based model. Application code retrieves secrets at startup via the secrets mount, not environment variables, to avoid process listing exposure."},
                        {"role": "ai", "content": "What's your philosophy on on-call rotations and runbooks?"},
                        {"role": "candidate", "content": "Runbooks should be executable, not explanatory. Every alert links to a runbook that has a decision tree: 'If you see X, do Y, then check Z.' If the runbook requires deep knowledge to follow, the alert is too low-level. We also do post-mortems within 48 hours and convert every action item into a runbook update or automation ticket — not a 'be more careful' note."},
                    ],
                    "Dr. Liam Zhang": [
                        {"role": "ai", "content": "Tell me about a production ML system you designed and deployed."},
                        {"role": "candidate", "content": "At OpenAI I owned the finetuning serving infrastructure for GPT-3.5 custom models. The challenge was dynamic batching across models with wildly different sequence lengths. I implemented a priority queue with SLA-aware preemption, used FlashAttention for memory efficiency, and reduced P99 latency by 42% over the baseline vLLM setup through custom CUDA kernels for the specific batch shapes we saw in prod."},
                        {"role": "ai", "content": "What's gradient checkpointing and when would you use it?"},
                        {"role": "candidate", "content": "Gradient checkpointing trades compute for memory. During the forward pass you only store activations at checkpoint boundaries rather than the full computation graph. On the backward pass you recompute the activations between checkpoints on the fly. You use it when training large models that would OOM on your GPU memory without it — typically above a few billion parameters. The trade-off is roughly 30% more compute for a ~60% reduction in activation memory."},
                        {"role": "ai", "content": "How do you think about the gap between research and production for ML systems?"},
                        {"role": "candidate", "content": "The biggest gap is the evaluation problem. In research you have a benchmark; in production you have a distribution shift, latency constraints, and a user population that doesn't match your held-out test set. I spend a lot of time on monitoring — offline-to-online metric correlation, shadow mode deployment, and human eval pipelines that catch regressions the automated metrics miss."},
                        {"role": "ai", "content": "One of our concerns is that researchers sometimes prefer to stay in research mode. How do you think about the product-vs-research tension?"},
                        {"role": "candidate", "content": "I understand the concern. Honestly I've shipped enough systems that I find production deeply interesting — the feedback loop is so much faster than waiting for a paper review. The part I find most rewarding is when a model I built is making real decisions for real users. That said, I'd want to be clear with you about the expectation split up front, because a role that's 100% maintenance without any research budget would eventually push me back to academia."},
                        {"role": "ai", "content": "What's your greatest research contribution?"},
                        {"role": "candidate", "content": "My NeurIPS 2022 paper on efficient long-context attention — we got 4x context length extension with sublinear memory growth. It's been cited 340 times and is the basis for the sliding window attention in Mistral's architecture."},
                    ],
                    "Carlos Mendez": [
                        {"role": "ai", "content": "Tell me about a machine learning model you've deployed to production."},
                        {"role": "candidate", "content": "I built a churn prediction model at Lyft using logistic regression on historical ride data. It runs in a Jupyter notebook that we export as a script and the data science team runs it monthly. The output goes into a Tableau dashboard."},
                        {"role": "ai", "content": "How would you serve a trained PyTorch model at 10,000 requests per second with P99 under 100ms?"},
                        {"role": "candidate", "content": "I would... probably use Flask? I've seen tutorials that show how to wrap a model in a Flask endpoint. I haven't personally done inference serving at that scale but I assume you'd add more servers."},
                        {"role": "ai", "content": "Can you explain gradient descent and why we use mini-batches?"},
                        {"role": "candidate", "content": "Gradient descent finds the minimum of the loss function by moving in the direction of the steepest descent. Mini-batches are used because... they're faster than using the full dataset? I know it's more efficient but I'd have to look up the exact reason."},
                        {"role": "ai", "content": "Describe a time you caught a data quality issue before it impacted a model."},
                        {"role": "candidate", "content": "I noticed that some rows in my training set had negative revenue values, which didn't make sense. I flagged it to my manager and we ended up filtering those out. The model accuracy went up slightly after that."},
                    ],
                    "Sophie Chen": [
                        {"role": "ai", "content": "Walk me through the most complex SQL query you've written in production."},
                        {"role": "candidate", "content": "A revenue attribution query at Spotify that joined seven tables across three data sources — user events, subscription history, and ad impression logs. It used a series of CTEs, window functions for sessionisation with a 30-minute inactivity timeout, and a final CASE-based attribution model that allocated revenue to the first touch in each session. Ran on ~2TB of daily data; I spent two days on query plan optimisation to get it under our 5-minute SLA."},
                        {"role": "ai", "content": "We have a dataset showing feature adoption is up 20% but revenue is flat. How do you approach diagnosing this?"},
                        {"role": "candidate", "content": "First I'd check if the adoption metric and revenue metric are even measuring the same user segment — cohort contamination is common. Then I'd look at the distribution of adoption: is the 20% lift concentrated in a low-LTV segment? I'd also check if there's a Simpson's Paradox situation where the aggregate looks flat but the per-segment trend is positive. Finally I'd verify the adoption event definition hasn't changed — metric definitions drift."},
                        {"role": "ai", "content": "How do you ensure data quality in a pipeline you own?"},
                        {"role": "candidate", "content": "dbt tests are my first line of defense — not-null, unique, accepted values, relationship tests for every model. For business logic validation I write custom schema tests that check domain rules like 'revenue should never be negative' or 'event timestamps should fall within business hours for this cohort.' I also set up monitoring with Great Expectations for distributions that shouldn't drift — things like order GMV staying within 3 standard deviations of the 30-day rolling average."},
                        {"role": "ai", "content": "Tell me about a finding you made that changed a product decision."},
                        {"role": "candidate", "content": "Spotify was considering removing the 'Fans also like' module from the artist page. The hypothesis was it reduced scroll depth. My analysis showed it had the highest click-through rate of any module on the page for users who were new to an artist, but near-zero for fans. I suggested personalisation — show it to first-time visitors, hide it for fans. The personalised version increased downstream stream depth by 8%."},
                    ],
                }

                transcript = transcripts_by_name.get(name)
                if not transcript:
                    # Generic fallback for candidates without a custom transcript
                    q_count = 5 if has_eval else 3
                    sample_questions = [
                        "Tell me about your most challenging technical project.",
                        "How do you approach debugging a production issue?",
                        "Describe your experience with the technologies listed in this role.",
                        "Walk me through how you would design a scalable system for this use case.",
                        "How do you handle disagreements with team members on technical decisions?",
                    ]
                    sample_answers = [
                        f"At {role_name}, I led a project that required cross-functional coordination across three teams...",
                        "My approach starts with reproducing the issue locally, then checking monitoring dashboards...",
                        f"I have {exp} years working with these technologies and have shipped multiple production systems...",
                        "I'd start by identifying the key requirements: throughput, latency, and data consistency...",
                        "I believe in data-driven discussions. When there's a disagreement, I propose we prototype both approaches...",
                    ]
                    transcript = []
                    for i in range(q_count):
                        transcript.append({"role": "ai", "content": sample_questions[i]})
                        transcript.append({"role": "candidate", "content": sample_answers[i]})

                completed_at_ts = _days_ago(jidx + 2) if has_eval else None

                # Set candidate.completed_at to match the interview
                if completed_at_ts:
                    candidate.completed_at = completed_at_ts

                interview_status = "completed" if has_eval else "in_progress"
                interview = Interview(
                    candidate_id=candidate.id,
                    job_posting_id=jobs[jidx].id,
                    transcript=transcript,
                    planned_questions=[m["content"] for m in transcript if m["role"] == "ai"],
                    current_question_index=len([m for m in transcript if m["role"] == "ai"]),
                    status=interview_status,
                    total_prompt_tokens=1200 * (len(transcript) // 2),
                    total_completion_tokens=800 * (len(transcript) // 2),
                    cost_usd=round(0.002 * (len(transcript) // 2), 4),
                    started_at=_days_ago(jidx + 3),
                    completed_at=completed_at_ts,
                )
                db.add(interview)
                await db.flush()
                n_interviews += 1

                if has_eval and name in EVALUATIONS:
                    ev_data = EVALUATIONS[name]
                    evaluation = EvaluationRecord(
                        interview_id=interview.id,
                        **ev_data,
                    )
                    db.add(evaluation)
                    await db.flush()
                    n_evaluations += 1

        await db.commit()
        print(f"✅ Created {n_candidates} candidates")
        print(f"✅ Created {n_interviews} interviews")
        print(f"✅ Created {n_evaluations} evaluations")
        print()
        print("=" * 50)
        print("🎉 Seed complete! Summary:")
        print(f"   Companies:   {len(companies)}")
        print(f"   Users:       {len(users)}")
        print(f"   Jobs:        {len(jobs)}")
        print(f"   Candidates:  {n_candidates}")
        print(f"   Interviews:  {n_interviews}")
        print(f"   Evaluations: {n_evaluations}")
        print()
        print("📋 Login credentials (all users):")
        print("   Password: Password123!")
        for _, email, name, role in USERS:
            print(f"   • {email} ({name}, {role})")
        print()


if __name__ == "__main__":
    asyncio.run(seed())
