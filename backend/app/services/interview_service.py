"""Interview service: manages the AI interview flow with async LLM calls.

Two-phase architecture:
  Phase A — apply(): accept application + resume, process in background
  Phase B — begin_session() / process_message(): run the actual interview
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import async_session_factory
from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.job_posting import JobPosting
from app.services.email_service import send_interview_invite
from app.services.llm_client import get_async_openai_client, llm_chat_completion
from app.services.prompts import (
    FOLLOW_UP_DECISION_PROMPT,
    INTERVIEW_SYSTEM_PROMPT,
    JD_QUESTIONS_PROMPT,
    QUESTION_GENERATION_PROMPT,
    RESUME_QUESTIONS_PROMPT,
)
from app.services.resume_service import extract_text_from_bytes, parse_resume_with_llm_async
from app.utils.audit import audit
from app.utils.storage import (
    generate_storage_key,
    upload_file_local,
    validate_resume_content,
    validate_resume_file,
)
from app.utils.token_tracker import calculate_cost
from sqlalchemy.exc import IntegrityError, OperationalError

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_FOLLOW_UPS_PER_QUESTION = 2
CONTEXT_WINDOW_MESSAGES = 10
# Thresholds for repetition / parroting detection
_REPETITION_RATIO_THRESHOLD = 0.4  # if 40%+ of sentences are duplicates
_PARROTING_OVERLAP_THRESHOLD = 0.5  # if 50%+ of answer words come from the question

LLM_MODEL = settings.active_llm_model

# Strong references for fire-and-forget background tasks. Without this, the
# event loop only holds a weak reference and tasks may be GC'd mid-execution.
_BACKGROUND_TASKS: set[asyncio.Task] = set()

# SQLite can only handle a single writer at a time. When a burst of /apply
# calls fan out into background tasks that all try to write concurrently,
# they hit `database is locked` mid-flush — past the point where a commit
# retry can recover. Cap concurrency to keep the backend stable on SQLite.
# (Set high enough that Postgres deployments aren't bottlenecked.)
_BG_CONCURRENCY = int(os.environ.get("BG_PIPELINE_CONCURRENCY", "3"))
_BG_SEMAPHORE = asyncio.Semaphore(_BG_CONCURRENCY)


async def _commit_with_retry(db: AsyncSession, *, attempts: int = 4) -> None:
    """Commit with backoff on transient SQLite lock errors.

    Even with WAL + busy_timeout, bursts of concurrent background writes
    can still hit `OperationalError: database is locked` once the timeout
    is exhausted. Rather than failing the whole pipeline, back off briefly
    and retry — this is safe because we hold no other resource.
    """
    delay = 0.5
    for i in range(attempts):
        try:
            await db.commit()
            return
        except OperationalError as exc:
            msg = str(exc).lower()
            if "locked" not in msg and "busy" not in msg:
                raise
            if i == attempts - 1:
                logger.error("Commit failed after %d retries: %s", attempts, exc)
                raise
            logger.warning(
                "DB locked on commit (attempt %d/%d); backing off %.1fs",
                i + 1, attempts, delay,
            )
            try:
                await db.rollback()
            except Exception:
                pass
            await asyncio.sleep(delay)
            delay *= 2


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

async def get_job_by_token(db: AsyncSession, job_token: str) -> JobPosting:
    """Look up a job posting by its public interview link token."""
    result = await db.execute(
        select(JobPosting)
        .options(selectinload(JobPosting.company))
        .where(
            JobPosting.interview_link_token == job_token,
            JobPosting.status == "active",
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found or inactive")
    return job


# ---------------------------------------------------------------------------
# Phase A — Application
# ---------------------------------------------------------------------------

def normalize_email(email: str) -> str:
    """Normalize email: lowercase, strip +alias tags (Gmail-style).

    e.g. Ferrer.Jedidiah+123@Gmail.com → ferrer.jedidiah@gmail.com
    """
    email = email.strip().lower()
    local, _, domain = email.partition("@")
    if not domain:
        return email
    # Strip +alias tag from local part
    local = local.split("+", 1)[0]
    return f"{local}@{domain}"


async def apply(
    db: AsyncSession,
    job: JobPosting,
    candidate_name: str,
    candidate_email: str,
    file_content: bytes,
    filename: str,
) -> Candidate:
    """Accept an application. Saves candidate as 'processing' and returns immediately.

    The caller is responsible for kicking off process_application_background().
    Rejects duplicate applications (same normalized email + same job).
    """
    from fastapi import HTTPException, status

    normalized = normalize_email(candidate_email)

    # Test-email bypass — strictly opt-in via env. Never enabled in production.
    test_emails: set[str] = set()
    if settings.enable_test_emails and settings.test_emails:
        test_emails = {
            normalize_email(e) for e in settings.test_emails.split(",") if e.strip()
        }

    if normalized in test_emails:
        existing = await db.execute(
            select(Candidate).where(
                Candidate.normalized_email == normalized,
                Candidate.job_posting_id == job.id,
            )
        )
        old = existing.scalar_one_or_none()
        if old:
            await db.delete(old)
            await db.flush()
            logger.info(
                "Test email %s: deleted previous application for re-testing", normalized
            )
    else:
        # Pre-check for friendlier 409; DB unique constraint is the source of truth.
        existing = await db.execute(
            select(Candidate).where(
                Candidate.normalized_email == normalized,
                Candidate.job_posting_id == job.id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already applied for this position.",
            )

    # Validate file: extension + size, then magic-bytes (rejects spoofed types).
    try:
        validate_resume_file(filename, len(file_content))
        validate_resume_content(filename, file_content)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    storage_key = generate_storage_key(filename)
    resume_url = await upload_file_local(file_content, storage_key)

    interview_token = secrets.token_urlsafe(24)

    candidate = Candidate(
        job_posting_id=job.id,
        name=candidate_name,
        email=candidate_email,
        normalized_email=normalized,
        resume_url=resume_url,
        status="processing",
        interview_token=interview_token,
    )
    db.add(candidate)
    try:
        await db.commit()
    except IntegrityError:
        # Race: a concurrent request inserted the same (email, job) pair first.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already applied for this position.",
        )
    except OperationalError as exc:
        # SQLite "database is locked" or transient PG issue. Surface as 503
        # with Retry-After so the client (and load balancers) can back off
        # rather than treating it as a real server bug.
        await db.rollback()
        logger.warning("apply: transient DB error for %s: %s", normalized, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is busy, please retry in a few seconds.",
            headers={"Retry-After": "5"},
        ) from exc
    await db.refresh(candidate)
    audit(
        "candidate.applied",
        candidate_id=candidate.id,
        job_id=job.id,
        company_id=job.company_id,
    )
    return candidate


async def process_application_background(
    candidate_id: str,
    job_id: str,
    file_content: bytes,
    filename: str,
) -> None:
    """Background task: parse → score → decide → action.

    The pipeline:
      1. Parse resume into structured data (hard-fail on error → status=error).
      2. Score the resume against the job description.
      3. Apply the job's screening policy to pick a routing decision.
      4. For `auto_invite`: build the interview record, mark `ready`, email link.
         For `review`: stop here with status=`review_pending` (HR will approve later).

    Uses its own DB session (not the request session).
    """
    # Throttle concurrent pipelines to avoid SQLite write-lock storms.
    # (Manual acquire/release so we don't have to re-indent the whole body.)
    await _BG_SEMAPHORE.acquire()
    try:
      async with async_session_factory() as db:
        try:
            # Re-load candidate + job
            candidate = await db.get(Candidate, candidate_id)
            if not candidate:
                logger.error("Background: candidate %s not found", candidate_id)
                return

            result = await db.execute(
                select(JobPosting)
                .options(selectinload(JobPosting.company))
                .where(JobPosting.id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                logger.error("Background: job %s not found", job_id)
                return

            client = get_async_openai_client()
            total_pt, total_ct = 0, 0

            # 1. Parse resume
            try:
                resume_text = extract_text_from_bytes(file_content, filename)
                resume_data, pt, ct = await parse_resume_with_llm_async(client, resume_text)
                total_pt += pt
                total_ct += ct
            except (ValueError, json.JSONDecodeError) as exc:
                # Hard-fail: an interview built on dummy resume data produces
                # garbage questions and a misleading evaluation. Better to
                # surface the error to the HR user than ship bad data.
                logger.error(
                    "Resume parse failed for candidate %s: %s", candidate_id, exc
                )
                candidate.status = "error"
                candidate.pre_screen_decision = "error"
                candidate.pre_screen_reason = f"Resume could not be parsed: {exc}"
                candidate.pre_screened_at = datetime.now(timezone.utc)
                await _commit_with_retry(db)
                audit(
                    "candidate.resume_parse_failed",
                    candidate_id=candidate_id,
                    job_id=job_id,
                    reason=str(exc),
                )
                return

            candidate.resume_parsed_data = resume_data

            # 2. Score resume vs JD. A scorer failure is non-fatal — we fall
            #    through with score=None, and the decision engine will route
            #    the candidate to HR review under any non-`auto_all` policy.
            from app.services.resume_scoring_service import score_resume_match

            match_score: int | None = None
            match_confidence: float | None = None
            match_breakdown: dict | None = None
            try:
                match = await score_resume_match(
                    resume_data=resume_data,
                    job_title=job.title,
                    job_description=job.description,
                    required_skills=list(job.required_skills or []),
                )
                match_score = match["score"]
                match_confidence = match["confidence"]
                match_breakdown = {
                    "matched_skills": match["matched_skills"],
                    "missing_must_haves": match["missing_must_haves"],
                    "rationale": match["rationale"],
                    # Phase 2 / Item 8: surface the deterministic skill
                    # match alongside the LLM verdict so the UI can render
                    # evidence chips without re-running the LLM.
                    "deterministic_match": match["deterministic_match"],
                }
                total_pt += match["prompt_tokens"]
                total_ct += match["completion_tokens"]
            except Exception:
                logger.exception(
                    "Resume scoring failed for candidate %s; falling back to HR review",
                    candidate_id,
                )

            candidate.resume_match_score = match_score
            candidate.resume_match_confidence = match_confidence
            candidate.resume_match_breakdown = match_breakdown

            # 3. Apply screening policy.
            from app.services.screening_service import (
                ScreeningPolicy as _Policy,
                decide as _decide,
            )

            outcome = _decide(
                policy=_Policy(
                    mode=job.screening_mode or "auto_all",
                    auto_invite_threshold=job.auto_invite_threshold or 75,
                    review_threshold=job.review_threshold or 55,
                ),
                score=match_score,
                confidence=match_confidence,
            )
            candidate.pre_screen_decision = outcome.decision
            candidate.pre_screen_reason = outcome.reason
            candidate.pre_screened_at = datetime.now(timezone.utc)

            # Append-only calibration log: every prediction is recorded so
            # we can later compare against HR's ground-truth decision.
            from app.services.screening_outcome_service import record_prediction

            det_match = (match_breakdown or {}).get("deterministic_match") or {}
            await record_prediction(
                db=db,
                candidate_id=candidate_id,
                job_posting_id=job_id,
                score=match_score,
                confidence=match_confidence,
                decision=outcome.decision,
                matched_skills=det_match.get("matched_skills"),
                missing_skills=det_match.get("missing_skills"),
                deterministic_recall=det_match.get("recall"),
            )

            audit(
                "candidate.pre_screened",
                candidate_id=candidate_id,
                job_id=job_id,
                decision=outcome.decision,
                score=match_score,
            )

            if outcome.decision != "auto_invite":
                # Park the candidate; HR will approve/reject from the dashboard.
                candidate.status = "review_pending"
                await _commit_with_retry(db)
                logger.info(
                    "Candidate %s routed to %s (score=%s, mode=%s)",
                    candidate_id,
                    outcome.decision,
                    match_score,
                    job.screening_mode,
                )
                return

            # 4. Auto-invite path: generate questions, create interview, send email.
            await _build_interview_and_invite(
                db=db,
                candidate=candidate,
                job=job,
                resume_data=resume_data,
                client=client,
                running_pt=total_pt,
                running_ct=total_ct,
            )

        except Exception as exc:
            logger.exception("Background processing failed for candidate %s", candidate_id)
            # Mark candidate with error status using a fresh session (original may be broken)
            try:
                async with async_session_factory() as err_db:
                    candidate = await err_db.get(Candidate, candidate_id)
                    if candidate:
                        candidate.status = "error"
                        candidate.pre_screen_decision = "error"
                        candidate.pre_screen_reason = (
                            f"Background processing failed: {type(exc).__name__}: {exc}"
                        )[:500]
                        candidate.pre_screened_at = datetime.now(timezone.utc)
                        await _commit_with_retry(err_db)
            except Exception:
                logger.exception("Failed to revert candidate status")
    finally:
        _BG_SEMAPHORE.release()


async def _build_interview_and_invite(
    *,
    db: AsyncSession,
    candidate: Candidate,
    job: JobPosting,
    resume_data: dict,
    client: AsyncOpenAI,
    running_pt: int = 0,
    running_ct: int = 0,
) -> None:
    """Generate questions, persist the interview, mark candidate ready, send invite.

    Reused by the background pipeline (auto-invite branch) and by the HR
    `approve-interview` endpoint, so the side effects only live in one place.
    Caller owns the session; we commit before sending the email so DB state
    is durable even if the mail provider hiccups.
    """
    total_pt, total_ct = running_pt, running_ct

    num_questions = (job.interview_config or {}).get("num_questions", 8)
    num_resume_qs = 2  # always 2 personalized resume verification questions
    num_jd_qs = num_questions - num_resume_qs

    # Cached JD-based questions (per job).
    if job.cached_jd_questions and len(job.cached_jd_questions) >= num_jd_qs:
        jd_questions = job.cached_jd_questions[:num_jd_qs]
        logger.info("Reusing %d cached JD questions for job %s", num_jd_qs, job.id)
    else:
        jd_questions, pt, ct = await _generate_jd_questions(
            client, job.description, num_jd_qs
        )
        total_pt += pt
        total_ct += ct
        job.cached_jd_questions = jd_questions
        logger.info("Generated and cached %d JD questions for job %s", num_jd_qs, job.id)

    # Personalized resume verification questions.
    resume_questions, pt, ct = await _generate_resume_questions(
        client, resume_data, job.title, num_resume_qs
    )
    total_pt += pt
    total_ct += ct

    questions = resume_questions + jd_questions

    interview = Interview(
        candidate_id=candidate.id,
        job_posting_id=job.id,
        planned_questions=questions,
        status="not_started",
        total_prompt_tokens=total_pt,
        total_completion_tokens=total_ct,
        cost_usd=calculate_cost(LLM_MODEL, total_pt, total_ct),
    )
    db.add(interview)

    candidate.status = "ready"
    candidate.interview_link_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    candidate.invite_sent_at = datetime.now(timezone.utc)
    await _commit_with_retry(db)

    interview_link = f"{settings.app_url}/interview/session/{candidate.interview_token}"
    await send_interview_invite(
        candidate_email=candidate.email or "",
        candidate_name=candidate.name or "Candidate",
        job_title=job.title,
        company_name=job.company.name if job.company else "Company",
        interview_link=interview_link,
    )
    logger.info(
        "Interview invite sent for candidate %s — link: %s",
        candidate.id, interview_link,
    )


# ---------------------------------------------------------------------------
# Phase B — Interview session
# ---------------------------------------------------------------------------

async def get_session_landing(
    db: AsyncSession,
    interview_token: str,
) -> dict:
    """Get interview session info for the candidate landing page."""
    from fastapi import HTTPException, status as http_status

    result = await db.execute(
        select(Candidate)
        .options(
            selectinload(Candidate.job_posting).selectinload(JobPosting.company),
            selectinload(Candidate.interview),
        )
        .where(Candidate.interview_token == interview_token)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Interview not found")

    # Check link expiry (only for candidates who haven't started yet)
    if candidate.status == "ready" and candidate.interview_link_expires_at:
        expires = candidate.interview_link_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires:
            raise HTTPException(
                status_code=http_status.HTTP_410_GONE,
                detail="This interview link has expired. Please contact the hiring team.",
            )

    job = candidate.job_posting
    interview = candidate.interview
    total_q = len(interview.planned_questions or []) if interview else 0

    return {
        "job_title": job.title,
        "company_name": job.company.name if job.company else "",
        "candidate_name": candidate.name or "",
        "total_questions": total_q,
        "status": candidate.status,
    }


async def begin_session(
    db: AsyncSession,
    interview_token: str,
) -> tuple[str, str, int]:
    """Start an interview session. Questions are already generated — just produce the opening message.

    Returns (interview_token, first_message, total_questions).
    """
    from fastapi import HTTPException, status as http_status

    result = await db.execute(
        select(Candidate)
        .options(
            selectinload(Candidate.job_posting).selectinload(JobPosting.company),
            selectinload(Candidate.interview),
        )
        .where(Candidate.interview_token == interview_token)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Interview not found")

    # Check link expiry (only before interview starts)
    if candidate.status == "ready" and candidate.interview_link_expires_at:
        expires = candidate.interview_link_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires:
            raise HTTPException(
                status_code=http_status.HTTP_410_GONE,
                detail="This interview link has expired. Please contact the hiring team.",
            )

    if candidate.status not in ("ready", "in_progress"):
        if candidate.status == "processing":
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Your application is still being processed. Please wait a moment and try again.",
            )
        if candidate.status == "completed":
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="This interview has already been completed.",
            )
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Interview is in unexpected state: {candidate.status}",
        )

    interview = candidate.interview
    if not interview:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Interview record not found")

    # If already in_progress, return the last AI message (resume)
    if interview.status == "in_progress" and interview.transcript:
        last_ai = next(
            (m["content"] for m in reversed(interview.transcript) if m["role"] == "interviewer"),
            "",
        )
        return interview_token, last_ai, len(interview.planned_questions or [])

    # Generate opening message via LLM
    job = candidate.job_posting
    questions = interview.planned_questions or []
    resume_data = candidate.resume_parsed_data or {}

    questions_text = "\n".join(
        f"{i+1}. [{q['category']}] {q['question']}" for i, q in enumerate(questions)
    )
    system_prompt = INTERVIEW_SYSTEM_PROMPT.format(
        job_title=job.title,
        resume_summary=resume_data.get("summary", ""),
        jd_summary=job.description[:500],
        questions=questions_text,
    )

    client = get_async_openai_client()
    opening_response, _model = await llm_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Ask the first interview question directly. Be conversational but do not include any greeting or introduction — the candidate has already been welcomed."},
        ],
        temperature=0.5,
    )

    first_q = questions[0]["question"] if questions else "Tell me about yourself."
    opening_text = opening_response.choices[0].message.content or first_q

    # Update token tracking
    if opening_response.usage:
        interview.total_prompt_tokens += opening_response.usage.prompt_tokens
        interview.total_completion_tokens += opening_response.usage.completion_tokens
        interview.cost_usd = float(interview.cost_usd) + calculate_cost(
            LLM_MODEL,
            opening_response.usage.prompt_tokens,
            opening_response.usage.completion_tokens,
        )

    # Save state
    now_str = datetime.now(timezone.utc).isoformat()
    interview.transcript = [{"role": "interviewer", "content": opening_text, "question_index": 0, "timestamp": now_str}]
    interview.status = "in_progress"
    interview.started_at = datetime.now(timezone.utc)
    candidate.status = "in_progress"

    await db.commit()
    return interview_token, opening_text, len(questions)


async def process_message(
    db: AsyncSession,
    interview_token: str,
    candidate_message: str,
    integrity_signals: dict | None = None,
) -> tuple[str, str, bool]:
    """Process a candidate message. Returns (ai_response, progress, is_complete)."""
    from fastapi import HTTPException, status as http_status

    result = await db.execute(
        select(Interview)
        .options(
            selectinload(Interview.candidate),
            selectinload(Interview.job_posting),
        )
        .join(Candidate, Interview.candidate_id == Candidate.id)
        .where(Candidate.interview_token == interview_token)
    )
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Interview not found")

    if interview.status != "in_progress":
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Interview is {interview.status}, cannot accept messages",
        )

    candidate = interview.candidate
    job = interview.job_posting
    questions = interview.planned_questions or []
    current_idx = interview.current_question_index
    transcript = list(interview.transcript or [])

    # Hard cap on total messages to prevent LLM cost abuse
    if len(transcript) >= 50:
        raise HTTPException(
            status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Interview message limit reached",
        )

    # Append candidate message
    now_str = datetime.now(timezone.utc).isoformat()
    transcript.append({"role": "candidate", "content": candidate_message, "question_index": current_idx, "timestamp": now_str})

    # Merge integrity signals
    if integrity_signals:
        signals = dict(interview.integrity_signals or {})
        paste_count = signals.get("paste_count", 0)
        if integrity_signals.get("was_pasted"):
            paste_count += 1
        signals["paste_count"] = paste_count

        timings = signals.get("timings", [])
        if "time_to_answer_seconds" in integrity_signals:
            timings.append(integrity_signals["time_to_answer_seconds"])
        signals["timings"] = timings

        tab_switches = signals.get("tab_switch_count", 0)
        tab_switches += integrity_signals.get("tab_switch_count", 0)
        signals["tab_switch_count"] = tab_switches

        interview.integrity_signals = signals

    # Decide follow-up vs next question
    client = get_async_openai_client()
    current_q = questions[current_idx] if current_idx < len(questions) else None
    idx_before = current_idx  # Track whether we advance in this turn

    follow_up_count = _count_follow_ups(transcript, current_idx)
    word_count = len(candidate_message.split())
    is_minimal_answer = word_count < 5

    if current_q:
        # Check for repetitive / parroted / copy-pasted content first
        is_garbage = _is_low_quality_long_answer(candidate_message, transcript, current_idx)

        if is_garbage:
            # Regardless of word count, flag as irrelevant — do NOT reward garbage
            decision = {"quality": "irrelevant", "follow_up": "NEXT"}
        elif word_count >= 50:
            # Only short-circuit as "detailed" for genuinely unique long answers
            decision = {"quality": "detailed", "follow_up": "NEXT"}
        elif is_minimal_answer:
            # Very short/garbage answers — skip LLM eval, allow at most 1 follow-up
            decision = {"quality": "vague", "follow_up": "NEXT"}
        else:
            decision, eval_pt, eval_ct = await _evaluate_answer(
                client, current_q, candidate_message, candidate.resume_parsed_data
            )
            interview.total_prompt_tokens += eval_pt
            interview.total_completion_tokens += eval_ct
            interview.cost_usd = float(interview.cost_usd) + calculate_cost(LLM_MODEL, eval_pt, eval_ct)

        # For minimal / garbage answers, allow only 1 follow-up instead of MAX_FOLLOW_UPS_PER_QUESTION
        max_follow_ups = 1 if (is_minimal_answer or is_garbage) else MAX_FOLLOW_UPS_PER_QUESTION

        if decision["quality"] != "detailed" and follow_up_count < max_follow_ups:
            if is_garbage:
                ai_response, resp_pt, resp_ct = await _get_interviewer_response(
                    client, job, candidate, questions, transcript,
                    "The candidate's response was repetitive, copy-pasted, or echoed the question back instead of giving a real answer. Briefly and politely let them know their answer didn't address the question and ask them to provide a genuine, specific response. Keep it under 30 words."
                )
            elif is_minimal_answer:
                ai_response, resp_pt, resp_ct = await _get_interviewer_response(
                    client, job, candidate, questions, transcript,
                    "The candidate gave a very brief or unclear answer. Gently encourage them to provide a real answer with specific details. Keep it short and supportive."
                )
            elif decision["quality"] == "irrelevant":
                ai_response, resp_pt, resp_ct = await _get_interviewer_response(
                    client, job, candidate, questions, transcript,
                    f"The candidate's answer was off-topic and did not address the question. Politely redirect them to answer the actual question. Ask this follow-up: {decision['follow_up']}"
                )
            else:
                ai_response, resp_pt, resp_ct = await _get_interviewer_response(
                    client, job, candidate, questions, transcript,
                    f"The candidate's answer was {decision['quality']}. Ask this follow-up: {decision['follow_up']}"
                )
        else:
            # Advance to next question
            current_idx += 1
            interview.current_question_index = current_idx

            # Build a transition instruction that's honest about answer quality
            was_poor = is_garbage or (follow_up_count > 0 and (is_minimal_answer or decision.get("quality") == "irrelevant"))
            if current_idx < len(questions):
                if was_poor:
                    transition = f"The candidate was unable to provide a satisfactory answer. Do not compliment or acknowledge their answer. Simply move on and ask question #{current_idx + 1}: {questions[current_idx]['question']}"
                else:
                    transition = f"Briefly acknowledge the answer and ask question #{current_idx + 1}: {questions[current_idx]['question']}"
                ai_response, resp_pt, resp_ct = await _get_interviewer_response(
                    client, job, candidate, questions, transcript, transition
                )
            else:
                ai_response, resp_pt, resp_ct = await _get_interviewer_response(
                    client, job, candidate, questions, transcript,
                    "This was the last question. Thank the candidate and wrap up the interview."
                )

        # Track response generation tokens
        interview.total_prompt_tokens += resp_pt
        interview.total_completion_tokens += resp_ct
        interview.cost_usd = float(interview.cost_usd) + calculate_cost(LLM_MODEL, resp_pt, resp_ct)
    else:
        ai_response = "Thank you for your time. The interview is now complete."
        current_idx = len(questions)
        interview.current_question_index = current_idx

    # Append AI response to transcript
    transcript.append({"role": "interviewer", "content": ai_response, "question_index": current_idx, "timestamp": datetime.now(timezone.utc).isoformat()})
    interview.transcript = transcript

    # Check completion
    is_complete = current_idx >= len(questions)
    if is_complete:
        interview.status = "completed"
        interview.completed_at = datetime.now(timezone.utc)
        candidate.status = "completed"
        candidate.completed_at = datetime.now(timezone.utc)

    progress = f"{min(current_idx + 1, len(questions))}/{len(questions)}"
    # Only flag is_last_question when we just advanced to it (not on follow-ups)
    advanced = current_idx != idx_before
    is_last_question = advanced and not is_complete and current_idx == len(questions) - 1
    await db.commit()

    # Auto-evaluate in background after completion.
    # Note: this is fire-and-forget. On worker restart the task is lost; move to
    # a durable queue (Celery/ARQ) before scaling beyond a single process.
    if is_complete:
        task = asyncio.create_task(_auto_evaluate_interview(interview.id))
        # Keep a strong reference so the task isn't garbage-collected mid-flight.
        _BACKGROUND_TASKS.add(task)
        task.add_done_callback(_BACKGROUND_TASKS.discard)
        audit(
            "interview.completed",
            interview_id=interview.id,
            candidate_id=candidate.id,
        )

    return ai_response, progress, is_complete, is_last_question


# ---------------------------------------------------------------------------
# LLM helper functions (all async)
# ---------------------------------------------------------------------------

async def _generate_questions(
    client: AsyncOpenAI, resume_data: dict, job_description: str, num_questions: int
) -> tuple[list[dict], int, int]:
    """Generate interview questions via LLM. Returns (questions, prompt_tokens, completion_tokens)."""

    prompt = QUESTION_GENERATION_PROMPT.format(
        num_questions=num_questions,
        resume_data=json.dumps(resume_data, indent=2),
        job_description=job_description,
    )
    response, _model = await llm_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    raw = response.choices[0].message.content or "[]"
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned[cleaned.index("\n") + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    questions = json.loads(cleaned.strip())
    pt = response.usage.prompt_tokens if response.usage else 0
    ct = response.usage.completion_tokens if response.usage else 0
    return questions, pt, ct


async def _evaluate_answer(client: AsyncOpenAI, question: dict, answer: str, resume_data: dict | None) -> tuple[dict, int, int]:
    """Use LLM to decide if the answer needs a follow-up. Returns (decision, prompt_tokens, completion_tokens)."""
    prompt = FOLLOW_UP_DECISION_PROMPT.format(
        question=question["question"],
        answer=answer,
        word_count=len(answer.split()),
        resume_summary=(resume_data or {}).get("summary", "Not available"),
    )
    response, _model = await llm_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    raw = response.choices[0].message.content or '{"quality":"detailed","follow_up":"NEXT"}'
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned[cleaned.index("\n") + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    pt = response.usage.prompt_tokens if response.usage else 0
    ct = response.usage.completion_tokens if response.usage else 0
    return json.loads(cleaned.strip()), pt, ct


async def _get_interviewer_response(
    client: AsyncOpenAI,
    job: JobPosting,
    candidate: Candidate,
    questions: list[dict],
    transcript: list[dict],
    instruction: str,
) -> tuple[str, int, int]:
    """Get the interviewer's next statement from the LLM. Returns (response, prompt_tokens, completion_tokens)."""
    questions_text = "\n".join(
        f"{i+1}. [{q['category']}] {q['question']}" for i, q in enumerate(questions)
    )
    resume_data = candidate.resume_parsed_data or {}
    system_prompt = INTERVIEW_SYSTEM_PROMPT.format(
        job_title=job.title,
        resume_summary=resume_data.get("summary", ""),
        jd_summary=job.description[:500],
        questions=questions_text,
    )

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

    # Sliding window of recent conversation
    recent = transcript[-CONTEXT_WINDOW_MESSAGES:]
    for msg in recent:
        role = "assistant" if msg["role"] == "interviewer" else "user"
        messages.append({"role": role, "content": msg["content"]})

    messages.append({"role": "user", "content": instruction})

    response, _model = await llm_chat_completion(
        messages=messages,
        temperature=0.5,
    )
    pt = response.usage.prompt_tokens if response.usage else 0
    ct = response.usage.completion_tokens if response.usage else 0
    return response.choices[0].message.content or "", pt, ct


