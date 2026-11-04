"""Historical HTTP interview stress harness.

Disabled: retained as source for ownership/refusal regression checks only.
Execution refuses before reading environment files, connecting or producing reports.
Use the deterministic portfolio verifier for supported local acceptance.
"""

from __future__ import annotations

# Refuse before imports that can connect, write, or expose application data.
import sys as _guard_sys
from pathlib import Path as _GuardPath
_guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
from scripts.owned_workspace import require_owned_workspace, owned_path
_OWNED_ROOT = require_owned_workspace(providers=True, http_target=True)

import argparse
import asyncio
import io
import json
import logging
import os
import secrets
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from docx import Document as DocxDocument

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = owned_path(_OWNED_ROOT / "stress_reports")
REPORTS_DIR.mkdir(exist_ok=True)

# Load backend/.env so DEEPSEEK_API_KEY is available to the harness too.
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(ROOT / ".env")
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("stress")

# ---------------------------------------------------------------------------
# LLM-backed candidate answer generator
# ---------------------------------------------------------------------------
# Calls DeepSeek directly to produce realistic, on-topic answers for the
# "ideal" behavior. Without this, the evaluator (correctly) flags scripted
# answers as strong_no, so we can never validate the happy path.

_DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


async def llm_candidate_answer(
    *,
    http: httpx.AsyncClient,
    question: str,
    resume: dict,
    job_title: str,
    style: str = "ideal",
) -> str:
    """Generate a realistic candidate answer to the interviewer's question.

    `style="ideal"`  → strong, on-topic answer grounded in the resume.
    `style="vague"`  → short, low-substance answer that plausibly tries.
    Falls back to a templated answer if the API call fails.
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return _fallback_answer(question, resume, style)

    bullets: list[str] = []
    for exp in resume.get("experience", []):
        bullets.extend(exp[2] if isinstance(exp, tuple) else exp.get("highlights", []))

    if style == "ideal":
        system = (
            "You are role-playing as a strong job candidate in a live interview. "
            "Answer the interviewer's question CONCRETELY and DIRECTLY in 3-5 sentences. "
            "Use specific examples drawn from the candidate's resume bullets when relevant. "
            "Mention numbers, technologies, and trade-offs. Do NOT repeat the question back. "
            "Do NOT use generic filler like 'great question'. Sound like a real engineer."
        )
    else:  # vague
        system = (
            "You are role-playing as an under-prepared candidate. Give a short, "
            "non-specific answer in 1-2 sentences that doesn't really address the "
            "question. No numbers, no specific technologies. Sound uncertain."
        )

    user = (
        f"Job: {job_title}\n"
        f"Candidate background: {resume.get('headline', 'experienced engineer')}\n"
        f"Resume highlights:\n- " + "\n- ".join(bullets[:8]) + "\n\n"
        f"Interviewer question: {question}\n\n"
        f"Your answer (no preamble, just the answer):"
    )

    try:
        r = await http.post(
            _DEEPSEEK_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.7 if style == "ideal" else 0.9,
                "max_tokens": 280,
            },
            timeout=30.0,
        )
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.warning("LLM answer failed (%s) — falling back to template", e)
        return _fallback_answer(question, resume, style)


def _fallback_answer(question: str, resume: dict, style: str) -> str:
    bullets: list[str] = []
    for exp in resume.get("experience", []):
        bullets.extend(exp[2] if isinstance(exp, tuple) else [])
    bullet = bullets[0] if bullets else "led a similar initiative end-to-end"
    if style == "vague":
        return "Yeah, I've done some of that. It generally went fine."
    return (
        f"Concretely: {bullet} The key trade-off was operational risk vs delivery "
        f"speed; we picked the simpler design and validated it with shadow traffic "
        f"before cutover. Happy to dig deeper into the metrics."
    )


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


JOBS: list[dict] = [
    {
        "key": "fullstack_hybrid_default",
        "title": "Senior Full-Stack Engineer",
        "description": (
            "We are hiring a Senior Full-Stack Engineer to design and build "
            "scalable web applications. You will own features end-to-end using "
            "React on the frontend and Node.js with PostgreSQL on the backend. "
            "5+ years of professional experience required. Strong TypeScript "
            "skills and experience deploying to AWS are expected."
        ),
        "required_skills": ["React", "TypeScript", "Node.js", "PostgreSQL", "AWS"],
        "screening_mode": "hybrid_threshold",
        "auto_invite_threshold": 75,
        "review_threshold": 55,
    },
    {
        "key": "ml_hybrid_strict",
        "title": "Machine Learning Engineer",
        "description": (
            "Build and ship production ML systems. You will train models with "
            "PyTorch, design feature pipelines in Python, and operate them with "
            "MLOps tooling. Deep experience with SQL data work and Docker for "
            "reproducible training is required. PhD or equivalent applied "
            "research experience preferred."
        ),
        "required_skills": ["Python", "PyTorch", "MLOps", "SQL", "Docker"],
        "screening_mode": "hybrid_threshold",
        "auto_invite_threshold": 90,
        "review_threshold": 80,
    },
    {
        "key": "devops_auto_all",
        "title": "DevOps Engineer",
        "description": (
            "Own our cloud infrastructure: build CI/CD pipelines, run Kubernetes "
            "clusters in production, and codify everything with Terraform. "
            "Comfort on call. Strong Docker and AWS or GCP experience required."
        ),
        "required_skills": ["Kubernetes", "Docker", "Terraform", "AWS", "CI/CD"],
        "screening_mode": "auto_all",
        "auto_invite_threshold": 75,
        "review_threshold": 55,
    },
    {
        "key": "designer_manual_all",
        "title": "Senior Product Designer",
        "description": (
            "Lead end-to-end product design for a B2B SaaS product. You will "
            "drive UX research, build prototypes in Figma, and contribute to our "
            "design system. Portfolio with shipped, measurable work required."
        ),
        "required_skills": ["Figma", "UX Research", "Prototyping", "Design Systems"],
        "screening_mode": "manual_all",
        "auto_invite_threshold": 75,
        "review_threshold": 55,
    },
    {
        "key": "frontend_hybrid_loose",
        "title": "Frontend Developer (React)",
        "description": (
            "Build accessible, responsive UIs with React and TypeScript. You "
            "will partner with design and product to ship features weekly. "
            "Experience with state management and modern build tooling expected."
        ),
        "required_skills": ["React", "TypeScript", "CSS", "Accessibility"],
        "screening_mode": "hybrid_threshold",
        "auto_invite_threshold": 60,
        "review_threshold": 40,
    },
]


RESUMES: list[dict] = [
    {
        "key": "strong_fullstack",
        "name": "Alex Rivera",
        "headline": "Senior Full-Stack Engineer · 7 years",
        "skills": [
            "React", "TypeScript", "Node.js", "PostgreSQL", "AWS",
            "Docker", "Redis", "GraphQL",
        ],
        "experience": [
            ("Stripe-style Fintech (2021-Present)", "Senior Full-Stack Engineer", [
                "Led migration of monolith to React + Node microservices on AWS ECS.",
                "Designed PostgreSQL schemas for 50M+ row ledger tables with sub-100ms p95.",
                "Owned TypeScript codegen pipeline shared by 30 engineers.",
            ]),
            ("HealthTech Co (2018-2021)", "Full-Stack Engineer", [
                "Built React + Node patient portal serving 200K MAU.",
                "Migrated jobs to AWS Lambda + SQS for elastic scaling.",
            ]),
        ],
        "education": "BS Computer Science, UC Berkeley",
    },
    {
        "key": "partial_fullstack_ml_leaning",
        "name": "Priya Natarajan",
        "headline": "ML Engineer transitioning to Full-Stack · 4 years",
        "skills": [
            "Python", "PyTorch", "MLOps", "Docker", "SQL",
            "FastAPI", "React (basics)",
        ],
        "experience": [
            ("AI Research Lab (2022-Present)", "ML Engineer", [
                "Trained vision transformers in PyTorch, deployed via Docker on Kubernetes.",
                "Built feature pipelines in Python and SQL over 10TB datasets.",
                "Owned MLOps tooling: experiment tracking, model registry, canary rollout.",
            ]),
            ("Edtech Startup (2020-2022)", "Backend Engineer", [
                "FastAPI microservices on PostgreSQL.",
                "Light React work for internal admin tools.",
            ]),
        ],
        "education": "MS Machine Learning, Carnegie Mellon",
    },
    {
        "key": "off_domain_designer",
        "name": "Jordan Kim",
        "headline": "Senior Product Designer · 8 years",
        "skills": [
            "Figma", "UX Research", "Prototyping", "Design Systems",
            "User Interviews", "Wireframing", "Accessibility",
        ],
        "experience": [
            ("Consumer SaaS Co (2020-Present)", "Senior Product Designer", [
                "Led redesign of onboarding flow, +18% activation.",
                "Built and maintained the company-wide Figma design system.",
                "Ran weekly UX research sessions and generative interviews.",
            ]),
            ("Agency (2016-2020)", "Product Designer", [
                "Shipped 12 client products end-to-end.",
            ]),
        ],
        "education": "BFA Interaction Design, RISD",
    },
    {
        "key": "junior_frontend",
        "name": "Sam Patel",
        "headline": "Junior Frontend Developer · 1.5 years",
        "skills": [
            "React", "TypeScript", "CSS", "HTML", "Accessibility (basics)",
            "Jest",
        ],
        "experience": [
            ("Local Agency (2024-Present)", "Junior Frontend Developer", [
                "Built marketing pages with React and TypeScript.",
                "Pair-programmed accessibility fixes across the design system.",
            ]),
            ("Bootcamp Capstone (2023)", "Student", [
                "Built a small e-commerce demo with React + Stripe.",
            ]),
        ],
        "education": "Bootcamp graduate, 2023",
    },
]


# Behavior profile → list of (answer-template) functions.
# Each turn picks an answer based on the profile.
#
# IMPORTANT: _ideal_answer must vary per turn. The evaluator prompt explicitly
# penalises repeated answers ("Repeating the same answer across different
# questions indicates the candidate is not genuinely engaging") so a static
# template scores strong_no even with a perfect resume.
_ideal_turn_counter: dict[int, int] = {}


def _resume_bullets(resume: dict) -> list[str]:
    bullets: list[str] = []
    for _company, _role, items in resume.get("experience", []):
        bullets.extend(items)
    return bullets or ["led a similar initiative end-to-end"]


def _question_keywords(question: str) -> str:
    """Extract a short topical phrase from the interviewer's question."""
    q = (question or "").strip().rstrip("?.!")
    # Take the last clause (usually the actual ask), keep it short.
    tail = q.split(".")[-1].strip() or q
    if len(tail) > 140:
        tail = tail[:140].rsplit(" ", 1)[0]
    return tail


