"""Small helpers shared by every LLM caller.

Kept separate from `llm_client` so unit tests can exercise them without
spinning up an `AsyncOpenAI` client or touching settings.
"""

from __future__ import annotations

import re

# Match an optional leading ```<lang> fence and an optional trailing ``` fence,
# capturing the body in between. Tolerant of:
#   * single-line fenced output (the original `text.index("\n")` crashed on this)
#   * an unclosed opening fence
#   * a `json` (or any) language hint
#   * trailing whitespace / blank lines around the fences
_OPEN_FENCE = re.compile(r"^\s*```[a-zA-Z0-9_+-]*\s*\n?", re.MULTILINE)
_CLOSE_FENCE = re.compile(r"\n?\s*```\s*$")


def strip_code_fences(text: str) -> str:
    """Remove markdown ```...``` fences from an LLM response.

    Robust to single-line fences (` ```{...}``` `), missing closing fences,
    and language hints like ` ```json `.

    Returns the inner body trimmed of surrounding whitespace. Returns the
    original text untouched (after stripping) when no fences are present.
    """
    if not text:
        return ""
    body = text.strip()
    body = _OPEN_FENCE.sub("", body, count=1)
    body = _CLOSE_FENCE.sub("", body, count=1)
    return body.strip()
