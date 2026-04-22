"""Interview router: public endpoints (token-based, no JWT)."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.interview import (
    ApplicationResponse,
    ApplicationStatusResponse,
    InterviewLandingResponse,
    InterviewMessageRequest,
    InterviewMessageResponse,
    InterviewStartResponse,
    InterviewStatusResponse,
    SessionLandingResponse,
    SessionStartResponse,
)
from app.services import interview_service

router = APIRouter(prefix="/interview", tags=["interview"])


# ---------------------------------------------------------------------------
# Phase A — Application (public)
# ---------------------------------------------------------------------------

@router.get("/{job_token}", response_model=InterviewLandingResponse)
async def interview_landing(
    job_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Get job info for the application landing page (public)."""
    job = await interview_service.get_job_by_token(db, job_token)
    return InterviewLandingResponse(
        job_title=job.title,
        company_name=job.company.name,
        description=job.description,
    )


@router.post("/apply", response_model=ApplicationResponse)
async def apply(
    background_tasks: BackgroundTasks,
    job_token: str = Form(...),
    candidate_name: str = Form(...),
    candidate_email: str = Form(...),
    resume: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Submit an application. Returns immediately; processing happens in background."""
    job = await interview_service.get_job_by_token(db, job_token)
    file_content = await resume.read()

    candidate = await interview_service.apply(
        db=db,
        job=job,
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        file_content=file_content,
        filename=resume.filename or "resume.pdf",
    )

    # Kick off background processing (resume parse → question gen → email)
    background_tasks.add_task(
        interview_service.process_application_background,
        candidate_id=candidate.id,
        job_id=job.id,
        file_content=file_content,
        filename=resume.filename or "resume.pdf",
    )

    return ApplicationResponse(
        message="Application received! We'll email you an interview link shortly.",
        candidate_id=candidate.id,
        interview_token=candidate.interview_token,
        status="processing",
    )


@router.get("/apply/{interview_token}/status", response_model=ApplicationStatusResponse)
async def application_status(
    interview_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Check if application processing is complete (poll endpoint)."""
    from sqlalchemy import select
    from app.models.candidate import Candidate
    from app.config import get_settings

    settings = get_settings()

    result = await db.execute(
        select(Candidate).where(Candidate.interview_token == interview_token)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    interview_link = None
    if candidate.status == "ready":
        interview_link = f"{settings.app_url}/interview/session/{candidate.interview_token}"

    return ApplicationStatusResponse(
        status=candidate.status,
        interview_link=interview_link,
    )


# ---------------------------------------------------------------------------
# Phase B — Interview session (public)
# ---------------------------------------------------------------------------

@router.get("/session/{interview_token}", response_model=SessionLandingResponse)
async def session_landing(
    interview_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Get interview session info for the candidate (public)."""
    data = await interview_service.get_session_landing(db, interview_token)
    return SessionLandingResponse(**data)


@router.post("/session/{interview_token}/start", response_model=SessionStartResponse)
async def session_start(
    interview_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Start the interview session. Questions are pre-loaded — just generates the opening message."""
    token, first_msg, total = await interview_service.begin_session(db, interview_token)
    return SessionStartResponse(
        interview_token=token,
        first_message=first_msg,
        total_questions=total,
    )


@router.post("/message", response_model=InterviewMessageResponse)
async def interview_message(
    data: InterviewMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a candidate answer and receive the next AI response (public)."""
    ai_response, progress, is_complete, is_last_question = await interview_service.process_message(
        db=db,
        interview_token=data.interview_token,
        candidate_message=data.message,
        integrity_signals=data.integrity_signals,
    )
    return InterviewMessageResponse(
        ai_response=ai_response,
        progress=progress,
        is_complete=is_complete,
        is_last_question=is_last_question,
    )


# ---------------------------------------------------------------------------
# Legacy (kept for backward compat)
# ---------------------------------------------------------------------------

@router.post("/start", response_model=InterviewStartResponse, deprecated=True)
async def start_interview(
    background_tasks: BackgroundTasks,
    job_token: str = Form(...),
    candidate_name: str = Form(...),
    candidate_email: str = Form(...),
    resume: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Legacy: Start a new interview (redirects through new two-phase flow)."""
    job = await interview_service.get_job_by_token(db, job_token)
    file_content = await resume.read()

    candidate = await interview_service.apply(
        db=db,
        job=job,
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        file_content=file_content,
        filename=resume.filename or "resume.pdf",
    )

    # Process synchronously for legacy compat (blocks but works)
    await interview_service.process_application_background(
        candidate_id=candidate.id,
        job_id=job.id,
        file_content=file_content,
        filename=resume.filename or "resume.pdf",
    )

    # Now begin the session
    token, first_msg, total = await interview_service.begin_session(db, candidate.interview_token)
    return InterviewStartResponse(
        interview_token=token,
        first_question=first_msg,
        total_questions=total,
    )


@router.get("/{interview_token}/status", response_model=InterviewStatusResponse)
async def interview_status(
    interview_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Check interview status (public)."""
    from sqlalchemy import select
    from app.models.candidate import Candidate
    from app.models.interview import Interview

    result = await db.execute(
        select(Interview)
        .join(Candidate, Interview.candidate_id == Candidate.id)
        .where(Candidate.interview_token == interview_token)
    )
    interview = result.scalar_one_or_none()
    if not interview:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    questions = interview.planned_questions or []
    progress = f"{interview.current_question_index}/{len(questions)}"
    return InterviewStatusResponse(status=interview.status, progress=progress)

    questions = interview.planned_questions or []
    progress = f"{interview.current_question_index}/{len(questions)}"
    return InterviewStatusResponse(status=interview.status, progress=progress)
