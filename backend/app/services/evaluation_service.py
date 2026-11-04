"""Evaluation service: generate evaluation from completed interview."""

from __future__ import annotations

import json

from openai import OpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import EvaluationRecord
from app.models.interview import Interview
from app.config import get_settings
from app.services.prompts import EVALUATION_PROMPT
from app.utils.token_tracker import calculate_cost

_settings = get_settings()


def _parse_evaluation_response(raw: str) -> dict:
    """Parse LLM evaluation response, stripping code fences."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned[cleaned.index("\n") + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return json.loads(cleaned.strip())


def _build_evaluation_record(
    interview: Interview, data: dict, pt: int, ct: int, cost: float
) -> EvaluationRecord:
    """Create an EvaluationRecord from parsed LLM data."""
    # Support both nested {"scores": {...}} and flat {"skill_match": ...} formats
    scores = data.get("scores") if isinstance(data.get("scores"), dict) else data
    return EvaluationRecord(
        interview_id=interview.id,
        overall_score=data.get("overall_score"),
        skill_match=scores.get("skill_match"),
        communication=scores.get("communication"),
        problem_solving=scores.get("problem_solving"),
        cultural_fit=scores.get("cultural_fit"),
        summary=data.get("summary"),
        strengths=data.get("strengths", []),
        gaps=data.get("gaps", []),
        red_flags=data.get("red_flags", []),
        recommendation=data.get("recommendation"),
        evaluation_tokens=pt + ct,
        evaluation_cost_usd=cost,
    )


async def evaluate_interview(
    db: AsyncSession,
    client: OpenAI,
    interview: Interview,
) -> EvaluationRecord:
    """Run LLM evaluation on a completed interview transcript (sync client).

    Creates and returns an EvaluationRecord.
    """
    if _settings.portfolio_demo:
        raise ValueError("Synchronous provider operation has no demo adapter")
    candidate = interview.candidate
    job = interview.job_posting
    resume_data = candidate.resume_parsed_data or {}
    transcript = interview.transcript or []

    formatted = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in transcript
    )

    # Format integrity signals for the evaluator
    signals = interview.integrity_signals or {}
    integrity_lines = []
    if signals.get("paste_count", 0) > 0:
        integrity_lines.append(f"- Paste count: {signals['paste_count']} (candidate pasted text {signals['paste_count']} times)")
    if signals.get("tab_switch_count", 0) > 0:
        integrity_lines.append(f"- Tab switches: {signals['tab_switch_count']}")
    timings = signals.get("timings", [])
    if timings:
        avg_time = sum(timings) / len(timings)
        integrity_lines.append(f"- Average response time: {avg_time:.1f} seconds")
    integrity_text = "\n".join(integrity_lines) if integrity_lines else "No integrity concerns detected."

    prompt = EVALUATION_PROMPT.format(
        job_title=job.title,
        job_description=job.description[:1000],
        resume_summary=resume_data.get("summary", "Not available"),
        transcript=formatted,
        integrity_signals=integrity_text,
    )

    llm_model = _settings.active_llm_model
    response = client.chat.completions.create(
        model=llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    raw = response.choices[0].message.content or "{}"
    data = _parse_evaluation_response(raw)

    pt = response.usage.prompt_tokens if response.usage else 0
    ct = response.usage.completion_tokens if response.usage else 0
    cost = calculate_cost(llm_model, pt, ct)

    evaluation = _build_evaluation_record(interview, data, pt, ct, cost)
    db.add(evaluation)

    # Update interview cost totals
    interview.total_prompt_tokens += pt
    interview.total_completion_tokens += ct
    interview.cost_usd = float(interview.cost_usd) + cost

    await db.commit()
    await db.refresh(evaluation)
    return evaluation


async def evaluate_interview_async(
    db: AsyncSession,
    interview: Interview,
) -> EvaluationRecord:
    """Run LLM evaluation using provider fallback (for background tasks).

    Creates and returns an EvaluationRecord.
    """
    from app.services.llm_client import llm_chat_completion

    candidate = interview.candidate
    job = interview.job_posting
    resume_data = candidate.resume_parsed_data or {}
    transcript = interview.transcript or []

    formatted = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in transcript
    )

    # Format integrity signals for the evaluator
    signals = interview.integrity_signals or {}
    integrity_lines = []
    if signals.get("paste_count", 0) > 0:
        integrity_lines.append(f"- Paste count: {signals['paste_count']} (candidate pasted text {signals['paste_count']} times)")
    if signals.get("tab_switch_count", 0) > 0:
        integrity_lines.append(f"- Tab switches: {signals['tab_switch_count']}")
    timings = signals.get("timings", [])
    if timings:
        avg_time = sum(timings) / len(timings)
        integrity_lines.append(f"- Average response time: {avg_time:.1f} seconds")
    integrity_text = "\n".join(integrity_lines) if integrity_lines else "No integrity concerns detected."

    prompt = EVALUATION_PROMPT.format(
        job_title=job.title,
        job_description=job.description[:1000],
        resume_summary=resume_data.get("summary", "Not available"),
        transcript=formatted,
        integrity_signals=integrity_text,
    )

    response, model_used = await llm_chat_completion(
        operation="evaluate", demo_context={},
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    raw = response.choices[0].message.content or "{}"
    data = _parse_evaluation_response(raw)

    pt = response.usage.prompt_tokens if response.usage else 0
    ct = response.usage.completion_tokens if response.usage else 0
    cost = calculate_cost(model_used, pt, ct)

    evaluation = _build_evaluation_record(interview, data, pt, ct, cost)
    db.add(evaluation)

    interview.total_prompt_tokens += pt
    interview.total_completion_tokens += ct
    interview.cost_usd = float(interview.cost_usd) + cost

    await db.commit()
    await db.refresh(evaluation)
    return evaluation
