"""Question generator: Resume + JD → categorized interview questions via LLM."""

from __future__ import annotations

from openai import OpenAI

from src.prompts import QUESTION_GENERATION_PROMPT
from src.schemas import InterviewQuestion, ResumeData
from src.utils import chat_completion_json


def generate_questions(
    client: OpenAI,
    resume_data: ResumeData,
    job_description: str,
    num_questions: int = 7,
) -> list[InterviewQuestion]:
    """Generate categorized interview questions tailored to the candidate and role.

    Returns a validated list of InterviewQuestion objects.
    """
    prompt = QUESTION_GENERATION_PROMPT.format(
        num_questions=num_questions,
        resume_data=resume_data.model_dump_json(indent=2),
        job_description=job_description,
    )
    data = chat_completion_json(
        client,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        operation="question_generation",
    )
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array of questions, got {type(data).__name__}")

    return [InterviewQuestion.model_validate(q) for q in data]
