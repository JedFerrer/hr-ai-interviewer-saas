"""Screening eval harness.

Two layers:

1. **Deterministic layer (always runs).** For every fixture, runs
   `compute_skill_match` against the resume + required_skills and asserts
   that recall meets the per-case `min_recall` floor. This guards against
   regressions in the alias map and matching logic — no LLM required, runs
   on every CI build.

2. **Full-LLM layer (opt-in).** Set `RUN_SCREENING_EVAL=1` to run the real
   `score_resume_match` + `decide()` pipeline for each fixture and report
   precision / recall / F1 of the auto_invite decision against the labeled
   `expected_decision`. No assertion threshold yet — this is observability
   so we can track the headline number across changes.

Fixtures live in `backend/tests/fixtures/screening_eval/cases.jsonl`. Each
line is a JSON object with the schema:

    {
      "id": str,
      "job_title": str,
      "job_description": str,
      "required_skills": [str],
      "resume_data": {ResumeData-shaped dict},
      "expected_decision": "auto_invite" | "review",
      "min_recall": float
    }
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.services.skill_matcher import compute_skill_match

FIXTURES_PATH = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "screening_eval"
    / "cases.jsonl"
)


def _load_cases() -> list[dict]:
    with FIXTURES_PATH.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


_CASES = _load_cases()


# -----------------------------------------------------------------------------
# Layer 1: deterministic recall floor (always runs).
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("case", _CASES, ids=[c["id"] for c in _CASES])
def test_deterministic_recall_meets_floor(case: dict) -> None:
    report = compute_skill_match(case["required_skills"], case["resume_data"])
    floor = case["min_recall"]
    assert report.recall >= floor, (
        f"Case {case['id']}: deterministic recall {report.recall:.2f} "
        f"below floor {floor:.2f}. matched={report.matched_skills} "
        f"missing={report.missing_skills}"
    )


# -----------------------------------------------------------------------------
# Layer 2: full LLM screening eval (opt-in via RUN_SCREENING_EVAL=1).
# -----------------------------------------------------------------------------


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


@pytest.mark.skipif(
    not os.getenv("RUN_SCREENING_EVAL"),
    reason="Full-LLM screening eval is opt-in (set RUN_SCREENING_EVAL=1).",
)
@pytest.mark.asyncio
async def test_full_screening_eval_metrics(capsys: pytest.CaptureFixture) -> None:
    """Run the real LLM pipeline and print precision/recall/F1.

    No assertion threshold for v1 — the goal is a printed headline number
    we can watch across releases. Failures from the LLM (timeout, bad JSON)
    surface as case-level errors, not pipeline-level failures.
    """
    from app.services.resume_scoring_service import score_resume_match
    from app.services.screening_service import ScreeningPolicy, decide

    policy = ScreeningPolicy(
        mode="hybrid",
        auto_invite_threshold=75,
        review_threshold=55,
    )

    tp = fp = fn = tn = 0
    rows: list[tuple[str, str, str, int | None, float | None]] = []

    for case in _CASES:
        try:
            match = await score_resume_match(
                resume_data=case["resume_data"],
                job_title=case["job_title"],
                job_description=case["job_description"],
                required_skills=case["required_skills"],
            )
            outcome = decide(
                policy=policy,
                score=match["score"],
                confidence=match["confidence"],
            )
            actual = outcome.decision
            score = match["score"]
            confidence = match["confidence"]
        except Exception as exc:  # noqa: BLE001
            actual = f"error:{type(exc).__name__}"
            score = None
            confidence = None

        expected = case["expected_decision"]
        rows.append((case["id"], expected, actual, score, confidence))

        # Collapse to binary auto_invite vs not for the headline metric.
        pred_pos = actual == "auto_invite"
        true_pos = expected == "auto_invite"
        if pred_pos and true_pos:
            tp += 1
        elif pred_pos and not true_pos:
            fp += 1
        elif not pred_pos and true_pos:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = _f1(precision, recall)

    print("\n=== Screening eval (auto_invite vs not) ===")
    print(f"{'case':<28} {'expected':<12} {'actual':<14} {'score':<6} {'conf':<5}")
    for case_id, expected, actual, score, confidence in rows:
        s = "-" if score is None else str(score)
        c = "-" if confidence is None else f"{confidence:.2f}"
        print(f"{case_id:<28} {expected:<12} {actual:<14} {s:<6} {c:<5}")
    print(
        f"\nTP={tp} FP={fp} FN={fn} TN={tn} | "
        f"precision={precision:.3f} recall={recall:.3f} f1={f1:.3f}"
    )

    # Force capsys output to be visible even on success.
    captured = capsys.readouterr()
    print(captured.out)
