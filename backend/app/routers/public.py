"""Public, unauthenticated routes for shared evaluation reports."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.share import (
    PublicEvaluation,
    PublicReportResponse,
    PublicTranscriptMessage,
)
from app.services import share_service

# No auth, no CSRF — fully public, but the URL contains an unguessable token.
router = APIRouter(prefix="/public", tags=["public"])


@router.get("/report/{token}", response_model=PublicReportResponse)
async def get_public_report(
    token: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Render a candidate's evaluation report for a hiring manager.

    Returns 404 for any invalid / expired / revoked token (no enumeration).
    Excludes HR-internal data (email, resume URL, integrity signals,
    cost telemetry).
    """
    # Stop search engines from indexing shared reports.
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["Cache-Control"] = "no-store"

    candidate = await share_service.resolve_share_token(db, token)

    interview = candidate.interview
    evaluation_dto = None
    transcript_dto: list[PublicTranscriptMessage] = []
    if interview:
        if interview.evaluation:
            ev = interview.evaluation
            evaluation_dto = PublicEvaluation(
                overall_score=float(ev.overall_score) if ev.overall_score is not None else None,
                scores={
                    "skill_match": float(ev.skill_match) if ev.skill_match is not None else None,
                    "communication": (
                        float(ev.communication) if ev.communication is not None else None
                    ),
                    "problem_solving": (
                        float(ev.problem_solving) if ev.problem_solving is not None else None
                    ),
                    "cultural_fit": (
                        float(ev.cultural_fit) if ev.cultural_fit is not None else None
                    ),
                },
                summary=ev.summary,
                strengths=ev.strengths,
                gaps=ev.gaps,
                recommendation=ev.recommendation,
            )
        if interview.transcript:
            transcript_dto = [
                PublicTranscriptMessage(
                    role=str(m.get("role", "")),
                    content=str(m.get("content", "")),
                    timestamp=str(m["timestamp"]) if m.get("timestamp") else None,
                )
                for m in interview.transcript
                if isinstance(m, dict)
            ]

    return PublicReportResponse(
        candidate_name=candidate.name,
        job_title=candidate.job_posting.title,
        company_name=candidate.job_posting.company.name if candidate.job_posting.company else "",
        completed_at=candidate.completed_at,
        evaluation=evaluation_dto,
        transcript=transcript_dto,
        expires_at=candidate.__share_expires_at,  # type: ignore[attr-defined]
    )
