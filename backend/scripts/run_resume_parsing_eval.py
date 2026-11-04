"""Run a live resume parsing + scoring benchmark with expected-vs-actual checks.

This script uses the real LLM pipeline:
1) parse resume text -> structured ResumeData
2) score parsed resume against job description
3) apply screening decision policy
4) compare outputs against expected ranges in fixtures

Fixture file: backend/tests/fixtures/resume_eval/cases.jsonl
Each line is one JSON object. See that file for example schema.
"""

from __future__ import annotations

# Refuse before imports that can connect, write, or expose application data.
import sys as _guard_sys
from pathlib import Path as _GuardPath
_guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
from scripts.owned_workspace import require_owned_workspace, owned_path
_OWNED_ROOT = require_owned_workspace(providers=True, http_target=False)

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Allow `python scripts/run_resume_parsing_eval.py` from backend root.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.services.resume_scoring_service import score_resume_match
from app.services.resume_service import extract_text_from_bytes, parse_resume_with_llm_async
from app.services.screening_service import ScreeningPolicy, decide
from app.services.skill_matcher import normalize_skill


@dataclass
class CaseRunResult:
    case_id: str
    passed: bool
    score: int | None
    confidence: float | None
    expected_score_min: int | None
    expected_score_max: int | None
    expected_decision: str | None
    actual_decision: str | None
    deterministic_recall: float | None
    parse_errors: list[str]
    score_errors: list[str]
    runtime_error: str | None = None


def _load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                cases.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {path} at line {line_number}: {exc}"
                ) from exc
    if not cases:
        raise ValueError(f"No cases found in fixture file: {path}")
    return cases


def _canonical_skill_set(skills: list[str] | None) -> set[str]:
    if not skills:
        return set()
    return {normalize_skill(str(skill)) for skill in skills if str(skill).strip()}


def _tokenize_skill(value: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-z0-9]+", value.lower())
        if token
    }


def _skill_present(expected_skill: str, actual_skills: list[str]) -> bool:
    """Return True when expected skill is represented in parsed skill strings.

    Handles common variants such as "airflow" vs "apache airflow" without
    relying on a huge alias map inside this harness.
    """
    expected_norm = normalize_skill(expected_skill)
    expected_tokens = _tokenize_skill(expected_norm)

    for skill in actual_skills:
        actual_norm = normalize_skill(skill)
        if actual_norm == expected_norm:
            return True

        actual_tokens = _tokenize_skill(actual_norm)
        if expected_tokens and expected_tokens.issubset(actual_tokens):
            return True

    return False


def _resume_text_from_case(case: dict[str, Any]) -> str:
    lines = case.get("resume_lines") or []
    if not isinstance(lines, list):
        raise ValueError(f"Case {case.get('id')} has non-list resume_lines")
    return "\n".join(str(line) for line in lines)


def _resume_text_from_docx(case_id: str, docx_dir: Path) -> str:
    file_path = docx_dir / f"{case_id}.docx"
    if not file_path.exists():
        raise FileNotFoundError(
            f"Missing DOCX resume for case '{case_id}': {file_path}"
        )
    content = file_path.read_bytes()
    return extract_text_from_bytes(content, file_path.name)


