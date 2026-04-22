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
        "overall_score": 8.5, "skill_match": 9.0, "communication": 8.0,
        "problem_solving": 8.5, "cultural_fit": 8.5,
        "summary": "Strong full-stack engineer with excellent technical depth. Demonstrated solid understanding of scalable architecture patterns. Communication was clear and structured.",
        "strengths": ["Deep React/TypeScript expertise", "Production experience at scale (Stripe)", "Strong system design thinking"],
        "gaps": ["Limited experience with our specific tech stack (no GraphQL at scale)"],
        "red_flags": [],
        "recommendation": "strong_hire",
    },
    "Priya Sharma": {
        "overall_score": 7.2, "skill_match": 7.5, "communication": 7.5,
        "problem_solving": 7.0, "cultural_fit": 7.0,
        "summary": "Solid engineer with good breadth of skills. Answers were competent but lacked the depth expected for a senior role. Good cultural fit.",
        "strengths": ["Good breadth across frontend and backend", "Strong e-commerce domain knowledge"],
        "gaps": ["Less experience with AWS infrastructure", "Problem-solving approach was somewhat linear"],
        "red_flags": [],
        "recommendation": "hire",
    },
    "Maya Patel": {
        "overall_score": 9.0, "skill_match": 9.5, "communication": 9.0,
        "problem_solving": 8.5, "cultural_fit": 9.0,
        "summary": "Exceptional product designer with a portfolio that speaks for itself. Articulated design decisions with clarity and showed deep empathy for users.",
        "strengths": ["World-class portfolio (Airbnb design system)", "Excellent communication and storytelling", "Research-driven design approach"],
        "gaps": ["Limited experience with B2B products"],
        "red_flags": [],
        "recommendation": "strong_hire",
    },
    "Raj Gupta": {
        "overall_score": 8.8, "skill_match": 9.0, "communication": 8.5,
        "problem_solving": 9.0, "cultural_fit": 8.5,
        "summary": "Highly skilled DevOps engineer with deep Kubernetes and cloud expertise. Solved the infrastructure scenario flawlessly. Great incident response mindset.",
        "strengths": ["Expert-level Kubernetes knowledge", "Netflix-scale production experience", "Strong incident management skills"],
        "gaps": ["Salary expectations may be above our range"],
        "red_flags": [],
        "recommendation": "strong_hire",
    },
    "Dr. Liam Zhang": {
        "overall_score": 9.2, "skill_match": 9.5, "communication": 8.5,
        "problem_solving": 9.5, "cultural_fit": 8.5,
        "summary": "Outstanding ML engineer with rare combination of research depth and production experience. Answered every technical question with exceptional clarity.",
        "strengths": ["PhD-level NLP expertise", "Production ML deployment experience at OpenAI", "Published researcher with strong fundamentals"],
        "gaps": ["May prefer research over product engineering"],
        "red_flags": [],
        "recommendation": "strong_hire",
    },
    "Carlos Mendez": {
        "overall_score": 4.5, "skill_match": 4.0, "communication": 6.0,
        "problem_solving": 4.0, "cultural_fit": 5.5,
        "summary": "Candidate shows potential but lacks the production ML engineering experience required for this role. Responses to system design questions were surface-level.",
        "strengths": ["Good communication skills", "Enthusiastic about learning"],
        "gaps": ["No production ML pipeline experience", "Limited PyTorch knowledge", "No deployment/MLOps experience"],
        "red_flags": ["Misrepresented experience level on resume"],
        "recommendation": "no_hire",
    },
    "Sophie Chen": {
        "overall_score": 7.8, "skill_match": 8.0, "communication": 8.0,
        "problem_solving": 7.5, "cultural_fit": 7.5,
        "summary": "Strong data analyst with excellent SQL and dashboarding skills. Good understanding of experimentation methodology. Would be productive quickly.",
        "strengths": ["Expert SQL skills", "Strong A/B testing knowledge", "Experience with our BI stack"],
        "gaps": ["Python skills are basic compared to top candidates"],
        "red_flags": [],
        "recommendation": "hire",
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
                # Build a realistic transcript
                q_count = 5 if has_eval else 3  # completed interviews have more questions
                transcript = []
                sample_questions = [
                    "Tell me about your most challenging technical project.",
                    "How do you approach debugging a production issue?",
                    "Describe your experience with the technologies listed in this role.",
                    "Walk me through how you would design a scalable system for this use case.",
                    "How do you handle disagreements with team members on technical decisions?",
                ]
                sample_answers = [
                    f"At {resume['current_role'].split(' at ')[-1] if resume else 'my company'}, I led a project that...",
                    "My approach starts with checking monitoring dashboards, then narrowing down with logs...",
                    f"I have {resume['experience_years'] if resume else 3} years working with these technologies...",
                    "I'd start by identifying the key requirements: throughput, latency, and data consistency...",
                    "I believe in data-driven discussions. When there's a disagreement, I propose we...",
                ]

                for i in range(q_count):
                    transcript.append({"role": "ai", "content": sample_questions[i]})
                    transcript.append({"role": "candidate", "content": sample_answers[i]})

                interview_status = "completed" if has_eval else "in_progress"
                interview = Interview(
                    candidate_id=candidate.id,
                    job_posting_id=jobs[jidx].id,
                    transcript=transcript,
                    planned_questions=sample_questions,
                    current_question_index=q_count,
                    status=interview_status,
                    total_prompt_tokens=1200 * q_count,
                    total_completion_tokens=800 * q_count,
                    cost_usd=round(0.002 * q_count, 4),
                    started_at=_days_ago(jidx + 3),
                    completed_at=_days_ago(jidx + 2) if has_eval else None,
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
