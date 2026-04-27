"""Unit tests for `score_resume_match`.

Exercises happy path + every guarded failure mode that the screening
pipeline relies on for routing to the `error` branch.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.resume_scoring_service import score_resume_match


def _fake_response(content: str, prompt_tokens: int = 200, completion_tokens: int = 80):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        ),
    )


_VALID_PAYLOAD = {
    "score": 82,
    "confidence": 0.9,
    "matched_skills": ["Python", "FastAPI"],
    "missing_must_haves": ["AWS"],
    "rationale": "Strong backend match.",
}


@pytest.mark.asyncio
async def test_happy_path_returns_full_result() -> None:
    response = _fake_response(json.dumps(_VALID_PAYLOAD))

    with patch(
        "app.services.resume_scoring_service.llm_chat_completion",
        new=AsyncMock(return_value=(response, "deepseek-chat")),
    ):
        result = await score_resume_match(
            resume_data={"name": "X", "skills": ["Python", "FastAPI"]},
            job_title="Backend Engineer",
            job_description="Build APIs.",
            required_skills=["Python", "FastAPI"],
        )

    assert result["score"] == 82
    assert result["confidence"] == 0.9
    assert result["matched_skills"] == ["Python", "FastAPI"]
    assert result["missing_must_haves"] == ["AWS"]
    assert result["rationale"] == "Strong backend match."
    assert result["prompt_tokens"] == 200
    assert result["completion_tokens"] == 80
    # Phase 2 / Item 8: deterministic match should be populated even though
    # the mocked LLM payload doesn't include it.
    det = result["deterministic_match"]
    assert set(det["matched_skills"]) == {"python", "fastapi"}
    assert det["missing_skills"] == []
    assert det["recall"] == 1.0


@pytest.mark.asyncio
async def test_deterministic_match_populated_even_when_skills_missing() -> None:
    response = _fake_response(json.dumps(_VALID_PAYLOAD))

    with patch(
        "app.services.resume_scoring_service.llm_chat_completion",
        new=AsyncMock(return_value=(response, "deepseek-chat")),
    ):
        result = await score_resume_match(
            resume_data={"name": "X", "skills": []},
            job_title="X",
            job_description="X",
            required_skills=["Kubernetes"],
        )

    det = result["deterministic_match"]
    assert det["matched_skills"] == []
    assert det["missing_skills"] == ["kubernetes"]
    assert det["recall"] == 0.0


@pytest.mark.asyncio
async def test_fenced_response_is_stripped() -> None:
    response = _fake_response(f"```json\n{json.dumps(_VALID_PAYLOAD)}\n```")

    with patch(
        "app.services.resume_scoring_service.llm_chat_completion",
        new=AsyncMock(return_value=(response, "deepseek-chat")),
    ):
        result = await score_resume_match(
            resume_data={},
            job_title="X",
            job_description="X",
            required_skills=[],
        )
    assert result["score"] == 82


@pytest.mark.asyncio
async def test_invalid_json_raises_value_error() -> None:
    response = _fake_response("definitely not json")

    with patch(
        "app.services.resume_scoring_service.llm_chat_completion",
        new=AsyncMock(return_value=(response, "deepseek-chat")),
    ):
        with pytest.raises(ValueError, match="valid JSON"):
            await score_resume_match(
                resume_data={},
                job_title="X",
                job_description="X",
                required_skills=[],
            )


@pytest.mark.asyncio
async def test_non_dict_payload_raises_value_error() -> None:
    response = _fake_response("[1, 2, 3]")

    with patch(
        "app.services.resume_scoring_service.llm_chat_completion",
        new=AsyncMock(return_value=(response, "deepseek-chat")),
    ):
        with pytest.raises(ValueError, match="JSON object"):
            await score_resume_match(
                resume_data={},
                job_title="X",
                job_description="X",
                required_skills=[],
            )


@pytest.mark.asyncio
async def test_score_out_of_range_fails_validation() -> None:
    bad = {**_VALID_PAYLOAD, "score": 150}
    response = _fake_response(json.dumps(bad))

    with patch(
        "app.services.resume_scoring_service.llm_chat_completion",
        new=AsyncMock(return_value=(response, "deepseek-chat")),
    ):
        with pytest.raises(ValueError, match="failed validation"):
            await score_resume_match(
                resume_data={},
                job_title="X",
                job_description="X",
                required_skills=[],
            )


@pytest.mark.asyncio
async def test_confidence_out_of_range_fails_validation() -> None:
    bad = {**_VALID_PAYLOAD, "confidence": 1.5}
    response = _fake_response(json.dumps(bad))

    with patch(
        "app.services.resume_scoring_service.llm_chat_completion",
        new=AsyncMock(return_value=(response, "deepseek-chat")),
    ):
        with pytest.raises(ValueError, match="failed validation"):
            await score_resume_match(
                resume_data={},
                job_title="X",
                job_description="X",
                required_skills=[],
            )
