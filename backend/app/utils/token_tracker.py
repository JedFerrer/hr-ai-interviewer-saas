"""Token/cost tracking for LLM API calls."""

from __future__ import annotations

from pydantic import BaseModel

# Pricing (USD per 1M tokens)
_PRICING: dict[str, dict[str, float]] = {
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "deepseek-flash": {"input": 0.30, "output": 1.20},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "deepseek-chat": {"input": 0.27, "output": 1.10},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-haiku-3.5": {"input": 0.80, "output": 4.00},
}


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate USD cost for a single API call."""
    pricing = _PRICING.get(model, _PRICING.get("deepseek-chat", {"input": 0.27, "output": 1.10}))
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)
