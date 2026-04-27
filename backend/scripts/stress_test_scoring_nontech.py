"""Cross-industry stress test for resume scoring.

Covers non-tech professions to catch domain bias in the prompt + skill matcher:
healthcare, finance, marketing, sales, HR, legal, hospitality, education,
trades, and creative. Mirrors the structure of stress_test_scoring.py but
with non-tech jobs and resumes.

Each scenario asserts a single behavior. Pairs verify relative ordering
between competing candidates for the same role.
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


SCENARIOS: list[Scenario] = [
    # ---- HEALTHCARE ----
    Scenario(
        name="rn_strong_fit",
        job_title="Senior Registered Nurse - ICU",
        job_description="Provide direct patient care in a 20-bed ICU. Manage ventilators, run codes, and mentor junior nurses. Active RN license, BLS, ACLS, and EHR (Epic) experience required.",
        required_skills=["RN License", "BLS", "ACLS", "Epic EHR", "Patient Care"],
        resume={
            "name": "Marcia Lin", "years_experience": 10,
            "current_role": "Charge Nurse - ICU", "current_company": "St. Mercy Hospital",
            "skills": ["RN License (active, CA)", "BLS", "ACLS", "PALS", "Epic EHR", "Patient Care", "Ventilator Management"],
            "experience": [{
                "company": "St. Mercy Hospital", "role": "Charge Nurse - ICU", "duration": "2018-Present",
                "highlights": [
                    "Lead 20-bed ICU shift; supervise 6 RNs",
                    "Run code blues; certified BLS and ACLS",
                    "Charted patient care in Epic EHR",
                ],
            }],
        },
        asserts=[
            assert_score_between(80, 100),
            assert_matched_contains("rn license"),
            assert_matched_contains("acls"),
        ],
    ),
    Scenario(
        name="medical_assistant_to_rn_mismatch",
        job_title="Senior Registered Nurse - ICU",
        job_description="Provide direct patient care in a 20-bed ICU. Manage ventilators, run codes, and mentor junior nurses. Active RN license, BLS, ACLS, and EHR (Epic) experience required.",
        required_skills=["RN License", "BLS", "ACLS", "Epic EHR", "Patient Care"],
        resume={
            "name": "Tara Boyd", "years_experience": 6,
            "current_role": "Medical Assistant", "current_company": "QuickCare Clinic",
            "skills": ["MA Certification", "BLS", "Vitals", "Phlebotomy", "Patient Care"],
            "experience": [{
                "company": "QuickCare Clinic", "role": "Medical Assistant", "duration": "2020-Present",
                "highlights": ["Took vitals, drew blood, charted in athenahealth"],
            }],
        },
        asserts=[
            assert_score_between(5, 35),
            assert_missing_contains("rn license"),
            assert_missing_contains("acls"),
        ],
    ),

    # ---- FINANCE / ACCOUNTING ----
    Scenario(
        name="cpa_strong_fit",
        job_title="Senior Accountant",
        job_description="Own monthly close, lead audit prep, and ensure GAAP compliance. CPA preferred. Hands-on with NetSuite or SAP and advanced Excel.",
        required_skills=["CPA", "GAAP", "NetSuite", "Month-end Close", "Excel"],
        resume={
            "name": "Bernard Cho", "years_experience": 8,
            "current_role": "Senior Accountant", "current_company": "BrightLedger",
            "skills": ["CPA (active)", "GAAP", "NetSuite", "Month-end Close", "Excel (advanced)", "Audit Prep"],
            "experience": [{
                "company": "BrightLedger", "role": "Senior Accountant", "duration": "2019-Present",
                "highlights": [
                    "Lead 5-day month-end close in NetSuite",
                    "Owned GAAP-compliant revenue recognition",
                    "Coordinated annual audit with Big 4 firm",
                ],
            }],
        },
        asserts=[
            assert_score_between(80, 100),
            assert_matched_contains("cpa"),
            assert_matched_contains("netsuite"),
        ],
    ),
    Scenario(
        name="bookkeeper_to_senior_accountant_partial",
        job_title="Senior Accountant",
        job_description="Own monthly close, lead audit prep, and ensure GAAP compliance. CPA preferred. Hands-on with NetSuite or SAP and advanced Excel.",
        required_skills=["CPA", "GAAP", "NetSuite", "Month-end Close", "Excel"],
        resume={
            "name": "Lily Hart", "years_experience": 6,
            "current_role": "Senior Bookkeeper", "current_company": "MainStreet Books",
            "skills": ["QuickBooks", "AR/AP", "Bank Reconciliation", "Excel", "Month-end Close"],
            "experience": [{
                "company": "MainStreet Books", "role": "Senior Bookkeeper", "duration": "2020-Present",
                "highlights": ["Closed monthly books in QuickBooks for 30 SMB clients"],
            }],
        },
        asserts=[
            assert_score_between(20, 55),
            assert_missing_contains("cpa"),
            assert_missing_contains("netsuite"),
        ],
    ),

    # ---- MARKETING ----
    Scenario(
        name="digital_marketing_strong_fit",
        job_title="Senior Digital Marketing Manager",
        job_description="Lead paid acquisition across Google Ads and Meta. Own SEO strategy, manage HubSpot lifecycle campaigns, and report on CAC/LTV.",
        required_skills=["Google Ads", "Meta Ads", "SEO", "HubSpot", "Analytics"],
        resume={
            "name": "Ines Moreau", "years_experience": 8,
            "current_role": "Senior Digital Marketing Manager", "current_company": "GrowthMint",
            "skills": ["Google Ads", "Meta Ads", "SEO", "HubSpot", "Google Analytics", "A/B Testing"],
            "experience": [{
                "company": "GrowthMint", "role": "Senior Digital Marketing Manager", "duration": "2019-Present",
                "highlights": [
                    "Scaled Google Ads spend from $50k to $400k/month at flat CAC",
                    "Owned SEO program; organic traffic up 220%",
                    "Built HubSpot lifecycle campaigns driving 18% MQL→SQL",
                ],
            }],
        },
        asserts=[
            assert_score_between(80, 100),
            assert_matched_contains("google ads"),
            assert_matched_contains("hubspot"),
        ],
    ),
    Scenario(
        name="content_writer_to_marketing_mgr_mismatch",
        job_title="Senior Digital Marketing Manager",
        job_description="Lead paid acquisition across Google Ads and Meta. Own SEO strategy, manage HubSpot lifecycle campaigns, and report on CAC/LTV.",
        required_skills=["Google Ads", "Meta Ads", "SEO", "HubSpot", "Analytics"],
        resume={
            "name": "Owen Park", "years_experience": 7,
            "current_role": "Senior Content Writer", "current_company": "Inkwell",
            "skills": ["Copywriting", "SEO Writing", "WordPress", "Editorial"],
            "experience": [{
                "company": "Inkwell", "role": "Senior Content Writer", "duration": "2019-Present",
                "highlights": ["Wrote 200+ long-form articles; basic SEO keyword research"],
            }],
        },
        asserts=[
            assert_score_between(10, 45),
            assert_missing_contains("google ads"),
            assert_missing_contains("hubspot"),
        ],
    ),

    # ---- SALES ----
    Scenario(
        name="ae_strong_fit",
        job_title="Senior Account Executive - Enterprise",
        job_description="Own $1.5M+ enterprise quota, run MEDDIC pipeline, manage Salesforce CRM, and close 6-figure SaaS deals.",
        required_skills=["Enterprise Sales", "MEDDIC", "Salesforce", "Quota Attainment"],
        resume={
            "name": "Daniela Ortiz", "years_experience": 9,
            "current_role": "Senior Enterprise AE", "current_company": "Vendia",
            "skills": ["Enterprise Sales", "MEDDIC", "Salesforce", "Outreach", "Negotiation"],
            "experience": [{
                "company": "Vendia", "role": "Senior Enterprise AE", "duration": "2020-Present",
                "highlights": [
                    "115% of $1.8M quota for 4 consecutive years",
                    "Run MEDDIC qualification on every deal",
                    "Manage 60-account book in Salesforce",
                ],
            }],
        },
        asserts=[
            assert_score_between(80, 100),
            assert_matched_contains("meddic"),
            assert_matched_contains("salesforce"),
        ],
    ),
    Scenario(
        name="bdr_to_senior_ae_mismatch",
        job_title="Senior Account Executive - Enterprise",
        job_description="Own $1.5M+ enterprise quota, run MEDDIC pipeline, manage Salesforce CRM, and close 6-figure SaaS deals.",
        required_skills=["Enterprise Sales", "MEDDIC", "Salesforce", "Quota Attainment"],
        resume={
            "name": "Jaden Rowe", "years_experience": 2,
            "current_role": "Business Development Rep", "current_company": "OpenStack Sales Co",
            "skills": ["Cold Calling", "Outreach", "Salesforce", "Lead Qualification"],
            "experience": [{
                "company": "OpenStack Sales Co", "role": "BDR", "duration": "2024-Present",
                "highlights": ["Booked 12 demos/month via cold outreach"],
            }],
        },
        asserts=[
            assert_score_between(5, 40),
            assert_missing_contains("meddic"),
        ],
    ),

    # ---- HR / RECRUITING ----
    Scenario(
        name="hr_generalist_strong_fit",
        job_title="Senior HR Generalist",
        job_description="Own employee relations, benefits administration, and HRIS (Workday). Drive performance reviews and compliance with FMLA/EEOC.",
        required_skills=["Workday", "FMLA", "EEOC", "Employee Relations", "Benefits Administration"],
        resume={
            "name": "Pamela Reyes", "years_experience": 10,
            "current_role": "Senior HR Generalist", "current_company": "Atlas Manufacturing",
            "skills": ["Workday", "FMLA", "EEOC", "Employee Relations", "Benefits Administration", "PHR"],
            "experience": [{
                "company": "Atlas Manufacturing", "role": "Senior HR Generalist", "duration": "2018-Present",
                "highlights": [
                    "Administered Workday HRIS for 800 employees",
                    "Managed FMLA cases and EEOC compliance",
                    "Owned annual benefits enrollment cycle",
                ],
            }],
        },
        asserts=[
            assert_score_between(80, 100),
            assert_matched_contains("workday"),
        ],
    ),

    # ---- LEGAL ----
    Scenario(
        name="attorney_strong_fit",
        job_title="Senior Corporate Attorney",
        job_description="Lead M&A and commercial contract negotiation. JD required, active state bar, 7+ years BigLaw or in-house experience.",
        required_skills=["JD", "Bar Admission", "M&A", "Commercial Contracts"],
        resume={
            "name": "Henry Wright", "years_experience": 9,
            "current_role": "Senior Corporate Counsel", "current_company": "Vortex Industries",
            "skills": ["JD (Harvard Law 2016)", "NY Bar (active)", "M&A", "Commercial Contracts", "SEC Filings"],
            "experience": [{
                "company": "Vortex Industries", "role": "Senior Corporate Counsel", "duration": "2020-Present",
                "highlights": [
                    "Led 8 M&A transactions totaling $1.2B",
                    "Negotiated commercial contracts with Fortune 500 vendors",
                ],
            }],
        },
        asserts=[
            assert_score_between(80, 100),
            assert_matched_contains("m&a"),
        ],
    ),
    Scenario(
        name="paralegal_to_attorney_mismatch",
        job_title="Senior Corporate Attorney",
        job_description="Lead M&A and commercial contract negotiation. JD required, active state bar, 7+ years BigLaw or in-house experience.",
        required_skills=["JD", "Bar Admission", "M&A", "Commercial Contracts"],
        resume={
            "name": "Sasha Doyle", "years_experience": 8,
            "current_role": "Senior Paralegal", "current_company": "Brentwood LLP",
            "skills": ["Paralegal Certification", "Document Review", "Legal Research", "Westlaw"],
            "experience": [{
                "company": "Brentwood LLP", "role": "Senior Paralegal", "duration": "2018-Present",
                "highlights": ["Supported attorneys on M&A document review"],
            }],
        },
        asserts=[
            assert_score_between(5, 35),
            assert_missing_contains("jd"),
            assert_missing_contains("bar admission"),
        ],
    ),

    # ---- HOSPITALITY ----
    Scenario(
        name="executive_chef_strong_fit",
        job_title="Executive Chef",
        job_description="Run kitchen operations for fine-dining restaurant. Menu development, food cost control, ServSafe certification, and HACCP compliance required.",
        required_skills=["Menu Development", "Food Cost Control", "ServSafe", "HACCP", "Kitchen Management"],
        resume={
            "name": "Matteo Russo", "years_experience": 15,
            "current_role": "Executive Chef", "current_company": "Bella Notte",
            "skills": ["Menu Development", "Food Cost Control", "ServSafe", "HACCP", "Kitchen Management", "Italian Cuisine"],
            "experience": [{
                "company": "Bella Notte", "role": "Executive Chef", "duration": "2018-Present",
                "highlights": [
                    "Developed seasonal tasting menus",
                    "Maintained 28% food cost on $4M annual revenue",
                    "ServSafe and HACCP certified; led kitchen of 15",
                ],
            }],
        },
        asserts=[
            assert_score_between(80, 100),
            assert_matched_contains("servsafe"),
            assert_matched_contains("haccp"),
        ],
    ),

    # ---- EDUCATION ----
    Scenario(
        name="teacher_strong_fit",
        job_title="High School Math Teacher",
        job_description="Teach Algebra II and Calculus to grades 10-12. State teaching license required. Experience with IEP/504 accommodations and Common Core.",
        required_skills=["State Teaching License", "Algebra", "Calculus", "Common Core", "IEP"],
        resume={
            "name": "Greta Olsen", "years_experience": 8,
            "current_role": "Math Teacher", "current_company": "Lincoln High School",
            "skills": ["State Teaching License (CA)", "Algebra", "Calculus", "Common Core", "IEP/504"],
            "experience": [{
                "company": "Lincoln High School", "role": "Math Teacher", "duration": "2018-Present",
                "highlights": [
                    "Taught Algebra II and Calculus to 140 students/year",
                    "Implemented IEP accommodations aligned to Common Core",
                ],
            }],
        },
        asserts=[
            assert_score_between(80, 100),
            assert_matched_contains("calculus"),
        ],
    ),

    # ---- SKILLED TRADES ----
    Scenario(
        name="electrician_strong_fit",
        job_title="Master Electrician - Commercial",
        job_description="Install and maintain commercial electrical systems. Master electrician license required. NEC code knowledge and experience with conduit bending and panel installation.",
        required_skills=["Master Electrician License", "NEC Code", "Conduit Bending", "Panel Installation"],
        resume={
            "name": "Wesley Banks", "years_experience": 14,
            "current_role": "Master Electrician", "current_company": "Volt Industries",
            "skills": ["Master Electrician License", "NEC Code", "Conduit Bending", "Panel Installation", "OSHA 30"],
            "experience": [{
                "company": "Volt Industries", "role": "Master Electrician", "duration": "2016-Present",
                "highlights": [
                    "Lead electrician on 40+ commercial buildouts",
                    "Maintain NEC code compliance on all installs",
                ],
            }],
        },
        asserts=[
            assert_score_between(80, 100),
            assert_matched_contains("nec code"),
        ],
    ),

    # ---- CREATIVE ----
    Scenario(
        name="graphic_designer_strong_fit",
        job_title="Senior Graphic Designer",
        job_description="Design brand assets and marketing collateral. Adobe Creative Suite (Illustrator, Photoshop, InDesign), Figma, and brand systems experience required.",
        required_skills=["Adobe Illustrator", "Photoshop", "InDesign", "Figma", "Brand Systems"],
        resume={
            "name": "Ana Beltran", "years_experience": 9,
            "current_role": "Senior Graphic Designer", "current_company": "Northwind Studio",
            "skills": ["Adobe Illustrator", "Photoshop", "InDesign", "Figma", "Brand Systems", "Typography"],
            "experience": [{
                "company": "Northwind Studio", "role": "Senior Graphic Designer", "duration": "2019-Present",
                "highlights": [
                    "Built brand systems for 12 B2B clients",
                    "Daily work in Illustrator, Photoshop, InDesign, and Figma",
                ],
            }],
        },
        asserts=[
            assert_score_between(80, 100),
            assert_matched_contains("figma"),
        ],
    ),

    # ---- ADJACENCY (NON-TECH) ----
    # QuickBooks (small biz) vs SAP (enterprise) — adjacent in spirit but
    # very different scale. We expect partial credit, not zero.
    Scenario(
        name="quickbooks_for_sap_partial",
        job_title="Senior Accountant",
        job_description="Own monthly close in SAP. GAAP compliance and audit prep.",
        required_skills=["SAP", "GAAP", "Month-end Close"],
        resume={
            "name": "Roy Stein", "years_experience": 7,
            "current_role": "Senior Accountant", "current_company": "Heritage Foods",
            "skills": ["QuickBooks Enterprise", "GAAP", "Month-end Close", "Audit Prep"],
            "experience": [{
                "company": "Heritage Foods", "role": "Senior Accountant", "duration": "2019-Present",
                "highlights": ["Closed monthly books in QuickBooks Enterprise for $50M company"],
            }],
        },
        asserts=[
            assert_score_between(40, 80),
            assert_missing_contains("sap"),
        ],
    ),

    # ---- CROSS-INDUSTRY MISMATCH ----
    Scenario(
        name="chef_to_attorney_extreme_mismatch",
        job_title="Senior Corporate Attorney",
        job_description="Lead M&A and commercial contract negotiation. JD required.",
        required_skills=["JD", "Bar Admission", "M&A"],
        resume={
            "name": "Matteo Russo", "years_experience": 15,
            "current_role": "Executive Chef", "current_company": "Bella Notte",
            "skills": ["Menu Development", "Food Cost Control", "ServSafe"],
            "experience": [{
                "company": "Bella Notte", "role": "Executive Chef", "duration": "2010-Present",
                "highlights": ["Run kitchen of 15"],
            }],
        },
        asserts=[
            assert_score_between(0, 15),
            assert_missing_contains("jd"),
        ],
    ),
]


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
    Pair("rn_vs_medical_assistant", "rn_strong_fit", "medical_assistant_to_rn_mismatch",
         "RN should beat MA by >= 40 for RN role", delta_at_least(40)),
    Pair("cpa_vs_bookkeeper", "cpa_strong_fit", "bookkeeper_to_senior_accountant_partial",
         "CPA should beat bookkeeper by >= 25 for senior accountant role", delta_at_least(25)),
    Pair("marketer_vs_writer", "digital_marketing_strong_fit", "content_writer_to_marketing_mgr_mismatch",
         "Marketing manager should beat content writer by >= 35 for marketing role", delta_at_least(35)),
    Pair("ae_vs_bdr", "ae_strong_fit", "bdr_to_senior_ae_mismatch",
         "Enterprise AE should beat BDR by >= 35 for senior AE role", delta_at_least(35)),
    Pair("attorney_vs_paralegal", "attorney_strong_fit", "paralegal_to_attorney_mismatch",
         "Attorney should beat paralegal by >= 50 for attorney role", delta_at_least(50)),
    Pair("attorney_vs_chef", "attorney_strong_fit", "chef_to_attorney_extreme_mismatch",
         "Attorney should beat chef by >= 70 for attorney role", delta_at_least(70)),
]


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

    print("\n=== Cross-Industry Stress Test: per-scenario ===\n")
    print(f"{'scenario':<46} {'score':>5} {'conf':>5}  {'recall':>6}  status")
    print("-" * 84)

    for s in SCENARIOS:
        try:
            r = await run_scenario(s)
        except Exception as exc:  # noqa: BLE001
            print(f"{s.name:<46} ERROR: {exc}")
            failures.append((s.name, f"exception: {exc}"))
            continue
        results[s.name] = r
        per_fails: list[str] = []
        for assertion in s.asserts:
            ok, msg = assertion(r)
            if not ok:
                per_fails.append(msg)
        status = "PASS" if not per_fails else "FAIL"
        recall = r["deterministic_match"].get("recall", 0)
        print(f"{s.name:<46} {r['score']:>5} {r['confidence']:>5.2f}  {recall:>6.2f}  {status}")
        for f in per_fails:
            print(f"    - {f}")
            failures.append((s.name, f))

    print("\n=== Cross-Industry Stress Test: pair deltas ===\n")
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
