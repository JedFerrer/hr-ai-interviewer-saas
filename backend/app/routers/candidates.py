"""Candidate router: detail, shortlist, reject."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

from fastapi import BackgroundTasks, APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import get_settings
from app.models.user import User
from app.schemas.candidate import (
    CandidateDetailResponse,
    EvaluationResponse,
    InterviewSummaryResponse,
    PreScreenSummary,
    SendNotificationRequest,
    SendNotificationResponse,
    StatusUpdateRequest,
)
from app.services import candidate_service
from app.utils.security import csrf_protect, get_current_user

router = APIRouter(prefix="/candidates", tags=["candidates"], dependencies=[Depends(csrf_protect)])


def _build_pre_screen_summary(candidate) -> PreScreenSummary | None:
    """Bundle pre-screen-related columns into a response object, if any are set."""
    has_data = any(
        getattr(candidate, name) is not None
        for name in (
            "resume_match_score",
            "resume_match_confidence",
            "pre_screen_decision",
            "pre_screen_reason",
            "resume_match_breakdown",
            "pre_screened_at",
            "invite_sent_at",
        )
    )
    if not has_data:
        return None
    return PreScreenSummary(
        score=(
            float(candidate.resume_match_score)
            if candidate.resume_match_score is not None
            else None
        ),
        confidence=(
            float(candidate.resume_match_confidence)
            if candidate.resume_match_confidence is not None
            else None
        ),
        decision=candidate.pre_screen_decision,
        reason=candidate.pre_screen_reason,
        breakdown=candidate.resume_match_breakdown,
        pre_screened_at=candidate.pre_screened_at,
        invite_sent_at=candidate.invite_sent_at,
    )


def _build_detail_response(
    candidate,
    *,
    interview: InterviewSummaryResponse | None = None,
    evaluation: EvaluationResponse | None = None,
) -> CandidateDetailResponse:
    """Single source of truth for the candidate-detail payload.

    Reads `auto_send_status_emails` from the eagerly-loaded job_posting and
    surfaces the most recent candidate notification so the UI can warn HR
    before triggering a status change or a contradictory email.
    """
    job = getattr(candidate, "job_posting", None)
    # Expose a usable capability only on the tenant-authorized detail response.
    # Never add this to public application status or candidate list responses.
    interview_link = None
    expires = candidate.interview_link_expires_at
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if (interview is not None and candidate.status in {"ready", "in_progress"}
            and candidate.interview_token and expires and expires > datetime.now(timezone.utc)):
        interview_link = f"{get_settings().app_url}/interview/session/{candidate.interview_token}"
    return CandidateDetailResponse(
        id=candidate.id,
        name=candidate.name,
        email=candidate.email,
        status=candidate.status,
        resume_url=candidate.resume_url,
        resume_parsed_data=candidate.resume_parsed_data,
        interview=interview,
        interview_link=interview_link,
        evaluation=evaluation,
        pre_screen=_build_pre_screen_summary(candidate),
        job_auto_send_status_emails=bool(
            getattr(job, "auto_send_status_emails", False)
        ),
        last_notification_kind=candidate.last_status_email_kind,
        last_notification_sent_at=candidate.last_status_email_sent_at,
        created_at=candidate.created_at,
    )


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

    return _build_detail_response(
        candidate,
        interview=interview_resp,
        evaluation=evaluation_resp,
    )


@router.post("/{candidate_id}/approve-interview", response_model=CandidateDetailResponse)
async def approve_interview(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """HR action: approve a candidate awaiting pre-screen review.

    Generates the interview, marks the candidate `ready`, and emails the
    invite link. Only valid for candidates currently in `review_pending`
    (or `error` as a manual rescue path).
    """
    candidate = await candidate_service.approve_pre_screen(
        db, candidate_id, user.company_id,
        actor_user_id=user.id, actor_name=user.name,
    )
    return _build_detail_response(candidate)


@router.post("/{candidate_id}/reject-pre-screen", response_model=CandidateDetailResponse)
async def reject_pre_screen(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """HR action: reject a candidate awaiting pre-screen review (no interview)."""
    candidate = await candidate_service.reject_pre_screen(
        db, candidate_id, user.company_id,
        actor_user_id=user.id, actor_name=user.name,
    )
    return _build_detail_response(candidate)


@router.post("/{candidate_id}/shortlist", response_model=CandidateDetailResponse)
async def shortlist_candidate(
    candidate_id: str,
    body: StatusUpdateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Move candidate to shortlisted status. Does NOT send an email — use
    `POST /candidates/{id}/send-notification` to notify the candidate.
    """
    candidate = await candidate_service.update_candidate_status(
        db, candidate_id, user.company_id, "shortlisted",
        actor_user_id=user.id, actor_name=user.name,
    )
    return _build_detail_response(candidate)


@router.post("/{candidate_id}/reject", response_model=CandidateDetailResponse)
async def reject_candidate(
    candidate_id: str,
    body: StatusUpdateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Move candidate to rejected status. Does NOT send an email — use
    `POST /candidates/{id}/send-notification` to notify the candidate.
    """
    candidate = await candidate_service.update_candidate_status(
        db, candidate_id, user.company_id, "rejected",
        actor_user_id=user.id, actor_name=user.name,
    )
    return _build_detail_response(candidate)


@router.post(
    "/{candidate_id}/send-notification",
    response_model=SendNotificationResponse,
)
async def send_candidate_notification(
    candidate_id: str,
    body: SendNotificationRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Explicitly email the candidate about their current status.

    Returns 409 with a `notification_conflict` payload when the new email
    would contradict the previously-sent one (e.g. reject → shortlist) and
    `force` is not set. The frontend handles the 409 by prompting HR to
    either confirm the override or send a `status_correction` email first.
    """
    candidate, sent = await candidate_service.send_status_notification(
        db,
        candidate_id,
        user.company_id,
        kind=body.kind,
        force=body.force,
    )
    return SendNotificationResponse(
        sent=sent,
        kind=body.kind,
        last_notification_kind=candidate.last_status_email_kind,
        last_notification_sent_at=candidate.last_status_email_sent_at,
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
    if not resolved.is_relative_to(uploads_root):
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


@router.post("/{candidate_id}/retry-invite")
async def retry_interview_invite(candidate_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    delivered = await candidate_service.retry_interview_email(db, candidate_id, user.company_id)
    if not delivered:
        raise HTTPException(status_code=503, detail="Email delivery unavailable; retry after checking provider configuration")
    return {"sent": True}


@router.post("/{candidate_id}/retry-processing", status_code=202)
async def retry_processing(candidate_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    from app.services.interview_service import process_application_background
    job_id, content, filename = await candidate_service.prepare_processing_retry(db, candidate_id, user.company_id)
    background_tasks.add_task(process_application_background, candidate_id=candidate_id, job_id=job_id, file_content=content, filename=filename)
    return {"status": "processing"}
