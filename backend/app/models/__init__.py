"""Re-export all models so Alembic and relationships can discover them."""

from app.models.base import Base
from app.models.candidate import Candidate
from app.models.company import Company
from app.models.email_template import EmailTemplate
from app.models.evaluation import EvaluationRecord
from app.models.interview import Interview
from app.models.job_posting import JobPosting
from app.models.screening_outcome import ScreeningOutcome
from app.models.share_token import CandidateShareToken
from app.models.user import User
from app.models.user_invite import UserInvite

__all__ = [
    "Base",
    "Candidate",
    "CandidateShareToken",
    "Company",
    "EmailTemplate",
    "EvaluationRecord",
    "Interview",
    "JobPosting",
    "ScreeningOutcome",
    "User",
    "UserInvite",
]
