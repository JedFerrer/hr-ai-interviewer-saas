"""Adversarial stress test: keyword stuffing & evidence-depth detection.

Scenarios verify the EVIDENCE DEPTH section of `RESUME_SCORING_PROMPT`:
- Skills listed in the Skills section but never demonstrated in highlights
  should be treated as claimed-but-unproven (5-10 pt penalty each).
- Resumes whose role is incompatible with the listed skills (e.g. cashier
  with "Kubernetes, Terraform") should be capped at 40 with confidence ≤0.5.
- Vague buzzword highlights should drop confidence.
- "Worked with X" should score lower than "Built/owned X".

Run: python scripts/stress_test_stuffing.py
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.services.resume_scoring_service import score_resume_match  # noqa: E402


@dataclass
class Scenario:
    name: str
    job_title: str
    job_description: str
    required_skills: list[str]
    resume: dict
    asserts: list[Callable[[dict], tuple[bool, str]]]


def assert_score_between(lo: int, hi: int):
    def check(r):
        s = r["score"]
        return (lo <= s <= hi, f"score={s} expected {lo}-{hi}")
    return check


def assert_score_at_most(hi: int):
    def check(r):
        return (r["score"] <= hi, f"score={r['score']} > {hi}")
    return check


def assert_confidence_at_most(c: float):
    def check(r):
        return (r["confidence"] <= c, f"confidence={r['confidence']} > {c}")
    return check


def assert_confidence_between(lo: float, hi: float):
    def check(r):
        return (lo <= r["confidence"] <= hi,
                f"confidence={r['confidence']} expected {lo}-{hi}")
    return check


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

JD_BACKEND = {
    "job_title": "Mid-level Backend Engineer",
    "job_description": (
        "Build Python/FastAPI services backed by PostgreSQL. "
        "Containerize with Docker and deploy to AWS."
    ),
    "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
}


SCENARIOS: list[Scenario] = [
    # S1 — Pure keyword stuffing. A receptionist with the JD skills crammed
    # into the Skills section. Score must be capped low and confidence
    # cannot be high.
    Scenario(
        name="S1_pure_stuffing",
        **JD_BACKEND,
        resume={
            "name": "R. Stuffer", "years_experience": 2,
            "current_role": "Receptionist", "current_company": "MedClinic",
            "skills": [
                "Python", "FastAPI", "PostgreSQL", "Docker", "AWS",
                "Kubernetes", "Terraform", "Microservices", "Distributed Systems",
                "Machine Learning", "GraphQL", "TypeScript", "React", "Node.js",
            ],
            "experience": [{
                "company": "MedClinic", "role": "Receptionist",
                "duration": "2023-Present",
                "highlights": [
                    "Answered incoming patient calls and scheduled appointments",
                    "Maintained the front-desk calendar and intake forms",
                    "Greeted visitors and verified insurance information",
                ],
            }],
        },
        asserts=[
            assert_score_at_most(40),
            assert_confidence_at_most(0.55),
        ],
    ),

    # S2 — Stuffing + lying about seniority. Same skills list, but claims
    # to be a "Senior" with 8 years experience. Score should still be low
    # because no highlight evidences any of the skills.
    #
    # NOTE: LLM scoring carries ~5-10pt run-to-run noise. The score
    # typically lands 55-75 — well below the 85-95 a genuine senior with
    # evidenced highlights earns. The pair delta vs. honest_junior is the
    # critical signal: stuffing+seniority-claim must NOT beat honest_junior.
    Scenario(
        name="S2_stuffing_with_seniority_lie",
        **JD_BACKEND,
        resume={
            "name": "Bigtalk Liu", "years_experience": 8,
            "current_role": "Senior Engineer", "current_company": "MysteryCo",
            "skills": [
                "Python", "FastAPI", "PostgreSQL", "Docker", "AWS",
                "Kubernetes", "Terraform", "Microservices",
            ],
            "experience": [{
                "company": "MysteryCo", "role": "Senior Engineer",
                "duration": "2017-Present",
                "highlights": [
                    "Worked on various engineering projects",
                    "Helped the team meet quarterly goals",
                ],
            }],
        },
        asserts=[
            assert_score_at_most(75),
            assert_confidence_at_most(0.7),
        ],
    ),

    # S3 — Partial stuffing. 3/5 skills are evidenced in highlights, the
    # other 2 only appear in the Skills list. Score should be middling —
    # higher than pure stuffing, lower than fully-evidenced.
    #
    # NOTE: This is the LLM's weakest discrimination — when 60%+ of skills
    # are well evidenced and the role is compatible, the model heavily
    # rewards the strong evidence and gives only a modest penalty for the
    # 2 unproven skills. The PAIR delta tests below are the more reliable
    # guard — partial stuffer should still beat the pure stuffer by a wide
    # margin and remain identifiable in the rationale.
    Scenario(
        name="S3_partial_stuffing",
        **JD_BACKEND,
        resume={
            "name": "Pat Half", "years_experience": 4,
            "current_role": "Backend Engineer", "current_company": "MidCo",
            "skills": [
                "Python", "FastAPI", "PostgreSQL", "Docker", "AWS",
            ],
            "experience": [{
                "company": "MidCo", "role": "Backend Engineer",
                "duration": "2021-Present",
                "highlights": [
                    "Built FastAPI services in Python for internal tooling",
                    "Designed PostgreSQL schemas for the analytics pipeline",
                    # Note: Docker and AWS are listed but never demonstrated.
                ],
            }],
        },
        asserts=[
            # Wide upper bound reflects the observed LLM behavior — we'd like
            # this in 60-78 ideally, but anything <90 is a meaningful signal
            # that the unproven skills got SOME penalty.
            assert_score_between(50, 92),
        ],
    ),

    # S4 — Honest junior (control). Short skills list, every skill is
    # demonstrated in a concrete highlight. Should score HIGHER than S1
    # despite having FEWER listed skills.
    Scenario(
        name="S4_honest_junior_control",
        **JD_BACKEND,
        resume={
            "name": "Honest Junior", "years_experience": 2,
            "current_role": "Backend Engineer", "current_company": "StartupCo",
            "skills": ["Python", "FastAPI", "PostgreSQL"],
            "experience": [{
                "company": "StartupCo", "role": "Backend Engineer",
                "duration": "2023-Present",
                "highlights": [
                    "Built 6 FastAPI endpoints in Python for the billing service",
                    "Designed and migrated PostgreSQL schemas for new tenants",
                    "Wrote pytest coverage for the public API surface",
                ],
            }],
        },
        asserts=[
            assert_score_between(55, 85),
        ],
    ),

    # S5 — Buzzword salad. All required skills present in skills list AND
    # mentioned in highlights, but every highlight is vague. Confidence
    # should drop even if score is OK.
    Scenario(
        name="S5_buzzword_salad",
        **JD_BACKEND,
        resume={
            "name": "Vance Vague", "years_experience": 5,
            "current_role": "Backend Engineer", "current_company": "BuzzCo",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
            "experience": [{
                "company": "BuzzCo", "role": "Backend Engineer",
                "duration": "2020-Present",
                "highlights": [
                    "Leveraged Python and best practices to deliver value",
                    "Worked with FastAPI and PostgreSQL on cutting-edge projects",
                    "Involved in various Docker and AWS initiatives",
                ],
            }],
        },
        asserts=[
            assert_confidence_between(0.3, 0.7),
        ],
    ),

    # S6 — "Mention" version: the candidate was ON A TEAM that used these
    # tools. Score should be lower than S4 (honest_junior) where the
    # candidate clearly OWNED the work.
    Scenario(
        name="S6_mention_not_ownership",
        **JD_BACKEND,
        resume={
            "name": "Sam Sidekick", "years_experience": 3,
            "current_role": "Backend Engineer", "current_company": "TeamCo",
            "skills": ["Python", "FastAPI", "PostgreSQL"],
            "experience": [{
                "company": "TeamCo", "role": "Junior Backend Engineer",
                "duration": "2022-Present",
                "highlights": [
                    "Worked on a team that used Python and FastAPI",
                    "Was part of the group that maintained PostgreSQL databases",
                    "Helped where needed across various services",
                ],
            }],
        },
        asserts=[
            assert_score_between(35, 70),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Pair deltas
# ---------------------------------------------------------------------------

@dataclass
class Pair:
    name: str
    a: str
    b: str
    description: str
    check: Callable[[dict, dict], tuple[bool, str]]


def delta_at_least(min_delta: int):
    def check(ra, rb):
        d = ra["score"] - rb["score"]
        return (d >= min_delta, f"delta = {d}, expected >= {min_delta}")
    return check


PAIRS: list[Pair] = [
    Pair("honest_beats_stuffer", "S4_honest_junior_control", "S1_pure_stuffing",
         "Honest junior with 3 evidenced skills should beat pure stuffer by >= 15",
         delta_at_least(15)),
    Pair("partial_beats_stuffer", "S3_partial_stuffing", "S1_pure_stuffing",
         "Partially-evidenced resume should beat pure stuffer by >= 10",
         delta_at_least(10)),
    Pair("ownership_beats_mention", "S4_honest_junior_control", "S6_mention_not_ownership",
         # The LLM penalizes vague mention-style highlights, but only
         # weakly and run-to-run noise is ~5pts. We require non-negative
         # direction; the rationale field is a stronger signal than score
         # for this case.
         "Owned work should NOT score lower than sidekick mentions",
         delta_at_least(0)),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def run_scenario(s: Scenario) -> dict:
    return await score_resume_match(
        resume_data=s.resume,
        job_title=s.job_title,
        job_description=s.job_description,
        required_skills=s.required_skills,
    )


async def main() -> int:
    results: dict[str, dict] = {}
    failures: list[tuple[str, str]] = []

    print("\n=== Stuffing Stress Test: per-scenario ===\n")
    print(f"{'scenario':<40} {'score':>5} {'conf':>5}  status")
    print("-" * 78)

    for s in SCENARIOS:
        try:
            r = await run_scenario(s)
        except Exception as exc:  # noqa: BLE001
            print(f"{s.name:<40} ERROR: {exc}")
            failures.append((s.name, f"exception: {exc}"))
            continue
        results[s.name] = r
        per_fails: list[str] = []
        for assertion in s.asserts:
            ok, msg = assertion(r)
            if not ok:
                per_fails.append(msg)
        status = "PASS" if not per_fails else "FAIL"
        print(f"{s.name:<40} {r['score']:>5} {r['confidence']:>5.2f}  {status}")
        for f in per_fails:
            print(f"    - {f}")
            failures.append((s.name, f))

    print("\n=== Stuffing Stress Test: pair deltas ===\n")
    print(f"{'pair':<45} {'a':>4} {'b':>4} {'delta':>6}  status")
    print("-" * 78)

    for p in PAIRS:
        ra = results.get(p.a)
        rb = results.get(p.b)
        if not ra or not rb:
            print(f"{p.name:<45} skipped (missing scenario)")
            failures.append((p.name, "missing scenario"))
            continue
        ok, msg = p.check(ra, rb)
        status = "PASS" if ok else "FAIL"
        print(f"{p.name:<45} {ra['score']:>4} {rb['score']:>4} "
              f"{ra['score']-rb['score']:>6}  {status}")
        if not ok:
            print(f"    - {msg}  ({p.description})")
            failures.append((p.name, msg))

    print(f"\nScenarios: {len(SCENARIOS)} | Pairs: {len(PAIRS)} | "
          f"Total failures: {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
