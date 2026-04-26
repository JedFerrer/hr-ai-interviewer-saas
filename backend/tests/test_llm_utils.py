"""Unit tests for `strip_code_fences`.

Covers the cases that crashed the previous `text.index('\\n')` implementation
plus the variants we routinely see from DeepSeek, OpenAI, and Anthropic.
"""

from __future__ import annotations

import pytest

from app.services.llm_utils import strip_code_fences


class TestStripCodeFences:
    def test_no_fence_returns_trimmed_text(self) -> None:
        assert strip_code_fences('  {"a": 1}  ') == '{"a": 1}'

    def test_empty_string_returns_empty(self) -> None:
        assert strip_code_fences("") == ""

    def test_multiline_fence_with_json_hint(self) -> None:
        text = '```json\n{"score": 80}\n```'
        assert strip_code_fences(text) == '{"score": 80}'

    def test_multiline_fence_without_language_hint(self) -> None:
        text = '```\n{"score": 80}\n```'
        assert strip_code_fences(text) == '{"score": 80}'

    def test_single_line_fence_does_not_crash(self) -> None:
        # The previous implementation crashed here because it called
        # `text.index('\n')` and there was no newline in the body.
        text = '```{"score": 80}```'
        assert strip_code_fences(text) == '{"score": 80}'

    def test_unclosed_opening_fence(self) -> None:
        text = '```json\n{"score": 80}'
        assert strip_code_fences(text) == '{"score": 80}'

    def test_trailing_whitespace_after_close_fence(self) -> None:
        text = '```json\n{"a": 1}\n```   \n'
        assert strip_code_fences(text) == '{"a": 1}'

    def test_inner_backticks_are_preserved(self) -> None:
        # Backticks inside the body (e.g. inline code in rationale) must
        # not be eaten by the close-fence regex.
        text = '```json\n{"rationale": "uses `pytest`"}\n```'
        assert strip_code_fences(text) == '{"rationale": "uses `pytest`"}'

    def test_only_fences_yields_empty_body(self) -> None:
        assert strip_code_fences("```\n```") == ""

    @pytest.mark.parametrize("lang", ["json", "JSON", "Json", "javascript"])
    def test_various_language_hints(self, lang: str) -> None:
        text = f'```{lang}\n{{"a": 1}}\n```'
        assert strip_code_fences(text) == '{"a": 1}'
