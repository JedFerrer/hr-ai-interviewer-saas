"""Centralized LLM client with multi-provider fallback.

Supports OpenAI, DeepSeek, and Anthropic via the OpenAI-compatible SDK.
On timeout/connection failure, automatically falls back to the next provider.
"""

from __future__ import annotations

import logging

from openai import APITimeoutError, APIConnectionError, AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()

# Default timeout and retry config per-provider attempt
_TIMEOUT = 60.0
_MAX_RETRIES = 2


def _build_client(provider_cfg: dict) -> AsyncOpenAI:
    """Build an AsyncOpenAI client for a single provider config."""
    return AsyncOpenAI(
        api_key=provider_cfg["api_key"],
        base_url=provider_cfg.get("base_url"),
        timeout=_TIMEOUT,
        max_retries=_MAX_RETRIES,
    )


async def llm_chat_completion(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.4,
    **kwargs,
) -> tuple:
    """Call chat completions with automatic provider fallback.

    Returns (response, model_name) where model_name is the model actually used.
    This allows callers to track costs accurately when a fallback fires.
    """
    chain = _settings.get_fallback_chain()

    last_exc: Exception | None = None

    for i, provider_cfg in enumerate(chain):
        provider_model = model or provider_cfg["model"]
        client = _build_client(provider_cfg)

        try:
            response = await client.chat.completions.create(
                model=provider_model,
                messages=messages,
                temperature=temperature,
                **kwargs,
            )
            if i > 0:
                logger.info(
                    "LLM fallback succeeded with provider #%d (model=%s)",
                    i + 1, provider_model,
                )
            return response, provider_model

        except (APITimeoutError, APIConnectionError) as exc:
            last_exc = exc
            remaining = len(chain) - i - 1
            logger.warning(
                "LLM provider failed (model=%s): %s. %d fallback(s) remaining.",
                provider_model, exc, remaining,
            )
            continue

    # All providers exhausted
    raise last_exc  # type: ignore[misc]


def get_async_openai_client() -> AsyncOpenAI:
    """Build client for the primary provider only (no fallback).

    Use llm_chat_completion() instead when fallback is desired.
    Kept for backward-compat in places that need a raw client.
    """
    api_key = _settings.active_llm_api_key
    if not api_key:
        raise RuntimeError(
            f"LLM API key is not configured (provider={_settings.llm_provider}). "
            "Set OPENAI_API_KEY, DEEPSEEK_API_KEY, or ANTHROPIC_API_KEY in .env"
        )
    return AsyncOpenAI(
        api_key=api_key,
        base_url=_settings.active_llm_base_url,
        timeout=_TIMEOUT,
        max_retries=_MAX_RETRIES,
    )
