"""Unit tests for the pure screening decision engine.

These tests exercise `screening_service.decide` exhaustively across the
three modes plus the confidence + missing-score edge cases. The decision
engine has no I/O so the tests need no fixtures or async runtime.
"""

from __future__ import annotations

import pytest

from app.services.screening_service import ScreeningPolicy, decide


def _hybrid(auto: int = 75, review: int = 55) -> ScreeningPolicy:
    return ScreeningPolicy(
        mode="hybrid_threshold",
        auto_invite_threshold=auto,
        review_threshold=review,
    )


class TestAutoAllMode:
    def test_always_invites_regardless_of_score(self) -> None:
        policy = ScreeningPolicy(
            mode="auto_all", auto_invite_threshold=75, review_threshold=55
        )
        assert decide(policy=policy, score=10, confidence=0.9).decision == "auto_invite"
        assert decide(policy=policy, score=99, confidence=0.9).decision == "auto_invite"

    def test_invites_even_with_missing_score(self) -> None:
        policy = ScreeningPolicy(
            mode="auto_all", auto_invite_threshold=75, review_threshold=55
        )
        assert decide(policy=policy, score=None, confidence=None).decision == "auto_invite"


class TestManualAllMode:
    def test_always_routes_to_review(self) -> None:
        policy = ScreeningPolicy(
            mode="manual_all", auto_invite_threshold=75, review_threshold=55
        )
        assert decide(policy=policy, score=99, confidence=0.99).decision == "review"
        assert decide(policy=policy, score=10, confidence=0.99).decision == "review"
        assert decide(policy=policy, score=None, confidence=None).decision == "review"


class TestHybridThresholdMode:
    def test_above_auto_invite_threshold_invites(self) -> None:
        outcome = decide(policy=_hybrid(), score=80, confidence=0.9)
        assert outcome.decision == "auto_invite"

    def test_at_auto_invite_threshold_invites(self) -> None:
        outcome = decide(policy=_hybrid(auto=75), score=75, confidence=0.9)
        assert outcome.decision == "auto_invite"

    def test_in_review_band_routes_to_review(self) -> None:
        outcome = decide(policy=_hybrid(auto=75, review=55), score=60, confidence=0.9)
        assert outcome.decision == "review"

    def test_below_review_threshold_routes_to_review(self) -> None:
        # v1 explicitly disables auto-reject — even very low scores fall
        # back to HR review so a single bad LLM verdict can't burn a candidate.
        outcome = decide(policy=_hybrid(auto=75, review=55), score=20, confidence=0.95)
        assert outcome.decision == "review"

    def test_low_confidence_forces_review_even_when_score_high(self) -> None:
        outcome = decide(policy=_hybrid(), score=95, confidence=0.2)
        assert outcome.decision == "review"
        assert "confidence" in (outcome.reason or "").lower()

    def test_missing_score_forces_review(self) -> None:
        outcome = decide(policy=_hybrid(), score=None, confidence=None)
        assert outcome.decision == "review"

    def test_missing_confidence_forces_review(self) -> None:
        outcome = decide(policy=_hybrid(), score=80, confidence=None)
        assert outcome.decision == "review"


class TestPolicyValidation:
    def test_review_threshold_above_invite_threshold_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            ScreeningPolicy(
                mode="hybrid_threshold",
                auto_invite_threshold=50,
                review_threshold=70,
            )

    def test_thresholds_outside_0_100_are_rejected(self) -> None:
        with pytest.raises(ValueError):
            ScreeningPolicy(
                mode="hybrid_threshold",
                auto_invite_threshold=150,
                review_threshold=50,
            )
        with pytest.raises(ValueError):
            ScreeningPolicy(
                mode="hybrid_threshold",
                auto_invite_threshold=80,
                review_threshold=-1,
            )
