"""Re-export all models so Alembic and relationships can discover them."""

from app.models.base import Base
from app.models.candidate import Candidate
from app.models.company import Company
from app.models.evaluation import EvaluationRecord
from app.models.interview import Interview
from app.models.job_posting import JobPosting
from app.models.user import User

__all__ = [
    "Base",
    "Candidate",
    "Company",
    "EvaluationRecord",
    "Interview",
    "JobPosting",
    "User",
]
