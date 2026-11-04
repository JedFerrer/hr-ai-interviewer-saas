"""Unit tests for the `llm_chat_completion` fallback policy.

The fallback chain is built from `Settings`; we patch it to a deterministic
two-provider chain and intercept `_build_client` so each provider returns a
stub whose `chat.completions.create` either raises or yields a result.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    BadRequestError,
    RateLimitError,
)

from app.services import llm_client


# --- Helpers ----------------------------------------------------------------


def _stub_client(create_side_effect):
    """Build a stub that mimics AsyncOpenAI.chat.completions.create."""
    create = AsyncMock(side_effect=create_side_effect)
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), create


_FAKE_REQUEST = httpx.Request("POST", "https://example.test/v1/chat/completions")


def _api_status_error(status_code: int) -> APIStatusError:
    response = httpx.Response(status_code=status_code, request=_FAKE_REQUEST)
    return APIStatusError(message=f"HTTP {status_code}", response=response, body=None)


def _rate_limit_error() -> RateLimitError:
    response = httpx.Response(status_code=429, request=_FAKE_REQUEST)
    return RateLimitError(message="rate limited", response=response, body=None)


def _bad_request() -> BadRequestError:
    response = httpx.Response(status_code=400, request=_FAKE_REQUEST)
    return BadRequestError(message="bad request", response=response, body=None)


def _connection_error() -> APIConnectionError:
    return APIConnectionError(request=_FAKE_REQUEST)


def _timeout() -> APITimeoutError:
    return APITimeoutError(request=_FAKE_REQUEST)


def _success_response():
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": 1}'))],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
    )


# --- Fixtures ---------------------------------------------------------------


@pytest.fixture
def two_provider_chain():
    """Patch the fallback chain to return two distinct providers."""
    chain = [
        {"name": "deepseek", "api_key": "k1", "model": "deepseek-chat", "base_url": "x"},
        {"name": "openai", "api_key": "k2", "model": "gpt-4.1-mini", "base_url": None},
    ]
    fake_settings = SimpleNamespace(portfolio_demo=False, get_fallback_chain=lambda: chain)
    with patch.object(llm_client, "_settings", fake_settings):
        yield chain


# --- Tests ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_primary_success_no_fallback(two_provider_chain) -> None:
    primary, primary_create = _stub_client([_success_response()])
    fallback, fallback_create = _stub_client([_success_response()])

    with patch.object(llm_client, "_build_client", side_effect=[primary, fallback]):
        response, model = await llm_client.llm_chat_completion(messages=[{"role": "user", "content": "hi"}])

    assert model == "deepseek-chat"
    assert response.choices[0].message.content == '{"ok": 1}'
    primary_create.assert_awaited_once()
    fallback_create.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("first_error", [_timeout(), _connection_error(), _rate_limit_error()])
async def test_retryable_errors_trigger_fallback(two_provider_chain, first_error) -> None:
    primary, _ = _stub_client([first_error])
    fallback, fallback_create = _stub_client([_success_response()])

    with patch.object(llm_client, "_build_client", side_effect=[primary, fallback]):
        _, model = await llm_client.llm_chat_completion(messages=[{"role": "user", "content": "hi"}])

    assert model == "gpt-4.1-mini"
    fallback_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_5xx_status_error_triggers_fallback(two_provider_chain) -> None:
    primary, _ = _stub_client([_api_status_error(503)])
    fallback, fallback_create = _stub_client([_success_response()])

    with patch.object(llm_client, "_build_client", side_effect=[primary, fallback]):
        _, model = await llm_client.llm_chat_completion(messages=[{"role": "user", "content": "hi"}])

    assert model == "gpt-4.1-mini"
    fallback_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_4xx_status_error_does_not_trigger_fallback(two_provider_chain) -> None:
    primary, _ = _stub_client([_api_status_error(404)])
    fallback, fallback_create = _stub_client([_success_response()])

    with patch.object(llm_client, "_build_client", side_effect=[primary, fallback]):
        with pytest.raises(APIStatusError):
            await llm_client.llm_chat_completion(messages=[{"role": "user", "content": "hi"}])

    fallback_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_bad_request_does_not_trigger_fallback(two_provider_chain) -> None:
    primary, _ = _stub_client([_bad_request()])
    fallback, fallback_create = _stub_client([_success_response()])

    with patch.object(llm_client, "_build_client", side_effect=[primary, fallback]):
        with pytest.raises(BadRequestError):
            await llm_client.llm_chat_completion(messages=[{"role": "user", "content": "hi"}])

    fallback_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_all_providers_exhausted_raises_last(two_provider_chain) -> None:
    primary, _ = _stub_client([_timeout()])
    fallback, _ = _stub_client([_rate_limit_error()])

    with patch.object(llm_client, "_build_client", side_effect=[primary, fallback]):
        with pytest.raises(RateLimitError):
            await llm_client.llm_chat_completion(messages=[{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_json_mode_passes_response_format_for_supported_provider(two_provider_chain) -> None:
    primary, primary_create = _stub_client([_success_response()])
    fallback, _ = _stub_client([_success_response()])

    with patch.object(llm_client, "_build_client", side_effect=[primary, fallback]):
        await llm_client.llm_chat_completion(
            messages=[{"role": "user", "content": "hi"}], json_mode=True
        )

    primary_create.assert_awaited_once()
    kwargs = primary_create.await_args.kwargs
    assert kwargs.get("response_format") == {"type": "json_object"}


@pytest.mark.asyncio
async def test_json_mode_skipped_for_anthropic() -> None:
    chain = [
        {"name": "anthropic", "api_key": "k", "model": "claude", "base_url": "x"},
    ]
    fake_settings = SimpleNamespace(portfolio_demo=False, get_fallback_chain=lambda: chain)
    with patch.object(llm_client, "_settings", fake_settings):
        primary, primary_create = _stub_client([_success_response()])
        with patch.object(llm_client, "_build_client", side_effect=[primary]):
            await llm_client.llm_chat_completion(
                messages=[{"role": "user", "content": "hi"}], json_mode=True
            )

    kwargs = primary_create.await_args.kwargs
    assert "response_format" not in kwargs