def _count_follow_ups(transcript: list[dict], question_index: int) -> int:
    """Count how many interviewer messages exist for the given question_index.

    The first interviewer message for a question is the original ask;
    every subsequent one is a follow-up.
    """
    interviewer_count = sum(
        1 for msg in transcript
        if msg["role"] == "interviewer" and msg.get("question_index") == question_index
    )
    # Subtract 1 for the original question; the rest are follow-ups.
    # For older transcripts without question_index, fall back to 0 so we
    # don't accidentally block all follow-ups.
    return max(0, interviewer_count - 1)


def _is_low_quality_long_answer(
    candidate_message: str,
    transcript: list[dict],
    current_question_index: int,
) -> bool:
    """Detect repetitive, parroted, or copy-pasted long answers that should NOT
    be short-circuited as 'detailed'.

    Checks for:
      1. Internal repetition — the same sentence repeated many times.
      2. Parroting — the answer is mostly the interviewer's question echoed back.
      3. Cross-answer repetition — the answer is nearly identical to a prior response.
    """
    msg_lower = candidate_message.lower().strip()

    # --- 1. Internal repetition ---
    # Split into sentences (rough split on . ? !) and look for duplicates.
    sentences = [s.strip() for s in re.split(r'[.?!]+', msg_lower) if len(s.strip()) > 10]
    if len(sentences) >= 3:
        unique = set(sentences)
        duplicate_ratio = 1 - (len(unique) / len(sentences))
        if duplicate_ratio >= _REPETITION_RATIO_THRESHOLD:
            return True

    # --- 2. Parroting the interviewer's question ---
    # Find the last interviewer message for this question index.
    last_q_text = ""
    for msg in reversed(transcript):
        if msg["role"] == "interviewer" and msg.get("question_index") == current_question_index:
            last_q_text = msg["content"].lower()
            break
    if last_q_text and len(msg_lower.split()) > 5:
        q_words = set(last_q_text.split())
        a_words = candidate_message.lower().split()
        if a_words:
            overlap = sum(1 for w in a_words if w in q_words) / len(a_words)
            if overlap >= _PARROTING_OVERLAP_THRESHOLD:
                return True

    # --- 3. Cross-answer repetition ---
    # Check if this answer is near-identical to any previous candidate message.
    answer_words = set(msg_lower.split())
    if len(answer_words) > 5:
        for msg in transcript:
            if msg["role"] == "candidate" and msg.get("question_index") != current_question_index:
                prev_words = set(msg["content"].lower().split())
                if len(prev_words) > 5:
                    intersection = answer_words & prev_words
                    union = answer_words | prev_words
                    if union and (len(intersection) / len(union)) > 0.7:
                        return True

    return False


