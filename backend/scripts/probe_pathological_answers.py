"""Historical HTTP answer-quality probe.

Disabled: retained as source for ownership/refusal regression checks only.
Execution refuses before reading environment files, connecting or producing reports.
Use the deterministic portfolio verifier for supported local acceptance.
"""
# Refuse before imports that can connect, write, or expose application data.
import sys as _guard_sys
from pathlib import Path as _GuardPath
_guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
from scripts.owned_workspace import require_owned_workspace
_OWNED_ROOT = require_owned_workspace(providers=True, http_target=True)

import asyncio
import os
import random
import sys
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:
    pass

BACKEND = "http://localhost:8000"

# Reuse the harness's resume DOCX generator
from scripts.stress_test_interview_flow import build_resume_docx, RESUMES

PROBES = [
    ("blank", ""),
    ("single_char", "."),
    ("yes", "yes"),
    ("idk", "I don't know."),
    ("offtopic_weather", "I love sunny weather and going to the beach. The ocean is calming."),
    ("offtopic_recipe", "First, preheat the oven to 350F. Then mix flour, sugar, and butter in a bowl until smooth. Bake for 25 minutes."),
    ("gibberish", "asdkfjh asldkfj qoiweur xkcvjhq plzxvm rtwerty zxcvbn mnbvcxz"),
    ("emoji_only", "👍 😀 🔥 ✨ 🚀"),
    ("profanity_lite", "honestly this is a stupid question and I won't answer it"),
    ("very_long_garbage", " ".join(random.choices(["lorem", "ipsum", "dolor", "sit", "amet"], k=200))),
]


async def main():
    suffix = f"probe.{random.randint(1000,9999)}"
    # JOBS/RESUMES are LISTS in this harness, not dicts
    resume = next((r for r in RESUMES if r.get("key") == "strong_fullstack"), RESUMES[0])
    pdf = build_resume_docx(resume)
    email = f"probe.{suffix}@stress.test"
    async with httpx.AsyncClient(timeout=60.0) as http:
        # 1. ensure job exists by posting one job (use an existing one if visible)
        # Easier: hit the public form-style apply endpoint
        # but jobs need to exist. Use harness helper would require auth; instead reuse the most recent job in DB.
        import sqlite3
        con = sqlite3.connect(os.path.join(os.path.dirname(__file__), "..", "hr_interviewer.db"))
        cur = con.cursor()
        cur.execute("SELECT id, title, interview_link_token FROM job_postings ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        con.close()
        job_id, job_title, job_token = row
        print(f"[probe] using job: {job_title} (id={job_id[:8]} token={job_token[:8]})")

        files = {"resume": ("resume.docx", pdf, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        data = {
            "job_token": job_token,
            "candidate_name": "Probe Candidate",
            "candidate_email": email,
        }
        r = await http.post(f"{BACKEND}/interview/apply", data=data, files=files)
        print(f"[probe] apply -> {r.status_code}")
        if r.status_code >= 400:
            print(r.text[:400])
            return
        body = r.json()
        # different shapes — try to extract candidate id / interview token
        cand_id = body.get("candidate_id") or body.get("id")

        # poll the DB directly for the candidate's interview_token + status
        token = None
        status = None
        for _ in range(60):
            con = sqlite3.connect(os.path.join(os.path.dirname(__file__), "..", "hr_interviewer.db"))
            cur = con.cursor()
            cur.execute("SELECT interview_token, status FROM candidates WHERE id=?", (cand_id,))
            r2 = cur.fetchone()
            con.close()
            if r2:
                token, status = r2
                if token and status in ("ready", "invited", "in_progress"):
                    break
            await asyncio.sleep(2)
        print(f"[probe] got token={token[:8] if token else None} status={status}")
        if not token or status not in ("ready","invited","in_progress"):
            print("[probe] no usable interview; status=", status)
            return

        # session
        r = await http.get(f"{BACKEND}/interview/session/{token}")
        print(f"[probe] session -> {r.status_code}")
        # start
        r = await http.post(f"{BACKEND}/interview/session/{token}/start")
        first = r.json()
        print(f"\n[INTERVIEWER opening] {first.get('first_message','')[:300]}")

        # send the probes one by one
        for label, text in PROBES:
            r = await http.post(
                f"{BACKEND}/interview/message",
                json={"interview_token": token, "message": text},
            )
            if r.status_code != 200:
                print(f"\n[!] probe {label!r} -> HTTP {r.status_code}: {r.text[:200]}")
                continue
            j = r.json()
            print(f"\n--- PROBE: {label!r} (sent {len(text)} chars) ---")
            print(f"  candidate -> {text[:120]!r}")
            print(f"  interviewer ({j['progress']}, complete={j['is_complete']}):")
            print(f"  {j['ai_response'][:500]}")
            if j["is_complete"]:
                print("[probe] interview complete; stopping")
                break

asyncio.run(main())
