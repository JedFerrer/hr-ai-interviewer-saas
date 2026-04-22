"""Evaluator: Transcript → structured evaluation scores via LLM."""

from __future__ import annotations

import json
from pathlib import Path

from openai import OpenAI

from src.prompts import EVALUATION_PROMPT
from src.schemas import Evaluation
from src.utils import chat_completion_json


def evaluate_interview(
    client: OpenAI,
    transcript_path: str | Path,
) -> Evaluation:
    """Load a transcript JSON and produce a structured evaluation.

    Returns a validated Evaluation object with scores, summary,
    strengths, gaps, red_flags, and recommendation.
    """
    path = Path(transcript_path)
    if not path.exists():
        raise FileNotFoundError(f"Transcript not found: {path}")

    transcript_data = json.loads(path.read_text(encoding="utf-8"))

    # Format transcript for the prompt
    formatted = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in transcript_data["transcript"]
    )

    prompt = EVALUATION_PROMPT.format(
        job_title=transcript_data["job_title"],
        job_description=transcript_data.get("jd_summary", "Not available"),
        resume_summary=transcript_data.get("resume_summary", "Not available"),
        transcript=formatted,
    )

    data = chat_completion_json(
        client,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        operation="evaluation",
    )
    return Evaluation.model_validate(data)


def save_evaluation(evaluation: Evaluation, output_path: str | Path) -> Path:
    """Save evaluation to a JSON file. Returns the file path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(evaluation.model_dump(), indent=2),
        encoding="utf-8",
    )
    return path
