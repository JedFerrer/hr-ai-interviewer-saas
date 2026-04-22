"""Candidate router: detail, shortlist, reject."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.candidate import (
    CandidateDetailResponse,
    EvaluationResponse,
    InterviewSummaryResponse,
    StatusUpdateRequest,
)
from app.services import candidate_service
from app.utils.security import get_current_user

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("/{candidate_id}", response_model=CandidateDetailResponse)
async def get_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get full candidate detail with interview and evaluation."""
    candidate = await candidate_service.get_candidate_detail(db, candidate_id, user.company_id)

    interview_resp = None
    evaluation_resp = None

    if candidate.interview:
        iv = candidate.interview
        interview_resp = InterviewSummaryResponse(
            id=iv.id,
            status=iv.status,
            transcript=iv.transcript,
            transcript_length=len(iv.transcript or []),
            integrity_signals=iv.integrity_signals,
            cost_usd=float(iv.cost_usd),
            started_at=iv.started_at,
            completed_at=iv.completed_at,
        )

        if iv.evaluation:
            ev = iv.evaluation
            evaluation_resp = EvaluationResponse(
                overall_score=float(ev.overall_score) if ev.overall_score else None,
                scores={
                    "skill_match": float(ev.skill_match) if ev.skill_match else None,
                    "communication": float(ev.communication) if ev.communication else None,
                    "problem_solving": float(ev.problem_solving) if ev.problem_solving else None,
                    "cultural_fit": float(ev.cultural_fit) if ev.cultural_fit else None,
                },
                summary=ev.summary,
                strengths=ev.strengths,
                gaps=ev.gaps,
                red_flags=ev.red_flags,
                recommendation=ev.recommendation,
            )

    return CandidateDetailResponse(
        id=candidate.id,
        name=candidate.name,
        email=candidate.email,
        status=candidate.status,
        resume_url=candidate.resume_url,
        resume_parsed_data=candidate.resume_parsed_data,
        interview=interview_resp,
        evaluation=evaluation_resp,
        created_at=candidate.created_at,
    )


@router.post("/{candidate_id}/shortlist", response_model=CandidateDetailResponse)
async def shortlist_candidate(
    candidate_id: str,
    body: StatusUpdateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Move candidate to shortlisted status."""
    candidate = await candidate_service.update_candidate_status(
        db, candidate_id, user.company_id, "shortlisted"
    )
    return CandidateDetailResponse(
        id=candidate.id,
        name=candidate.name,
        email=candidate.email,
        status=candidate.status,
        resume_url=candidate.resume_url,
        resume_parsed_data=candidate.resume_parsed_data,
        created_at=candidate.created_at,
    )


@router.post("/{candidate_id}/reject", response_model=CandidateDetailResponse)
async def reject_candidate(
    candidate_id: str,
    body: StatusUpdateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Move candidate to rejected status."""
    candidate = await candidate_service.update_candidate_status(
        db, candidate_id, user.company_id, "rejected"
    )
    return CandidateDetailResponse(
        id=candidate.id,
        name=candidate.name,
        email=candidate.email,
        status=candidate.status,
        resume_url=candidate.resume_url,
        resume_parsed_data=candidate.resume_parsed_data,
        created_at=candidate.created_at,
    )


@router.get("/{candidate_id}/resume")
async def download_resume(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Download the candidate's resume file."""
    candidate = await candidate_service.get_candidate_detail(db, candidate_id, user.company_id)
    if not candidate.resume_url:
        raise HTTPException(status_code=404, detail="No resume uploaded for this candidate")

    file_path = Path(candidate.resume_url)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Resume file not found on disk")

    # Sanitize: ensure path stays within uploads/
    resolved = file_path.resolve()
    uploads_root = Path("uploads").resolve()
    if not str(resolved).startswith(str(uploads_root)):
        raise HTTPException(status_code=403, detail="Access denied")

    filename = f"{candidate.name.replace(' ', '_')}_resume{file_path.suffix}"
    media_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
    }
    media_type = media_types.get(file_path.suffix.lower(), "application/octet-stream")
    return FileResponse(
        path=resolved,
        filename=filename,
        media_type=media_type,
    )
