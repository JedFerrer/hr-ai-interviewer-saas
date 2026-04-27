"""Unit tests for `parse_resume_with_llm_async`.

The LLM client is mocked so these tests exercise only the parsing,
fence-stripping, and validation logic — not provider behaviour.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.resume_service import parse_resume_with_llm_async


def _fake_response(content: str, prompt_tokens: int = 100, completion_tokens: int = 50):
    """Build a faux OpenAI ChatCompletion response shaped like the real one."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        ),
    )


@pytest.mark.asyncio
async def test_happy_path_returns_validated_data() -> None:
    payload = {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "years_experience": 5,
        "current_role": "Engineer",
        "current_company": "Analytical Engines Co.",
        "skills": ["Python", "Math"],
        "experience": [
            {
                "company": "AE Co.",
                "role": "Engineer",
                "duration": "2021-Present",
                "highlights": ["Wrote first algorithm"],
            }
        ],
        "education": [
            {"institution": "Cambridge", "degree": "BSc", "year": "1840"}
        ],
        "summary": "Pioneer.",
    }
    response = _fake_response(json.dumps(payload))

    with patch(
        "app.services.llm_client.llm_chat_completion",
        new=AsyncMock(return_value=(response, "deepseek-chat")),
    ):
        data, pt, ct = await parse_resume_with_llm_async(client=None, resume_text="...")  # type: ignore[arg-type]

    assert data["name"] == "Ada Lovelace"
    assert data["years_experience"] == 5
    assert data["current_role"] == "Engineer"
    assert data["experience"][0]["role"] == "Engineer"
    assert data["experience"][0]["highlights"] == ["Wrote first algorithm"]
    assert pt == 100
    assert ct == 50


@pytest.mark.asyncio
async def test_legacy_title_field_maps_to_role() -> None:
    """Older stored payloads use `title` instead of `role`; alias should accept it."""
    payload = {
        "name": "Legacy",
        "experience": [
            {"company": "X", "title": "PM", "duration": "1y"}
        ],
    }
    response = _fake_response(json.dumps(payload))

    with patch(
        "app.services.llm_client.llm_chat_completion",
        new=AsyncMock(return_value=(response, "deepseek-chat")),
    ):
        data, _, _ = await parse_resume_with_llm_async(client=None, resume_text="...")  # type: ignore[arg-type]

    assert data["experience"][0]["role"] == "PM"


@pytest.mark.asyncio
async def test_fenced_response_is_stripped() -> None:
    payload = {"name": "Fenced", "skills": ["Python"]}
    response = _fake_response(f"```json\n{json.dumps(payload)}\n```")

    with patch(
        "app.services.llm_client.llm_chat_completion",
        new=AsyncMock(return_value=(response, "deepseek-chat")),
    ):
        data, _, _ = await parse_resume_with_llm_async(client=None, resume_text="...")  # type: ignore[arg-type]

    assert data["name"] == "Fenced"


@pytest.mark.asyncio
async def test_non_dict_payload_raises_value_error() -> None:
    response = _fake_response('["not", "a", "dict"]')

    with patch(
        "app.services.llm_client.llm_chat_completion",
        new=AsyncMock(return_value=(response, "deepseek-chat")),
    ):
        with pytest.raises(ValueError, match="JSON object"):
            await parse_resume_with_llm_async(client=None, resume_text="...")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_invalid_json_raises() -> None:
    response = _fake_response("totally not json")

    with patch(
        "app.services.llm_client.llm_chat_completion",
        new=AsyncMock(return_value=(response, "deepseek-chat")),
    ):
        with pytest.raises(json.JSONDecodeError):
            await parse_resume_with_llm_async(client=None, resume_text="...")  # type: ignore[arg-type]