def _ideal_answer(question: str, resume: dict) -> str:
    """Produce a substantive, on-topic answer that varies every turn.

    The answer cites a different resume bullet each turn and references the
    actual question wording so the LLM sees genuine engagement.
    """
    bullets = _resume_bullets(resume)
    key = id(resume)
    idx = _ideal_turn_counter.get(key, 0)
    _ideal_turn_counter[key] = idx + 1
    bullet = bullets[idx % len(bullets)]
    headline = resume["headline"].split("·")[0].strip()
    topic = _question_keywords(question)

    templates = [
        (
            f"Good question on {topic!s}. Concretely, in my role as {headline}, "
            f"{bullet} The decision came down to balancing throughput against "
            f"operational risk; we picked the approach because it let a small "
            f"team own the rollout end-to-end. Happy to go deeper on the "
            f"trade-offs or the metrics we tracked."
        ),
        (
            f"On {topic!s}: the way I usually frame this is to start from the "
            f"failure modes and work backwards. {bullet} What worked was "
            f"writing down the SLOs first, then choosing the simplest design "
            f"that hit them. We measured success by p95 latency and weekly "
            f"incident count."
        ),
        (
            f"Sure. {bullet} Specifically for {topic!s}, the lesson I took "
            f"away was that the tooling matters less than the feedback loop \u2014 "
            f"we cut review time in half by adding contract tests in CI and "
            f"that shifted the team\u2019s velocity more than any framework "
            f"choice."
        ),
        (
            f"Yeah, I\u2019ve owned this end-to-end. {bullet} For {topic!s} the "
            f"key decision was rollout strategy: we shadow-deployed for two "
            f"weeks, compared outputs against the legacy path, and only "
            f"cut over once error rates were within 0.1%. That gave us a "
            f"clean rollback story."
        ),
        (
            f"Happy to walk through that. {bullet} On {topic!s} specifically, "
            f"I leaned on a small set of metrics \u2014 latency, error budget, "
            f"and developer NPS \u2014 to know whether the change was actually "
            f"helping. The hardest part was getting alignment across teams, "
            f"not the implementation."
        ),
    ]
    return templates[idx % len(templates)]


