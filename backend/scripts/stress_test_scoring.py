"""Stress-test resume scoring across diverse domains and adversarial pairs.

Each scenario asserts one specific behavior so a failure isolates a single
rule rather than a bundle of issues. Pairs are scored back-to-back so we can
report the relative delta (which is the user-visible behavior).
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
    # Each assertion takes the result dict and returns (ok, message).
    asserts: list[Callable[[dict], tuple[bool, str]]]


def assert_score_between(lo: int, hi: int):
    def check(r):
        s = r["score"]
        return (lo <= s <= hi, f"score={s} expected {lo}-{hi}")

    return check


def assert_missing_contains(skill: str):
    def check(r):
        miss = [m.lower() for m in r["missing_must_haves"]]
        return (skill.lower() in miss, f"expected '{skill}' in missing_must_haves={miss}")

    return check


def assert_matched_contains(skill: str):
    def check(r):
        matched = [m.lower() for m in r["matched_skills"]]
        return (skill.lower() in matched, f"expected '{skill}' in matched={matched}")

    return check


def assert_confidence_at_least(c: float):
    def check(r):
        return (r["confidence"] >= c, f"confidence={r['confidence']} < {c}")

    return check


def assert_confidence_at_most(c: float):
    def check(r):
        return (r["confidence"] <= c, f"confidence={r['confidence']} > {c}")

    return check


# ---------------------------------------------------------------------------
# Scenario library
# ---------------------------------------------------------------------------

SCENARIOS: list[Scenario] = [
    # 1. Mobile / iOS — strong fit
    Scenario(
        name="ios_strong_fit",
        job_title="Senior iOS Engineer",
        job_description="Build native iOS apps with Swift and SwiftUI. Use Combine for reactive state and integrate REST APIs.",
        required_skills=["Swift", "SwiftUI", "Combine", "REST APIs"],
        resume={
            "name": "Aiko Sato", "years_experience": 7,
            "current_role": "Senior iOS Engineer", "current_company": "Mobiq",
            "skills": ["Swift", "SwiftUI", "Combine", "REST APIs", "XCTest"],
            "experience": [{
                "company": "Mobiq", "role": "Senior iOS Engineer", "duration": "2020-Present",
                "highlights": [
                    "Shipped SwiftUI rewrite of flagship app",
                    "Built Combine pipelines for offline sync",
                    "Integrated REST APIs with codable layer",
                ],
            }],
        },
        asserts=[
            assert_score_between(80, 100),
            assert_matched_contains("swift"),
            assert_matched_contains("swiftui"),
        ],
    ),
    # 2. Android dev applying to iOS — wrong platform, no transfer credit
    Scenario(
        name="android_to_ios_mismatch",
        job_title="Senior iOS Engineer",
        job_description="Build native iOS apps with Swift and SwiftUI. Use Combine for reactive state and integrate REST APIs.",
        required_skills=["Swift", "SwiftUI", "Combine", "REST APIs"],
        resume={
            "name": "Tobi Adekunle", "years_experience": 6,
            "current_role": "Senior Android Engineer", "current_company": "DroidLab",
            "skills": ["Kotlin", "Jetpack Compose", "Coroutines", "REST APIs"],
            "experience": [{
                "company": "DroidLab", "role": "Senior Android Engineer", "duration": "2020-Present",
                "highlights": ["Built Jetpack Compose UI", "Wrote Kotlin coroutines for async work"],
            }],
        },
        asserts=[
            assert_score_between(5, 35),
            assert_missing_contains("swift"),
            assert_missing_contains("swiftui"),
        ],
    ),
    # 3. ML engineer — strong fit
    Scenario(
        name="ml_strong_fit",
        job_title="Senior Machine Learning Engineer",
        job_description="Train deep learning models with PyTorch, deploy via MLflow on AWS SageMaker, manage data with Pandas.",
        required_skills=["Python", "PyTorch", "MLflow", "AWS SageMaker", "Pandas"],
        resume={
            "name": "Diego Alvarez", "years_experience": 8,
            "current_role": "Senior ML Engineer", "current_company": "NeuroFlow",
            "skills": ["Python", "PyTorch", "MLflow", "AWS SageMaker", "Pandas", "NumPy", "Scikit-learn"],
            "experience": [{
                "company": "NeuroFlow", "role": "Senior ML Engineer", "duration": "2019-Present",
                "highlights": [
                    "Trained PyTorch CNN models for vision",
                    "Productionized models via MLflow on AWS SageMaker",
                    "Built Pandas ETL pipelines",
                ],
            }],
        },
        asserts=[
            assert_score_between(80, 100),
            assert_matched_contains("pytorch"),
        ],
    ),
    # 4. Data analyst applying to ML role — adjacent but not full match
    Scenario(
        name="analyst_to_ml_partial",
        job_title="Senior Machine Learning Engineer",
        job_description="Train deep learning models with PyTorch, deploy via MLflow on AWS SageMaker, manage data with Pandas.",
        required_skills=["Python", "PyTorch", "MLflow", "AWS SageMaker", "Pandas"],
        resume={
            "name": "Helen Park", "years_experience": 5,
            "current_role": "Senior Data Analyst", "current_company": "Insightly",
            "skills": ["Python", "Pandas", "SQL", "Tableau", "Scikit-learn"],
            "experience": [{
                "company": "Insightly", "role": "Senior Data Analyst", "duration": "2021-Present",
                "highlights": ["Built Pandas dashboards", "Trained sklearn classifiers for churn"],
            }],
        },
        asserts=[
            assert_score_between(25, 60),
            assert_missing_contains("pytorch"),
            assert_missing_contains("mlflow"),
        ],
    ),
    # 5. Security — strong fit
    Scenario(
        name="security_strong_fit",
        job_title="Senior Application Security Engineer",
        job_description="Threat-model web apps, review code for OWASP issues, run Burp Suite assessments, automate scanning with Snyk.",
        required_skills=["OWASP", "Burp Suite", "Snyk", "Threat Modeling"],
        resume={
            "name": "Mira Iyer", "years_experience": 9,
            "current_role": "Senior AppSec Engineer", "current_company": "Lockwave",
            "skills": ["OWASP Top 10", "Burp Suite", "Snyk", "Threat Modeling", "Python"],
            "experience": [{
                "company": "Lockwave", "role": "Senior AppSec Engineer", "duration": "2018-Present",
                "highlights": [
                    "Led OWASP-aligned secure code reviews",
                    "Ran Burp Suite Pro assessments on 40+ apps",
                    "Automated Snyk into CI for 80 repos",
                    "Drove threat modeling for new features",
                ],
            }],
        },
        asserts=[assert_score_between(80, 100), assert_matched_contains("burp suite")],
    ),
    # 6. QA engineer — strong fit
    Scenario(
        name="qa_strong_fit",
        job_title="Senior QA Automation Engineer",
        job_description="Write end-to-end tests with Cypress and Playwright. Build CI/CD test pipelines and report defects.",
        required_skills=["Cypress", "Playwright", "CI/CD"],
        resume={
            "name": "Tomas Ruiz", "years_experience": 6,
            "current_role": "Senior QA Automation Engineer", "current_company": "Testify",
            "skills": ["Cypress", "Playwright", "GitHub Actions", "JavaScript"],
            "experience": [{
                "company": "Testify", "role": "Senior QA Automation Engineer", "duration": "2020-Present",
                "highlights": [
                    "Built Cypress + Playwright suites covering 1200 flows",
                    "Owned CI/CD test pipelines on GitHub Actions",
                ],
            }],
        },
        asserts=[assert_score_between(75, 100)],
    ),
    # 7. UX designer applying to frontend engineer — should be heavily penalized
    Scenario(
        name="designer_to_frontend_mismatch",
        job_title="Senior Frontend Engineer",
        job_description="Build production React/Next.js apps with TypeScript and ship to millions of users.",
        required_skills=["React", "Next.js", "TypeScript"],
        resume={
            "name": "Olive Tran", "years_experience": 8,
            "current_role": "Senior UX Designer", "current_company": "Pixelhaus",
            "skills": ["Figma", "Sketch", "User Research", "Wireframing", "Design Systems"],
            "experience": [{
                "company": "Pixelhaus", "role": "Senior UX Designer", "duration": "2018-Present",
                "highlights": ["Led design system for B2B SaaS", "Ran 50+ usability studies"],
            }],
        },
        asserts=[
            assert_score_between(0, 25),
            assert_missing_contains("react"),
            assert_missing_contains("typescript"),
        ],
    ),
    # 8. PM applying to senior engineering role — heavy penalty
    Scenario(
        name="pm_to_engineer_mismatch",
        job_title="Staff Backend Engineer",
        job_description="Lead architecture for distributed Python services on AWS.",
        required_skills=["Python", "AWS", "System Design"],
        resume={
            "name": "Ravi Kapoor", "years_experience": 10,
            "current_role": "Senior Product Manager", "current_company": "MarketMint",
            "skills": ["Roadmapping", "JIRA", "Stakeholder Management", "SQL"],
            "experience": [{
                "company": "MarketMint", "role": "Senior PM", "duration": "2017-Present",
                "highlights": ["Owned product roadmap for B2B platform"],
            }],
        },
        asserts=[
            assert_score_between(0, 30),
            assert_missing_contains("python"),
        ],
    ),
    # 9. Adjacency test — true adjacent (Postgres present, MySQL required)
    Scenario(
        name="adjacent_postgres_for_mysql",
        job_title="Backend Engineer",
        job_description="Build Python services backed by MySQL.",
        required_skills=["Python", "MySQL"],
        resume={
            "name": "Anika Roy", "years_experience": 5,
            "current_role": "Backend Engineer", "current_company": "DataBay",
            "skills": ["Python", "PostgreSQL", "Django"],
            "experience": [{
                "company": "DataBay", "role": "Backend Engineer", "duration": "2021-Present",
                "highlights": ["Built Django apps backed by PostgreSQL"],
            }],
        },
        # MySQL missing but Postgres adjacent → softer penalty (~4-6 pts off perfect)
        asserts=[
            assert_score_between(60, 88),
            assert_missing_contains("mysql"),
        ],
    ),
    # 10. Non-adjacent test — different DB family (Mongo present, PostgreSQL required)
    Scenario(
        name="non_adjacent_mongo_for_postgres",
        job_title="Backend Engineer",
        job_description="Build Python services backed by PostgreSQL with strict relational schemas.",
        required_skills=["Python", "PostgreSQL"],
        resume={
            "name": "Bryce Loomis", "years_experience": 5,
            "current_role": "Backend Engineer", "current_company": "DocuStore",
            "skills": ["Python", "MongoDB", "FastAPI"],
            "experience": [{
                "company": "DocuStore", "role": "Backend Engineer", "duration": "2021-Present",
                "highlights": ["Built FastAPI services backed by MongoDB document store"],
            }],
        },
        # Per our rule, SQL vs Mongo is NOT adjacent → full penalty
        asserts=[
            assert_score_between(40, 75),
            assert_missing_contains("postgresql"),
        ],
    ),
    # 11. Sparse resume — confidence should drop
    Scenario(
        name="sparse_resume_low_confidence",
        job_title="Backend Engineer",
        job_description="Build Python services on AWS.",
        required_skills=["Python", "AWS"],
        resume={
            "name": "Sam Vu", "years_experience": 0,
            "current_role": "", "current_company": "",
            "skills": ["Python"],
            "experience": [],
        },
        asserts=[
            assert_confidence_at_most(0.6),
        ],
    ),
    # 12. Conflicting evidence — claims senior but 1 year experience
    Scenario(
        name="senior_title_low_experience",
        job_title="Senior Backend Engineer",
        job_description="Lead backend architecture in Python and PostgreSQL on AWS.",
        required_skills=["Python", "PostgreSQL", "AWS"],
        resume={
            "name": "Quinn Daly", "years_experience": 1,
            "current_role": "Senior Backend Engineer",  # Self-titled
            "current_company": "OneDevShop",
            "skills": ["Python", "PostgreSQL", "AWS"],
            "experience": [{
                "company": "OneDevShop", "role": "Senior Backend Engineer", "duration": "2025-Present",
                "highlights": ["Built side projects in Python"],
            }],
        },
        # Senior title but 1y exp → should be capped at 50 per seniority rule
        asserts=[
            assert_score_between(15, 55),
        ],
    ),
    # 13. Acronym-only resume (DevOps): uses k8s, k8 not Kubernetes
    Scenario(
        name="acronym_only_devops",
        job_title="Senior SRE",
        job_description="Operate Kubernetes clusters with Terraform on AWS. Strong observability culture.",
        required_skills=["Kubernetes", "Terraform", "AWS"],
        resume={
            "name": "Yuki Tanaka", "years_experience": 7,
            "current_role": "Senior SRE", "current_company": "Cloudly",
            "skills": ["k8s", "TF", "AWS", "Datadog"],
            "experience": [{
                "company": "Cloudly", "role": "Senior SRE", "duration": "2019-Present",
                "highlights": ["Run k8s across 4 regions", "Wrote TF for VPC + EKS"],
            }],
        },
        asserts=[
            # Kubernetes alias should resolve; "TF" is uncommon — may or may not
            assert_score_between(55, 100),
            assert_matched_contains("kubernetes"),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Pair tests — assert relative behavior between two scenarios
# ---------------------------------------------------------------------------

@dataclass
class Pair:
    name: str
    a: str  # scenario name
    b: str
    description: str
    check: Callable[[dict, dict], tuple[bool, str]]


def delta_at_least(min_delta: int):
    def check(ra, rb):
        d = ra["score"] - rb["score"]
        return (d >= min_delta, f"delta = {d}, expected >= {min_delta}")

    return check


PAIRS: list[Pair] = [
    Pair("ios_vs_android", "ios_strong_fit", "android_to_ios_mismatch",
         "iOS specialist should beat Android specialist by >= 30 for iOS role",
         delta_at_least(30)),
    Pair("ml_vs_analyst", "ml_strong_fit", "analyst_to_ml_partial",
         "ML engineer should beat analyst by >= 20 for ML role",
         delta_at_least(20)),
    Pair("frontend_engineer_vs_designer", "ios_strong_fit", "designer_to_frontend_mismatch",
         "Engineer should beat designer by >= 50 for engineering role",
         delta_at_least(50)),
    Pair("adjacent_softer_than_non_adjacent",
         "adjacent_postgres_for_mysql", "non_adjacent_mongo_for_postgres",
         "Adjacent DB substitution should score >= 5 higher than non-adjacent",
         delta_at_least(5)),
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

    print("\n=== Stress Test: per-scenario ===\n")
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

    print("\n=== Stress Test: pair deltas ===\n")
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
        print(f"{p.name:<45} {ra['score']:>4} {rb['score']:>4} {ra['score']-rb['score']:>6}  {status}")
        if not ok:
            print(f"    - {msg}  ({p.description})")
            failures.append((p.name, msg))

    print(f"\nScenarios: {len(SCENARIOS)} | Pairs: {len(PAIRS)} | "
          f"Total failures: {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
