"""CLI entry point: Evaluate a saved interview transcript.

Usage:
    python run_evaluation.py --transcript output/transcripts/candidate_transcript.json
"""

from __future__ import annotations

from backend.scripts.owned_workspace import require_owned_workspace, owned_path
require_owned_workspace(providers=True)

import argparse
import sys
from pathlib import Path

from src.evaluator import evaluate_interview, save_evaluation
from src.schemas import Recommendation
from src.utils import get_cost_summary, get_openai_client


_RECOMMENDATION_LABELS = {
    Recommendation.STRONG_YES: "STRONG YES ✓✓",
    Recommendation.YES: "YES ✓",
    Recommendation.MAYBE: "MAYBE ~",
    Recommendation.NO: "NO ✗",
    Recommendation.STRONG_NO: "STRONG NO ✗✗",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="AI HR Interviewer — Evaluate Transcript")
    parser.add_argument("--transcript", required=True, help="Path to interview transcript JSON")
    parser.add_argument("--output", default="output/evaluations", help="Output directory for evaluations")
    args = parser.parse_args()
    owned_path(args.output)  # reject output escapes before any provider call

    transcript_path = Path(args.transcript)
    if not transcript_path.exists():
        print(f"Error: Transcript not found: {transcript_path}")
        sys.exit(1)

    # Initialize
    client = get_openai_client()

    # Evaluate
    print("Evaluating interview transcript...")
    evaluation = evaluate_interview(client, transcript_path)

    # Display results
    print(f"\n{'='*60}")
    print("  EVALUATION RESULTS")
    print(f"{'='*60}")
    print(f"  Overall Score:   {evaluation.overall_score}/10")
    print(f"  Skill Match:     {evaluation.scores.skill_match}/10")
    print(f"  Communication:   {evaluation.scores.communication}/10")
    print(f"  Problem Solving: {evaluation.scores.problem_solving}/10")
    print(f"  Cultural Fit:    {evaluation.scores.cultural_fit}/10")
    print(f"{'='*60}")
    print(f"  Recommendation: {_RECOMMENDATION_LABELS.get(evaluation.recommendation, evaluation.recommendation.value)}")
    print(f"{'='*60}")
    print(f"\n  Summary: {evaluation.summary}")
    if evaluation.strengths:
        print("\n  Strengths:")
        for s in evaluation.strengths:
            print(f"    + {s}")
    if evaluation.gaps:
        print("\n  Gaps:")
        for g in evaluation.gaps:
            print(f"    - {g}")
    if evaluation.red_flags:
        print("\n  Red Flags:")
        for r in evaluation.red_flags:
            print(f"    ! {r}")
    print()

    # Save evaluation
    output_dir = owned_path(args.output)
    eval_filename = transcript_path.stem.replace("_transcript", "_evaluation") + ".json"
    eval_path = save_evaluation(evaluation, owned_path(output_dir / eval_filename))
    print(f"Evaluation saved: {eval_path}")

    # Cost summary
    cost = get_cost_summary()
    print(f"\nAPI Cost: ${cost['total_cost_usd']:.4f} ({cost['total_tokens']:,} tokens)")


if __name__ == "__main__":
    main()