def _vague_answer(question: str, resume: dict) -> str:
    pool = [
        "Yeah, I have done that before. It went well.",
        "I think I'm good at that.",
        "Sure, lots of experience with that.",
        "Mostly the usual stuff, nothing special.",
    ]
    return pool[secrets.randbelow(len(pool))]


def _rambling_answer(question: str, resume: dict) -> str:
    return (
        "So actually that reminds me of this one weekend trip to the mountains "
        "where I was thinking about backpacking gear, which got me into product "
        "design in a roundabout way, and then I had this conversation with my "
        "cousin about logistics, and you know what, I'm not sure if I ever "
        "really answered the question but the meta-point I want to make is "
        "that everything is connected if you look hard enough."
    )


def _parroted_answer(question: str, resume: dict) -> str:
    # Echoes the question back verbatim (triggers parroting / repetition heuristics)
    return question + " " + question


def _pasted_blob(question: str, resume: dict) -> str:
    # Looks copy-pasted from a generic source. Will be sent with was_pasted=true.
    return (
        "According to industry best practices, the key to this question is to "
        "leverage scalable solutions while maintaining a customer-centric mindset. "
        "By aligning stakeholders and iterating quickly, teams can unlock "
        "synergies and deliver value at scale. Communication and collaboration "
        "are essential cornerstones of any successful initiative."
    )


BEHAVIOR_PROFILES: dict[str, dict] = {
    "ideal":     {"answer_fn": _ideal_answer,    "paste": False, "tab_switches": 0, "delay": 35.0, "use_llm": "ideal"},
    "vague":     {"answer_fn": _vague_answer,    "paste": False, "tab_switches": 0, "delay": 8.0,  "use_llm": "vague"},
    "rambling":  {"answer_fn": _rambling_answer, "paste": False, "tab_switches": 1, "delay": 22.0, "use_llm": None},
    "pasted":    {"answer_fn": _pasted_blob,     "paste": True,  "tab_switches": 3, "delay": 6.0,  "use_llm": None},
    "parrot":    {"answer_fn": _parroted_answer, "paste": False, "tab_switches": 2, "delay": 5.0,  "use_llm": None},
}


