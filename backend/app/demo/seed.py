"""Minimal migrated-database seed for the owned demo only."""

import asyncio
import importlib.util
import secrets
from pathlib import Path

from app.demo.guard import require_demo


async def seed():
    root = require_demo()
    from app.database import async_session_factory, engine
    from app.models.company import Company
    from app.models.job_posting import JobPosting
    from app.models.user import User
    from app.utils.security import hash_password

    async with async_session_factory() as db:
        for domain, name in [
            ("example.com", "Fictional Orchard Studio"),
            ("example.org", "Fictional Harbor Workshop"),
        ]:
            company = Company(name=name)
            db.add(company)
            await db.flush()
            admin = None
            for role in ("admin", "recruiter"):
                user = User(
                    company_id=company.id,
                    email=f"{role}@{domain}",
                    name=f"Fictional {role.title()}",
                    role=role,
                    password_hash=hash_password("PortfolioDemo123!"),
                )
                db.add(user)
                await db.flush()
                if role == "admin":
                    admin = user
            db.add(
                JobPosting(
                    company_id=company.id,
                    created_by=admin.id,
                    title="Python Backend Engineer",
                    department="Engineering",
                    location="Remote (fictional)",
                    description="Build and test Python FastAPI services using SQL. Fictional portfolio role.",
                    employment_type="Full-time",
                    required_skills=["Python", "FastAPI", "SQL"],
                    interview_config={"num_questions": 4},
                    interview_link_token=secrets.token_urlsafe(24),
                    auto_send_status_emails=False,
                )
            )
        await db.commit()
    await engine.dispose()
    source = (
        Path(__file__).resolve().parents[2] / "tests/fixtures/portfolio/generate.py"
    )
    spec = importlib.util.spec_from_file_location("portfolio_fixtures", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.generate(root / "fixtures")


if __name__ == "__main__":
    asyncio.run(seed())
