"""Pure screening decision engine.

Given a job's screening policy + a resume match score, decide whether the
candidate should be auto-invited to interview, queued for HR review, or
flagged as an error.

Kept deliberately free of side effects (no DB, no LLM, no email) so it can
be unit-tested in isolation and reasoned about easily.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ScreeningMode = Literal["auto_all", "hybrid_threshold", "manual_all"]
Decision = Literal["auto_invite", "review", "reject", "error"]


@dataclass(frozen=True)
class ScreeningPolicy:
    mode: ScreeningMode
    auto_invite_threshold: int  # 0-100
    review_threshold: int       # 0-100

    def __post_init__(self) -> None:
        # Defensive validation — Pydantic already enforces this on the API
        # boundary, but the engine is also called from background tasks
        # where a stale/migrated row could carry bad data.
        for name, value in (
            ("auto_invite_threshold", self.auto_invite_threshold),
            ("review_threshold", self.review_threshold),
        ):
            if not 0 <= value <= 100:
                raise ValueError(f"{name} must be between 0 and 100, got {value}")
        if self.review_threshold > self.auto_invite_threshold:
            raise ValueError(
                "review_threshold must be <= auto_invite_threshold "
                f"(got review={self.review_threshold}, auto_invite={self.auto_invite_threshold})"
            )


@dataclass(frozen=True)
class ScreeningOutcome:
    decision: Decision
    reason: str


# When the LLM is shaky on the score we never auto-invite — we always route
# the borderline call to a human under hybrid mode.
_LOW_CONFIDENCE_CUTOFF = 0.4


def decide(
    *,
    policy: ScreeningPolicy,
    score: int | None,
    confidence: float | None,
) -> ScreeningOutcome:
    """Return the routing decision for a freshly scored candidate.

    `score` may be None if the resume could not be scored (e.g. parsing
    succeeded but the scorer LLM failed). In that case we fall back to HR
    review under any non-`auto_all` policy, and `auto_invite` under the
    legacy `auto_all` mode (preserving today's behaviour).
    """
    if policy.mode == "auto_all":
        return ScreeningOutcome(
            decision="auto_invite",
            reason="Job uses auto-invite mode; all parsed applicants get an interview link.",
        )

    if policy.mode == "manual_all":
        return ScreeningOutcome(
            decision="review",
            reason="Job uses manual review mode; awaiting HR approval.",
        )

    # hybrid_threshold from here on.
    if score is None:
        return ScreeningOutcome(
            decision="review",
            reason="Resume could not be scored automatically; routed to HR review.",
        )

    if confidence is None or confidence < _LOW_CONFIDENCE_CUTOFF:
        return ScreeningOutcome(
            decision="review",
            reason=(
                "Score returned with missing or low confidence; routed to HR review."
                if confidence is None
                else (
                    f"Score {score}/100 returned with low confidence "
                    f"({confidence:.2f}); routed to HR review."
                )
            ),
        )

    if score >= policy.auto_invite_threshold:
        return ScreeningOutcome(
            decision="auto_invite",
            reason=(
                f"Score {score}/100 meets auto-invite threshold "
                f"({policy.auto_invite_threshold})."
            ),
        )

    if score < policy.review_threshold:
        # v1 deliberately routes low-score candidates to HR review rather
        # than auto-rejecting (see RESUME_GATE_AND_INVITE_PLAN §13.2).
        return ScreeningOutcome(
            decision="review",
            reason=(
                f"Score {score}/100 below review threshold "
                f"({policy.review_threshold}); needs HR decision."
            ),
        )

    return ScreeningOutcome(
        decision="review",
        reason=(
            f"Score {score}/100 in review band "
            f"[{policy.review_threshold}, {policy.auto_invite_threshold}); "
            "needs HR decision."
        ),
    )