# ---------------------------------------------------------------------------
# Resume DOCX builder
# ---------------------------------------------------------------------------

def build_resume_docx(resume: dict) -> bytes:
    """Build a DOCX resume from the structured fixture."""
    doc = DocxDocument()
    doc.add_heading(resume["name"], level=0)
    doc.add_paragraph(resume["headline"])

    doc.add_heading("Skills", level=1)
    doc.add_paragraph(", ".join(resume["skills"]))

    doc.add_heading("Experience", level=1)
    for company, role, bullets in resume["experience"]:
        doc.add_paragraph(f"{role} — {company}", style="List Bullet")
        for b in bullets:
            doc.add_paragraph(f"  • {b}")

    doc.add_heading("Education", level=1)
    doc.add_paragraph(resume["education"])

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

class APIClient:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=120.0)
        self.token: str | None = None

    async def aclose(self):
        await self.client.aclose()

    @property
    def headers(self) -> dict[str, str]:
        h = {"X-Requested-With": "XMLHttpRequest"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    async def login(self, email: str, password: str) -> None:
        r = await self.client.post(
            f"{self.base}/auth/login",
            json={"email": email, "password": password},
        )
        r.raise_for_status()
        self.token = r.json()["access_token"]

    async def create_job(self, payload: dict) -> dict:
        r = await self.client.post(
            f"{self.base}/jobs", json=payload, headers=self.headers,
        )
        r.raise_for_status()
        return r.json()

    async def apply(
        self, job_token: str, name: str, email: str, filename: str, content: bytes
    ) -> httpx.Response:
        files = {"resume": (filename, content,
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        data = {
            "job_token": job_token,
            "candidate_name": name,
            "candidate_email": email,
        }
        return await self.client.post(
            f"{self.base}/interview/apply", data=data, files=files,
        )

    async def application_status(self, interview_token: str) -> dict:
        r = await self.client.get(
            f"{self.base}/interview/apply/{interview_token}/status",
        )
        r.raise_for_status()
        return r.json()

    async def session_landing(self, interview_token: str) -> dict:
        r = await self.client.get(f"{self.base}/interview/session/{interview_token}")
        r.raise_for_status()
        return r.json()

    async def session_start(self, interview_token: str) -> dict:
        r = await self.client.post(
            f"{self.base}/interview/session/{interview_token}/start",
        )
        r.raise_for_status()
        return r.json()

    async def send_message(
        self, interview_token: str, message: str, integrity: dict | None = None,
    ) -> dict:
        body = {"interview_token": interview_token, "message": message}
        if integrity:
            body["integrity_signals"] = integrity
        r = await self.client.post(f"{self.base}/interview/message", json=body)
        r.raise_for_status()
        return r.json()

    async def list_candidates(self, job_id: str) -> dict:
        r = await self.client.get(
            f"{self.base}/jobs/{job_id}/candidates?limit=100",
            headers=self.headers,
        )
        r.raise_for_status()
        return r.json()

    async def get_candidate(self, candidate_id: str) -> dict:
        r = await self.client.get(
            f"{self.base}/candidates/{candidate_id}", headers=self.headers,
        )
        r.raise_for_status()
        return r.json()

    async def approve_pre_screen(self, candidate_id: str) -> dict:
        r = await self.client.post(
            f"{self.base}/candidates/{candidate_id}/approve-interview",
            headers=self.headers,
        )
        r.raise_for_status()
        return r.json()

    async def reject_pre_screen(self, candidate_id: str) -> dict:
        r = await self.client.post(
            f"{self.base}/candidates/{candidate_id}/reject-pre-screen",
            headers=self.headers,
        )
        r.raise_for_status()
        return r.json()


# ---------------------------------------------------------------------------
# Per-application record
# ---------------------------------------------------------------------------

@dataclass
class AppRecord:
    job_key: str
    resume_key: str
    behavior: str
    candidate_email: str
    candidate_name: str
    interview_token: str = ""
    candidate_id: str = ""
    apply_status: int = 0
    apply_error: str = ""
    final_app_status: str = ""           # processing → ready / review_pending / error
    pre_screen_decision: str = ""
    pre_screen_score: float | None = None
    pre_screen_confidence: float | None = None
    hr_action: str = ""                  # "approved" | "rejected" | ""
    interview_started: bool = False
    interview_completed: bool = False
    turns: int = 0
    follow_ups_observed: int = 0
    questions_total: int = 0
    final_progress: str = ""
    transcript_len: int = 0
    cost_usd: float | None = None
    integrity_signals: dict = field(default_factory=dict)
    evaluation: dict | None = None
    eval_wait_s: float | None = None
    timings: dict[str, list[float]] = field(default_factory=lambda: {
        "apply": [], "session_start": [], "message": [],
    })
    issues: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

async def wait_until_terminal(
    client: APIClient, token: str, timeout_s: float = 90.0,
) -> dict:
    """Poll /apply/status until status leaves 'processing' or timeout."""
    start = time.monotonic()
    last: dict = {}
    while time.monotonic() - start < timeout_s:
        last = await client.application_status(token)
        if last["status"] != "processing":
            return last
        await asyncio.sleep(2.0)
    return last


async def drive_interview(
    client: APIClient, rec: AppRecord, behavior: dict, planned_questions_hint: int,
    *,
    llm_http: httpx.AsyncClient | None = None,
) -> None:
    """Run the chat loop for a single candidate."""
    # 1. Session landing
    landing = await client.session_landing(rec.interview_token)
    rec.questions_total = landing.get("total_questions", planned_questions_hint)

    # 2. Start session (LLM opening message)
    t0 = time.monotonic()
    start = await client.session_start(rec.interview_token)
    rec.timings["session_start"].append(time.monotonic() - t0)
    rec.interview_started = True
    last_ai = start["first_message"]
    log.info("[%s] opening: %s", rec.candidate_email, last_ai[:120])

    # 3. Loop
    answer_fn = behavior["answer_fn"]
    paste = behavior["paste"]
    tab_switches_per_turn = behavior["tab_switches"]
    delay = behavior["delay"]
    use_llm = behavior.get("use_llm")  # "ideal" | "vague" | None
    job_title = JOB_BY_KEY[rec.job_key]["title"]
    resume = RESUME_BY_KEY[rec.resume_key]

    # Hard upper bound (server will also cap at 50 messages)
    max_turns = 30
    last_progress_idx = 0

    for _turn in range(max_turns):
        if use_llm and llm_http is not None:
            msg = await llm_candidate_answer(
                http=llm_http, question=last_ai, resume=resume,
                job_title=job_title, style=use_llm,
            )
        else:
            msg = answer_fn(last_ai, resume)
        integrity = {
            "was_pasted": paste,
            "tab_switch_count": tab_switches_per_turn,
            "time_to_answer_seconds": delay,
        }
        t0 = time.monotonic()
        try:
            resp = await client.send_message(rec.interview_token, msg, integrity)
        except httpx.HTTPStatusError as e:
            rec.issues.append(f"message_http_{e.response.status_code}: {e.response.text[:200]}")
            break
        rec.timings["message"].append(time.monotonic() - t0)
        rec.turns += 1
        last_ai = resp["ai_response"]
        rec.final_progress = resp["progress"]

        # Track follow-ups: progress numerator unchanged → follow-up
        try:
            cur = int(resp["progress"].split("/")[0])
            if cur == last_progress_idx:
                rec.follow_ups_observed += 1
            last_progress_idx = cur
        except Exception:
            pass

        if resp["is_complete"]:
            rec.interview_completed = True
            log.info("[%s] interview complete after %d turns (%s)",
                     rec.candidate_email, rec.turns, resp["progress"])
            break


async def wait_for_evaluation(
    client: APIClient, rec: AppRecord, timeout_s: float = 90.0,
) -> None:
    """Poll candidate detail for evaluation after completion."""
    if not rec.candidate_id or not rec.interview_completed:
        return
    start = time.monotonic()
    while time.monotonic() - start < timeout_s:
        detail = await client.get_candidate(rec.candidate_id)
        ev = detail.get("evaluation")
        if ev and ev.get("overall_score") is not None:
            rec.evaluation = ev
            rec.eval_wait_s = time.monotonic() - start
            iv = detail.get("interview") or {}
            rec.cost_usd = iv.get("cost_usd")
            rec.transcript_len = iv.get("transcript_length", 0)
            rec.integrity_signals = iv.get("integrity_signals") or {}
            return
        await asyncio.sleep(3.0)
    rec.issues.append(f"evaluation_missing_after_{int(timeout_s)}s")


# ---------------------------------------------------------------------------
# Test plan
# ---------------------------------------------------------------------------

# How resumes map to behaviors per job. We aim for 20 applications and ~10-12
# completed interviews — auto_all + hybrid (default + loose) will yield most
# interviews; manual_all needs HR approval; hybrid_strict mostly to review.
PLAN: list[tuple[str, str, str]] = [
    # (job_key, resume_key, behavior)

    # JD1 fullstack_hybrid_default — expect 2 ready (strong + ml-leaning), 1 review (designer), 1 review/reject (junior)
    ("fullstack_hybrid_default", "strong_fullstack",            "ideal"),
    ("fullstack_hybrid_default", "partial_fullstack_ml_leaning","vague"),
    ("fullstack_hybrid_default", "off_domain_designer",         "rambling"),
    ("fullstack_hybrid_default", "junior_frontend",             "ideal"),

    # JD2 ml_hybrid_strict (90/80) — only ML resume should auto-invite; others to review
    ("ml_hybrid_strict",         "partial_fullstack_ml_leaning","ideal"),
    ("ml_hybrid_strict",         "strong_fullstack",            "ideal"),
    ("ml_hybrid_strict",         "off_domain_designer",         "vague"),
    ("ml_hybrid_strict",         "junior_frontend",             "vague"),

    # JD3 devops_auto_all — all 4 auto-invited regardless of fit; mix of behaviors
    ("devops_auto_all",          "strong_fullstack",            "ideal"),
    ("devops_auto_all",          "partial_fullstack_ml_leaning","pasted"),
    ("devops_auto_all",          "off_domain_designer",         "parrot"),
    ("devops_auto_all",          "junior_frontend",             "rambling"),

    # JD4 designer_manual_all — all 4 to review; we approve 2 to drive interviews
    ("designer_manual_all",      "off_domain_designer",         "ideal"),    # approve
    ("designer_manual_all",      "junior_frontend",             "vague"),    # approve
    ("designer_manual_all",      "strong_fullstack",            "ideal"),    # reject
    ("designer_manual_all",      "partial_fullstack_ml_leaning","ideal"),    # reject

    # JD5 frontend_hybrid_loose (60/40) — strong + junior should auto-invite
    ("frontend_hybrid_loose",    "junior_frontend",             "ideal"),
    ("frontend_hybrid_loose",    "strong_fullstack",            "vague"),
    ("frontend_hybrid_loose",    "off_domain_designer",         "rambling"),
    ("frontend_hybrid_loose",    "partial_fullstack_ml_leaning","ideal"),
]

# Per (job_key, resume_key) HR action override for manual_all flow
HR_ACTIONS: dict[tuple[str, str], str] = {
    ("designer_manual_all", "off_domain_designer"):          "approve",
    ("designer_manual_all", "junior_frontend"):              "approve",
    ("designer_manual_all", "strong_fullstack"):             "reject",
    ("designer_manual_all", "partial_fullstack_ml_leaning"): "reject",
    # Optional: also approve a hybrid_strict review_pending so we get an
    # interview from the strict job and exercise that path.
    ("ml_hybrid_strict",    "partial_fullstack_ml_leaning"): "approve",
    ("ml_hybrid_strict",    "strong_fullstack"):             "approve",
}


RESUME_BY_KEY: dict[str, dict] = {r["key"]: r for r in RESUMES}
JOB_BY_KEY: dict[str, dict] = {j["key"]: j for j in JOBS}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run(backend: str, hr_email: str, hr_password: str) -> dict:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    client = APIClient(backend)
    summary: dict[str, Any] = {
        "run_id": run_id,
        "backend": backend,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "jobs": [],
        "applications": [],
        "issues_global": [],
        "duplicate_test": {},
    }

    # Dedicated httpx client for direct DeepSeek calls (candidate answer LLM).
    llm_http = httpx.AsyncClient(timeout=45.0)
    try:
        log.info("Logging in as %s", hr_email)
        await client.login(hr_email, hr_password)


        # 1. Create JDs
        job_token_by_key: dict[str, str] = {}
        job_id_by_key: dict[str, str] = {}
        for j in JOBS:
            payload = {
                "title": j["title"],
                "description": j["description"],
                "required_skills": j["required_skills"],
                "screening_mode": j["screening_mode"],
                "auto_invite_threshold": j["auto_invite_threshold"],
                "review_threshold": j["review_threshold"],
                "interview_config": {"num_questions": 6},  # smaller = faster runs
                "auto_send_status_emails": False,
            }
            resp = await client.create_job(payload)
            token = resp["job"]["interview_link_token"]
            job_token_by_key[j["key"]] = token
            job_id_by_key[j["key"]] = resp["job"]["id"]
            summary["jobs"].append({"key": j["key"], "id": resp["job"]["id"], "token": token})
            log.info("Created JD %s (token=%s)", j["key"], token[:10])

        # 2. Submit applications
        records: list[AppRecord] = []
        for i, (job_key, resume_key, behavior_name) in enumerate(PLAN):
            resume = RESUME_BY_KEY[resume_key]
            email = f"c{i:02d}.{run_id}@stress.test"
            rec = AppRecord(
                job_key=job_key, resume_key=resume_key, behavior=behavior_name,
                candidate_email=email, candidate_name=resume["name"],
            )
            records.append(rec)

            content = build_resume_docx(resume)
            t0 = time.monotonic()
            try:
                r = await client.apply(
                    job_token=job_token_by_key[job_key],
                    name=resume["name"], email=email,
                    filename=f"{resume_key}.docx", content=content,
                )
                rec.timings["apply"].append(time.monotonic() - t0)
                rec.apply_status = r.status_code
                if r.status_code != 200:
                    rec.apply_error = r.text[:300]
                    rec.issues.append(f"apply_failed_{r.status_code}")
                    continue
                body = r.json()
                rec.candidate_id = body["candidate_id"]

                # We do NOT have the interview_token from /apply — the API
                # intentionally hides it. Look it up via HR endpoint instead.
            except Exception as e:
                rec.apply_error = repr(e)
                rec.issues.append("apply_exception")

        # 3. Resolve interview_tokens.
        # The public /apply response intentionally hides the interview_token.
        # In a real stress test we don't want to wait for an actual email,
        # so we read the token directly from the DB (test-only).
        sys.path.insert(0, str(ROOT))
        from app.database import async_session_factory  # noqa: E402
        from app.models.candidate import Candidate  # noqa: E402

        async with async_session_factory() as db:
            for rec in records:
                if not rec.candidate_id:
                    continue
                row = await db.get(Candidate, rec.candidate_id)
                if row:
                    rec.interview_token = row.interview_token or ""

        # 4. Wait for background processing (parse → score → screen) — parallel
        log.info("Waiting for background processing on %d applications…", len(records))

        async def _poll_one(rec: AppRecord) -> None:
            if not rec.interview_token:
                return
            try:
                last = await wait_until_terminal(client, rec.interview_token, timeout_s=180.0)
                rec.final_app_status = last.get("status", "")
            except Exception as e:
                rec.issues.append(f"status_poll_error: {e!r}")

        await asyncio.gather(*(_poll_one(r) for r in records))

        # 5. Pull pre-screen decision from candidate detail
        for rec in records:
            if not rec.candidate_id:
                continue
            try:
                detail = await client.get_candidate(rec.candidate_id)
                ps = detail.get("pre_screen") or {}
                rec.pre_screen_decision = ps.get("decision", "") or ""
                rec.pre_screen_score = ps.get("score")
                rec.pre_screen_confidence = ps.get("confidence")
            except Exception as e:
                rec.issues.append(f"detail_fetch_error: {e!r}")

        # 6. HR actions on review_pending
        for rec in records:
            if rec.final_app_status != "review_pending":
                continue
            action = HR_ACTIONS.get((rec.job_key, rec.resume_key))
            if action == "approve":
                try:
                    await client.approve_pre_screen(rec.candidate_id)
                    rec.hr_action = "approved"
                    # After approval candidate becomes 'ready' → re-poll
                    last = await wait_until_terminal(client, rec.interview_token, 60.0)
                    rec.final_app_status = last.get("status", "")
                except Exception as e:
                    rec.issues.append(f"approve_error: {e!r}")
            elif action == "reject":
                try:
                    await client.reject_pre_screen(rec.candidate_id)
                    rec.hr_action = "rejected"
                    rec.final_app_status = "rejected"
                except Exception as e:
                    rec.issues.append(f"reject_error: {e!r}")

        # 7. Drive interviews for everyone in 'ready'
        interview_recs = [r for r in records if r.final_app_status == "ready"]
        log.info("Driving %d interviews", len(interview_recs))
        for rec in interview_recs:
            behavior = BEHAVIOR_PROFILES[rec.behavior]
            try:
                await drive_interview(client, rec, behavior, planned_questions_hint=6, llm_http=llm_http)
            except Exception:
                rec.issues.append("drive_interview_exception")
                rec.issues.append(traceback.format_exc()[:1000])

        # 8. Wait for auto-evaluations
        log.info("Waiting for evaluations…")
        for rec in interview_recs:
            if rec.interview_completed:
                try:
                    await wait_for_evaluation(client, rec, timeout_s=120.0)
                except Exception as e:
                    rec.issues.append(f"eval_wait_error: {e!r}")

        # 9. Edge-case probes
        # 9a. Duplicate application (same email+job) → expect 409
        try:
            dup_resume = RESUMES[0]
            dup_email = f"c00.{run_id}@stress.test"  # already used for fullstack job
            content = build_resume_docx(dup_resume)
            r = await client.apply(
                job_token=job_token_by_key["fullstack_hybrid_default"],
                name=dup_resume["name"], email=dup_email,
                filename="dup.docx", content=content,
            )
            summary["duplicate_test"] = {
                "status_code": r.status_code,
                "expected": 409,
                "ok": r.status_code == 409,
                "body": r.text[:200],
            }
        except Exception as e:
            summary["duplicate_test"] = {"error": repr(e)}

        # 9b. Corrupt PDF upload → expect 400
        try:
            r = await client.apply(
                job_token=job_token_by_key["fullstack_hybrid_default"],
                name="Corrupt Tester",
                email=f"corrupt.{run_id}@stress.test",
                filename="bad.pdf",
                content=b"NOT A REAL PDF",
            )
            summary["corrupt_pdf_test"] = {
                "status_code": r.status_code,
                "expected": 400,
                "ok": r.status_code == 400,
                "body": r.text[:200],
            }
        except Exception as e:
            summary["corrupt_pdf_test"] = {"error": repr(e)}

        # Stash records
        summary["applications"] = [vars(r) for r in records]

    finally:
        await client.aclose()
        try:
            await llm_http.aclose()
        except Exception:
            pass

    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    return summary


def write_reports(summary: dict) -> tuple[Path, Path]:
    run_id = summary["run_id"]
    json_path = REPORTS_DIR / f"interview_flow_{run_id}.json"
    md_path = REPORTS_DIR / f"interview_flow_{run_id}.md"
    json_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    apps = summary["applications"]
    completed = [a for a in apps if a.get("interview_completed")]
    with_eval = [a for a in completed if a.get("evaluation")]
    no_eval = [a for a in completed if not a.get("evaluation")]
    review_pending = [a for a in apps if a.get("pre_screen_decision") == "review"]
    auto_invite = [a for a in apps if a.get("pre_screen_decision") == "auto_invite"]

    def _avg(xs):
        return round(sum(xs) / len(xs), 2) if xs else None

    def _flatten_timings(field_name: str):
        out = []
        for a in apps:
            out.extend(a.get("timings", {}).get(field_name, []))
        return out

    apply_times = _flatten_timings("apply")
    msg_times = _flatten_timings("message")
    start_times = _flatten_timings("session_start")

    cost_total = sum((a.get("cost_usd") or 0.0) for a in apps)

    lines: list[str] = []
    lines.append(f"# Interview Flow Stress Run — {run_id}\n")
    lines.append(f"- Backend: `{summary['backend']}`")
    lines.append(f"- Started: {summary['started_at']}")
    lines.append(f"- Finished: {summary['finished_at']}")
    lines.append("")
    lines.append("## Headline numbers")
    lines.append(f"- Applications submitted: **{len(apps)}**")
    lines.append(f"- Auto-invited by screening: **{len(auto_invite)}**")
    lines.append(f"- Routed to HR review: **{len(review_pending)}**")
    lines.append(f"- Interviews started: **{sum(1 for a in apps if a['interview_started'])}**")
    lines.append(f"- Interviews completed: **{len(completed)}**")
    lines.append(f"- Evaluations produced: **{len(with_eval)}** / {len(completed)}")
    lines.append(f"- Total LLM cost (sum of cost_usd): **${cost_total:.4f}**")
    lines.append("")
    lines.append("## Latency (seconds)")
    lines.append(f"- /apply        avg={_avg(apply_times)}  n={len(apply_times)}")
    lines.append(f"- /session/start avg={_avg(start_times)} n={len(start_times)}")
    lines.append(f"- /message      avg={_avg(msg_times)}    n={len(msg_times)}")
    lines.append("")
    lines.append("## Edge-case probes")
    lines.append(f"- Duplicate application: {summary.get('duplicate_test')}")
    lines.append(f"- Corrupt PDF upload:    {summary.get('corrupt_pdf_test')}")
    lines.append("")

    lines.append("## Per-application table")
    lines.append("")
    lines.append("| job | resume | behavior | apply | app_status | screen | score | conf | hr | started | done | turns | f-ups | progress | eval_score | recommend | issues |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for a in apps:
        ev = a.get("evaluation") or {}
        score = a.get("pre_screen_score")
        conf = a.get("pre_screen_confidence")
        lines.append(
            f"| {a['job_key']} | {a['resume_key']} | {a['behavior']} "
            f"| {a['apply_status']} | {a['final_app_status'] or '-'} | {a['pre_screen_decision'] or '-'} "
            f"| {score if score is not None else '-'} | {conf if conf is not None else '-'} "
            f"| {a['hr_action'] or '-'} "
            f"| {'✓' if a['interview_started'] else '·'} | {'✓' if a['interview_completed'] else '·'} "
            f"| {a['turns']} | {a['follow_ups_observed']} | {a['final_progress'] or '-'} "
            f"| {ev.get('overall_score') if ev else '-'} | {ev.get('recommendation') if ev else '-'} "
            f"| {'; '.join(a['issues'])[:80]} |"
        )
    lines.append("")

    if no_eval:
        lines.append("## ⚠ Completed interviews missing evaluation")
        for a in no_eval:
            lines.append(f"- {a['candidate_email']} ({a['job_key']}/{a['resume_key']})")
        lines.append("")

    issue_counts: dict[str, int] = {}
    for a in apps:
        for i in a["issues"]:
            key = i.split(":", 1)[0]
            issue_counts[key] = issue_counts.get(key, 0) + 1
    if issue_counts:
        lines.append("## Issue frequency")
        for k, v in sorted(issue_counts.items(), key=lambda x: -x[1]):
            lines.append(f"- {k}: {v}")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="http://localhost:8000")
    ap.add_argument("--hr-email", default="admin@techcorp.com")
    ap.add_argument("--hr-password", default="Password123!")
    args = ap.parse_args()

    summary = asyncio.run(run(args.backend, args.hr_email, args.hr_password))
    json_path, md_path = write_reports(summary)
    print("\n[OK] Run complete.")
    print(f"   JSON: {json_path}")
    print(f"   MD:   {md_path}")


if __name__ == "__main__":
    main()
