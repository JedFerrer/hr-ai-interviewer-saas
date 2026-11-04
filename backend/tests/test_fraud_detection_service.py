"""Unit tests for the fraud detection service.

The pure helpers (`normalize_name`, `name_similarity`, `compute_resume_hash`,
`_classify` via `detect_fraud_signals`) need no DB. The hash-collision check
is tested separately with a stub session that records the query.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.services.fraud_detection_service import (
    compute_resume_hash,
    detect_fraud_signals,
    name_similarity,
    normalize_name,
)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestNormalizeName:
    def test_lowercases_and_strips_punctuation(self) -> None:
        assert normalize_name("John A. Smith") == "john smith"

    def test_drops_titles_and_suffixes(self) -> None:
        assert normalize_name("Dr. Jane Doe Jr.") == "jane doe"

    def test_drops_single_letter_initials(self) -> None:
        assert normalize_name("J. R. R. Tolkien") == "tolkien"

    def test_handles_empty(self) -> None:
        assert normalize_name(None) == ""
        assert normalize_name("") == ""
        assert normalize_name("   ") == ""


class TestNameSimilarity:
    def test_identical_names_match(self) -> None:
        assert name_similarity("John Smith", "John Smith") == pytest.approx(1.0)

    def test_initials_vs_full_match(self) -> None:
        # "John A. Smith" vs "John Smith" should be high (initial dropped).
        assert name_similarity("John A. Smith", "John Smith") >= 0.9

    def test_reordered_tokens_match(self) -> None:
        # Token-set Jaccard handles "Last, First" style flips.
        assert name_similarity("Smith John", "John Smith") == pytest.approx(1.0)

    def test_completely_different_names_below_threshold(self) -> None:
        assert name_similarity("Alice Johnson", "Bob Williams") < 0.4

    def test_typo_still_high_via_sequence(self) -> None:
        # SequenceMatcher fallback catches single-character typos.
        assert name_similarity("Jonathan Smith", "Jonathon Smith") >= 0.85

    def test_empty_returns_zero(self) -> None:
        assert name_similarity("", "John Smith") == 0.0
        assert name_similarity("John Smith", None) == 0.0


class TestComputeResumeHash:
    def test_deterministic(self) -> None:
        a = compute_resume_hash(b"hello world")
        b = compute_resume_hash(b"hello world")
        assert a == b
        assert len(a) == 64  # sha256 hex

    def test_different_bytes_differ(self) -> None:
        assert compute_resume_hash(b"abc") != compute_resume_hash(b"abd")


# ---------------------------------------------------------------------------
# detect_fraud_signals — stub the DB layer
# ---------------------------------------------------------------------------


class _StubSession:
    """Async session stub: returns no hash collisions.

    `collisions` is a list of (candidate_id, name, normalized_email) triples
    mirroring the three columns selected by find_resume_hash_collision.
    """

    def __init__(self, collisions: list[tuple[str, str | None, str]] | None = None) -> None:
        self._collisions = collisions or []

    async def execute(self, _stmt):  # noqa: ANN001
        rows = list(self._collisions)

        @dataclass
        class _Result:
            _rows: list

            def all(self):
                return self._rows

        return _Result(rows)


class TestDetectFraudSignals:
    @pytest.mark.asyncio
    async def test_clean_application_no_signals(self) -> None:
        result = await detect_fraud_signals(
            db=_StubSession(),
            candidate_id="c1",
            form_name="John Smith",
            form_email="john@example.com",
            resume_data={"name": "John Smith", "email": "john@example.com"},
            content_hash="h1",
        )
        assert result.risk_level == "none"
        assert result.signals == []

    @pytest.mark.asyncio
    async def test_name_mismatch_alone_is_warn(self) -> None:
        result = await detect_fraud_signals(
            db=_StubSession(),
            candidate_id="c1",
            form_name="Bob Williams",
            form_email="john@example.com",
            resume_data={"name": "John Smith", "email": "john@example.com"},
            content_hash="h1",
        )
        assert result.risk_level == "warn"
        assert {s.kind for s in result.signals} == {"name_mismatch"}

    @pytest.mark.asyncio
    async def test_email_mismatch_alone_is_warn(self) -> None:
        result = await detect_fraud_signals(
            db=_StubSession(),
            candidate_id="c1",
            form_name="John Smith",
            form_email="someone-else@example.com",
            resume_data={"name": "John Smith", "email": "john@example.com"},
            content_hash="h1",
        )
        assert result.risk_level == "warn"
        assert {s.kind for s in result.signals} == {"email_mismatch"}

    @pytest.mark.asyncio
    async def test_name_and_email_mismatch_is_block(self) -> None:
        result = await detect_fraud_signals(
            db=_StubSession(),
            candidate_id="c1",
            form_name="Bob Williams",
            form_email="bob@example.com",
            resume_data={"name": "John Smith", "email": "john@example.com"},
            content_hash="h1",
        )
        assert result.risk_level == "block"
        assert {s.kind for s in result.signals} == {
            "name_mismatch",
            "email_mismatch",
        }

    @pytest.mark.asyncio
    async def test_resume_without_name_skips_name_check(self) -> None:
        result = await detect_fraud_signals(
            db=_StubSession(),
            candidate_id="c1",
            form_name="Bob Williams",
            form_email="bob@example.com",
            resume_data={"email": "bob@example.com"},
            content_hash="h1",
        )
        assert result.risk_level == "none"

    @pytest.mark.asyncio
    async def test_resume_without_email_skips_email_check(self) -> None:
        result = await detect_fraud_signals(
            db=_StubSession(),
            candidate_id="c1",
            form_name="John Smith",
            form_email="anything@example.com",
            resume_data={"name": "John Smith"},
            content_hash="h1",
        )
        assert result.risk_level == "none"

    @pytest.mark.asyncio
    async def test_email_normalization_strips_plus_alias(self) -> None:
        # form: john+job@example.com  vs  resume: john@example.com  -> match
        result = await detect_fraud_signals(
            db=_StubSession(),
            candidate_id="c1",
            form_name="John Smith",
            form_email="john+job123@example.com",
            resume_data={"name": "John Smith", "email": "john@example.com"},
            content_hash="h1",
        )
        assert result.risk_level == "none"

    @pytest.mark.asyncio
    async def test_hash_collision_with_different_email_blocks(self) -> None:
        # Another candidate row already has the same hash under a
        # *different* normalized email.
        stub = _StubSession(collisions=[("other_candidate", "Jane Doe", "someone@else.com")])
        result = await detect_fraud_signals(
            db=stub,
            candidate_id="c1",
            form_name="John Smith",
            form_email="john@example.com",
            resume_data={"name": "John Smith", "email": "john@example.com"},
            content_hash="hash_xyz",
        )
        assert result.risk_level == "block"
        assert any(s.kind == "resume_content_reused" for s in result.signals)
        # Detail should name the colliding person, not expose a UUID.
        collision_signal = next(s for s in result.signals if s.kind == "resume_content_reused")
        assert "Jane Doe" in collision_signal.detail
        assert "other_candidate" not in collision_signal.detail

    @pytest.mark.asyncio
    async def test_hash_collision_same_email_is_ignored(self) -> None:
        # Same person re-applying to a different job: same hash, same email.
        # That's legitimate; do not flag.
        stub = _StubSession(collisions=[("other_candidate", "John Smith", "john@example.com")])
        result = await detect_fraud_signals(
            db=stub,
            candidate_id="c1",
            form_name="John Smith",
            form_email="john@example.com",
            resume_data={"name": "John Smith", "email": "john@example.com"},
            content_hash="hash_xyz",
        )
        assert result.risk_level == "none"

    @pytest.mark.asyncio
    async def test_to_dict_serializes_for_storage(self) -> None:
        result = await detect_fraud_signals(
            db=_StubSession(),
            candidate_id="c1",
            form_name="Bob Williams",
            form_email="bob@example.com",
            resume_data={"name": "John Smith", "email": "john@example.com"},
            content_hash="h1",
        )
        data = result.to_dict()
        assert data["risk_level"] == "block"
        assert isinstance(data["signals"], list)
        assert all("kind" in s and "detail" in s for s in data["signals"])
