"""Utility functions: OpenAI client init, token tracking, cost calculation."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletion

from src.schemas import CostEntry, TokenUsage

load_dotenv()

# GPT-4.1-mini pricing (USD per 1M tokens)
_PRICING: dict[str, dict[str, float]] = {
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
}

_cost_log: list[CostEntry] = []


def get_openai_client() -> OpenAI:
    """Return an OpenAI client. Raises if key is missing."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Copy .env.example to .env and add your key.")
    return OpenAI(api_key=api_key)


def chat_completion(
    client: OpenAI,
    *,
    messages: list[dict[str, str]],
    model: str = "gpt-4.1-mini",
    temperature: float = 0.3,
    operation: str = "unknown",
) -> str:
    """Send a chat completion request and return the text response.

    Automatically tracks token usage and cost.
    """
    response: ChatCompletion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    content = response.choices[0].message.content or ""

    # Track cost
    if response.usage:
        usage = TokenUsage(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )
        cost = _calculate_cost(model, usage)
        _cost_log.append(CostEntry(operation=operation, model=model, usage=usage, cost_usd=cost))

    return content


def chat_completion_json(
    client: OpenAI,
    *,
    messages: list[dict[str, str]],
    model: str = "gpt-4.1-mini",
    temperature: float = 0.3,
    operation: str = "unknown",
) -> Any:
    """Like chat_completion but parses the response as JSON."""
    raw = chat_completion(
        client,
        messages=messages,
        model=model,
        temperature=temperature,
        operation=operation,
    )
    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.index("\n")
        cleaned = cleaned[first_newline + 1 :]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return json.loads(cleaned.strip())


def _calculate_cost(model: str, usage: TokenUsage) -> float:
    """Calculate USD cost for a single API call."""
    pricing = _PRICING.get(model, _PRICING["gpt-4.1-mini"])
    input_cost = (usage.prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (usage.completion_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


def get_cost_summary() -> dict[str, Any]:
    """Return a summary of all tracked API costs."""
    total = sum(e.cost_usd for e in _cost_log)
    total_prompt = sum(e.usage.prompt_tokens for e in _cost_log)
    total_completion = sum(e.usage.completion_tokens for e in _cost_log)
    return {
        "total_cost_usd": round(total, 4),
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_tokens": total_prompt + total_completion,
        "calls": len(_cost_log),
        "breakdown": [e.model_dump() for e in _cost_log],
    }


def reset_cost_log() -> None:
    """Clear the cost log (useful between test runs)."""
    _cost_log.clear()
