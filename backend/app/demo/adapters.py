"""Deterministic responses at provider boundaries; routes and writes stay real."""

import json
import secrets
from types import SimpleNamespace

from app.demo.guard import require_demo


def fail_once(operation):
    root = require_demo()
    flag = root / ("fail-" + operation)
    if flag.exists():
        flag.unlink()
        raise ValueError("Synthetic one-shot provider failure; retry is available")


def completion(operation, context):
    require_demo()
    fail_once("processing")
    if operation == "parse":
        text = context["text"]
        # Fixture recognition occurs AFTER real, isolated PDF/DOCX extraction.
        if "Avery Example" in text:
            strong, name, email = True, "Avery Example", "avery@example.com"
        elif "Riley Sample" in text:
            strong, name, email = False, "Riley Sample", "riley@example.com"
        else:
            raise ValueError(
                "Demo parser supports only the documented fictional resumes"
            )
        skills = ["Python", "FastAPI", "SQL"] if strong else ["Customer support"]
        result = {
            "name": name,
            "email": email,
            "phone": "",
            "years_experience": 6 if strong else 1,
            "current_role": "Backend Engineer" if strong else "Support Assistant",
            "current_company": "Fictional Orchard Studio",
            "skills": skills,
            "experience": [
                {
                    "company": "Fictional Orchard Studio",
                    "role": "Engineer" if strong else "Assistant",
                    "duration": "2020-2026" if strong else "2025-2026",
                    "highlights": [
                        "Built Python FastAPI services with SQL and tested recovery."
                        if strong
                        else "Answered customer support enquiries."
                    ],
                }
            ],
            "education": [],
            "summary": "SYNTHETIC portfolio fixture; no hiring accuracy claim.",
        }
    elif operation == "screen":
        strong = context["resume"].get("name") == "Avery Example"
        result = {
            "score": 92 if strong else 35,
            "confidence": 0.95,
            "matched_skills": ["Python", "FastAPI", "SQL"] if strong else [],
            "missing_must_haves": [] if strong else ["Python", "FastAPI", "SQL"],
            "rationale": "SYNTHETIC deterministic portfolio screening, not a hiring assessment.",
        }
    elif operation == "questions":
        questions = [
            "Describe how you built and tested the fictional Python API.",
            "How would you investigate a slow SQL query?",
            "Tell me about a time you helped a teammate resolve a defect.",
            "How would you handle an unavailable upstream service?",
            "Describe your approach to reviewing a change safely.",
            "How do you explain a technical tradeoff to a colleague?",
            "How would you validate a new feature before release?",
            "Describe what you learned from a project setback.",
        ]
        if context.get("category") == "resume_verification":
            questions = [
                "Describe your responsibilities at Fictional Orchard Studio.",
                "How did you test the Python service described in your resume?",
            ]
        result = [
            {
                "question": questions[i % len(questions)],
                "category": context.get("category", "role_specific"),
                "intent": "Synthetic walkthrough",
                "follow_up_if_vague": "Describe a concrete example.",
            }
            for i in range(context["count"])
        ]
    elif operation == "answer":
        result = {"quality": "detailed", "follow_up": "NEXT"}
    elif operation == "opening":
        result = context["question"]
    elif operation == "reply":
        result = (
            "Thank you. This synthetic portfolio interview is complete."
            if context.get("closing")
            else context.get("question") or "Describe a concrete example."
        )
    elif operation == "evaluate":
        result = {
            "skill_match": 8,
            "communication": 8,
            "problem_solving": 8,
            "cultural_fit": 8,
            "overall_score": 8,
            "summary": "SYNTHETIC fixed evaluation for portfolio workflow verification. It does not assess this person's answers or hiring suitability.",
            "strengths": ["Fictional workflow completed"],
            "gaps": ["Real model quality is not evaluated"],
            "red_flags": [],
            "recommendation": "yes",
        }
    else:
        raise ValueError(
            "No portfolio adapter for this operation; live fallback forbidden"
        )
    content = result if isinstance(result, str) else json.dumps(result)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))], usage=None
    )


def capture(kind, recipient, subject, body, link=None):
    root = require_demo()
    try:
        fail_once("email")
    except ValueError:
        return False
    if recipient.rsplit("@", 1)[-1].lower() not in {
        "example.com",
        "example.org",
        "example.net",
    }:
        return False
    mailbox = root / "mailbox"
    mailbox.mkdir(exist_ok=True)
    message = {
        "kind": kind,
        "recipient": recipient,
        "subject": subject,
        "body": body,
        "link": link,
    }
    target = mailbox / (secrets.token_hex(16) + ".json")
    target.write_text(json.dumps(message), encoding="utf-8")
    return True