# ---------------------------------------------------------------------------
# Cached question generation helpers
# ---------------------------------------------------------------------------

async def _generate_jd_questions(
    client: AsyncOpenAI, job_description: str, num_questions: int
) -> tuple[list[dict], int, int]:
    """Generate JD-based questions (cacheable across candidates)."""
    skill_count = max(1, num_questions - 2)
    prompt = JD_QUESTIONS_PROMPT.format(
        num_questions=num_questions,
        skill_count=skill_count,
        job_description=job_description,
    )
    response, _model = await llm_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    raw = response.choices[0].message.content or "[]"
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned[cleaned.index("\n") + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    questions = json.loads(cleaned.strip())
    pt = response.usage.prompt_tokens if response.usage else 0
    ct = response.usage.completion_tokens if response.usage else 0
    return questions, pt, ct


async def _generate_resume_questions(
    client: AsyncOpenAI, resume_data: dict, job_title: str, num_questions: int
) -> tuple[list[dict], int, int]:
    """Generate personalized resume-verification questions (unique per candidate)."""
    prompt = RESUME_QUESTIONS_PROMPT.format(
        num_questions=num_questions,
        resume_data=json.dumps(resume_data, indent=2),
        job_title=job_title,
    )
    response, _model = await llm_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    raw = response.choices[0].message.content or "[]"
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned[cleaned.index("\n") + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    questions = json.loads(cleaned.strip())
    pt = response.usage.prompt_tokens if response.usage else 0
    ct = response.usage.completion_tokens if response.usage else 0
    return questions, pt, ct


# ---------------------------------------------------------------------------
# Auto-evaluation (background)
# ---------------------------------------------------------------------------

async def _auto_evaluate_interview(interview_id: str) -> None:
    """Run post-interview evaluation in the background using its own DB session."""
    async with async_session_factory() as db:
        try:
            result = await db.execute(
                select(Interview)
                .options(
                    selectinload(Interview.candidate),
                    selectinload(Interview.job_posting),
                )
                .where(Interview.id == interview_id)
            )
            interview = result.scalar_one_or_none()
            if not interview:
                logger.error("Auto-eval: interview %s not found", interview_id)
                return

            from app.services.evaluation_service import evaluate_interview_async
            evaluation = await evaluate_interview_async(db, interview)
            logger.info(
                "Auto-evaluation complete for interview %s — score: %s, recommendation: %s",
                interview_id,
                evaluation.overall_score,
                evaluation.recommendation,
            )

            # Update candidate overall score
            candidate = interview.candidate
            if candidate and evaluation.overall_score:
                candidate.overall_score = evaluation.overall_score
                await db.commit()

        except Exception:
            logger.exception("Auto-evaluation failed for interview %s", interview_id)