def _validate_parse(parsed: dict[str, Any], expected_parse: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    min_years = expected_parse.get("years_experience_min")
    if min_years is not None:
        years = parsed.get("years_experience")
        if years is None or not isinstance(years, int) or years < int(min_years):
            errors.append(
                f"years_experience={years!r} is below expected minimum {min_years}"
            )

    role_fragment = expected_parse.get("current_role_contains")
    if role_fragment:
        current_role = (parsed.get("current_role") or "").lower()
        if str(role_fragment).lower() not in current_role:
            errors.append(
                f"current_role={parsed.get('current_role')!r} does not contain {role_fragment!r}"
            )

    company_fragment = expected_parse.get("current_company_contains")
    if company_fragment:
        current_company = (parsed.get("current_company") or "").lower()
        if str(company_fragment).lower() not in current_company:
            errors.append(
                f"current_company={parsed.get('current_company')!r} does not contain {company_fragment!r}"
            )

    expected_skills = [
        str(skill)
        for skill in (expected_parse.get("skills_should_include") or [])
        if str(skill).strip()
    ]
    actual_skills = [
        str(skill)
        for skill in (parsed.get("skills") or [])
        if str(skill).strip()
    ]
    missing_skills = [
        normalize_skill(skill)
        for skill in expected_skills
        if not _skill_present(skill, actual_skills)
    ]
    if missing_skills:
        errors.append(
            f"parsed skills missing expected skills: {', '.join(missing_skills)}"
        )

    min_experience_count = expected_parse.get("experience_min_count")
    if min_experience_count is not None:
        experience = parsed.get("experience") or []
        count = len(experience) if isinstance(experience, list) else 0
        if count < int(min_experience_count):
            errors.append(
                f"experience entries={count} is below expected minimum {min_experience_count}"
            )

    return errors


def _validate_score_and_decision(
    score_result: dict[str, Any],
    expected: dict[str, Any],
    *,
    actual_decision: str,
) -> list[str]:
    errors: list[str] = []

    score_expect = expected.get("score") or {}
    score_value = score_result.get("score")
    min_score = score_expect.get("min")
    max_score = score_expect.get("max")

    if min_score is not None and score_value < int(min_score):
        errors.append(f"score={score_value} is below expected min={min_score}")
    if max_score is not None and score_value > int(max_score):
        errors.append(f"score={score_value} is above expected max={max_score}")

    expected_decision = expected.get("decision")
    if expected_decision and actual_decision != expected_decision:
        errors.append(
            f"decision={actual_decision!r} does not match expected {expected_decision!r}"
        )

    det_expect = expected.get("deterministic") or {}
    det_actual = score_result.get("deterministic_match") or {}
    det_recall = det_actual.get("recall")

    det_recall_min = det_expect.get("recall_min")
    det_recall_max = det_expect.get("recall_max")
    if det_recall_min is not None and (det_recall is None or det_recall < det_recall_min):
        errors.append(
            f"deterministic recall={det_recall} is below expected min={det_recall_min}"
        )
    if det_recall_max is not None and (det_recall is None or det_recall > det_recall_max):
        errors.append(
            f"deterministic recall={det_recall} is above expected max={det_recall_max}"
        )

    det_matched = _canonical_skill_set(det_actual.get("matched_skills") or [])
    det_missing = _canonical_skill_set(det_actual.get("missing_skills") or [])

    expected_matched = _canonical_skill_set(det_expect.get("matched_should_include") or [])
    if expected_matched and not expected_matched.issubset(det_matched):
        missing_from_matched = sorted(expected_matched - det_matched)
        errors.append(
            "deterministic matched_skills missing expected entries: "
            + ", ".join(missing_from_matched)
        )

    expected_missing = _canonical_skill_set(det_expect.get("missing_should_include") or [])
    if expected_missing and not expected_missing.issubset(det_missing):
        missing_from_missing = sorted(expected_missing - det_missing)
        errors.append(
            "deterministic missing_skills missing expected entries: "
            + ", ".join(missing_from_missing)
        )

    return errors


async def _run_case(
    case: dict[str, Any],
    policy: ScreeningPolicy,
    *,
    use_upload_files: bool,
    docx_dir: Path,
) -> CaseRunResult:
    case_id = str(case.get("id", "unknown-case"))
    expected = case.get("expected") or {}

    try:
        resume_text = (
            _resume_text_from_docx(case_id, docx_dir)
            if use_upload_files
            else _resume_text_from_case(case)
        )

        # `parse_resume_with_llm_async` currently ignores the client parameter
        # and uses llm_chat_completion fallback internally.
        parsed, _parse_pt, _parse_ct = await parse_resume_with_llm_async(
            client=None,  # type: ignore[arg-type]
            resume_text=resume_text,
        )

        parse_errors = _validate_parse(parsed, expected.get("parse") or {})

        score_result = await score_resume_match(
            resume_data=parsed,
            job_title=case["job_title"],
            job_description=case["job_description"],
            required_skills=list(case.get("required_skills") or []),
        )
        outcome = decide(
            policy=policy,
            score=score_result["score"],
            confidence=score_result["confidence"],
        )

        score_errors = _validate_score_and_decision(
            score_result,
            expected,
            actual_decision=outcome.decision,
        )

        passed = not parse_errors and not score_errors
        score_expect = expected.get("score") or {}
        return CaseRunResult(
            case_id=case_id,
            passed=passed,
            score=score_result["score"],
            confidence=score_result["confidence"],
            expected_score_min=score_expect.get("min"),
            expected_score_max=score_expect.get("max"),
            expected_decision=expected.get("decision"),
            actual_decision=outcome.decision,
            deterministic_recall=(score_result.get("deterministic_match") or {}).get("recall"),
            parse_errors=parse_errors,
            score_errors=score_errors,
        )
    except Exception as exc:  # noqa: BLE001
        score_expect = expected.get("score") or {}
        return CaseRunResult(
            case_id=case_id,
            passed=False,
            score=None,
            confidence=None,
            expected_score_min=score_expect.get("min"),
            expected_score_max=score_expect.get("max"),
            expected_decision=expected.get("decision"),
            actual_decision=None,
            deterministic_recall=None,
            parse_errors=[],
            score_errors=[],
            runtime_error=f"{type(exc).__name__}: {exc}",
        )


def _print_summary(results: list[CaseRunResult]) -> None:
    print("\n=== Resume Parsing + Scoring Eval ===")
    print(
        f"{'case':<34} {'score':<7} {'expected':<12} "
        f"{'decision':<24} {'det_rec':<8} {'status':<6}"
    )

    for result in results:
        score = "-" if result.score is None else str(result.score)
        expected_range = (
            "-"
            if result.expected_score_min is None and result.expected_score_max is None
            else f"{result.expected_score_min}-{result.expected_score_max}"
        )
        decision = f"{result.actual_decision or '-'} / {result.expected_decision or '-'}"
        det_recall = "-" if result.deterministic_recall is None else f"{result.deterministic_recall:.2f}"
        status = "PASS" if result.passed else "FAIL"
        print(
            f"{result.case_id:<34} {score:<7} {expected_range:<12} "
            f"{decision:<24} {det_recall:<8} {status:<6}"
        )

    failures = [r for r in results if not r.passed]
    print(f"\nTotal: {len(results)} | Passed: {len(results) - len(failures)} | Failed: {len(failures)}")

    if failures:
        print("\n--- Failure details ---")
        for result in failures:
            print(f"\n[{result.case_id}]")
            if result.runtime_error:
                print(f"runtime_error: {result.runtime_error}")
            for err in result.parse_errors:
                print(f"parse_error: {err}")
            for err in result.score_errors:
                print(f"score_error: {err}")


def _serialize(results: list[CaseRunResult]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for result in results:
        payload.append(
            {
                "case_id": result.case_id,
                "passed": result.passed,
                "score": result.score,
                "confidence": result.confidence,
                "expected_score_min": result.expected_score_min,
                "expected_score_max": result.expected_score_max,
                "expected_decision": result.expected_decision,
                "actual_decision": result.actual_decision,
                "deterministic_recall": result.deterministic_recall,
                "parse_errors": result.parse_errors,
                "score_errors": result.score_errors,
                "runtime_error": result.runtime_error,
            }
        )
    return payload


async def _main_async(args: argparse.Namespace) -> int:
    if args.output:
        owned_path(args.output)  # refusal before provider calls or writes
    fixture_path = Path(args.cases).resolve()
    cases = _load_cases(fixture_path)
    docx_dir = Path(args.docx_dir).resolve()

    policy = ScreeningPolicy(
        mode="hybrid_threshold",
        auto_invite_threshold=args.auto_invite_threshold,
        review_threshold=args.review_threshold,
    )

    results: list[CaseRunResult] = []
    for case in cases:
        result = await _run_case(
            case,
            policy,
            use_upload_files=args.use_upload_files,
            docx_dir=docx_dir,
        )
        results.append(result)

    _print_summary(results)

    if args.output:
        output_path = owned_path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(_serialize(results), indent=2),
            encoding="utf-8",
        )
        print(f"\nWrote detailed results to: {output_path}")

    has_failures = any(not r.passed for r in results)
    return 1 if has_failures else 0


def _parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    default_cases = repo_root / "tests" / "fixtures" / "resume_eval" / "cases.jsonl"
    default_docx_dir = repo_root / "tests" / "fixtures" / "resume_eval" / "docx"

    parser = argparse.ArgumentParser(
        description="Run resume parsing + scoring eval against labeled fixtures.",
    )
    parser.add_argument(
        "--cases",
        default=str(default_cases),
        help="Path to JSONL fixture file.",
    )
    parser.add_argument(
        "--use-upload-files",
        action="store_true",
        help=(
            "Read resume text from DOCX files via extract_text_from_bytes "
            "(tests upload extraction path)."
        ),
    )
    parser.add_argument(
        "--docx-dir",
        default=str(default_docx_dir),
        help="Directory containing <case_id>.docx files.",
    )
    parser.add_argument(
        "--auto-invite-threshold",
        type=int,
        default=75,
        help="Auto-invite threshold for decision comparison.",
    )
    parser.add_argument(
        "--review-threshold",
        type=int,
        default=55,
        help="Review threshold for decision comparison.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional output JSON path for detailed results.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
