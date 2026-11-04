"""Dump full interview transcripts so we can audit interviewer quality."""
# Refuse before imports that can connect, write, or expose application data.
import sys as _guard_sys
from pathlib import Path as _GuardPath
_guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
from scripts.owned_workspace import require_owned_workspace, owned_path
_OWNED_ROOT = require_owned_workspace(providers=False, http_target=False)

import sqlite3
import json
import sys

DB = owned_path(_OWNED_ROOT / "owned.db")
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

# join interview -> candidate -> job
cur.execute("""
    SELECT i.id, i.status, i.transcript, i.planned_questions, i.current_question_index,
           c.name AS cand_name, c.email AS cand_email,
           jp.title AS job_title
    FROM interviews i
    JOIN candidates c ON c.id = i.candidate_id
    JOIN job_postings jp ON jp.id = i.job_posting_id
    ORDER BY i.started_at
""")
rows = list(cur.fetchall())
print(f"# Total interviews: {len(rows)}\n")

# args: indices to dump
which = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else [12, 16, 18, 20]

for idx in which:
    if idx >= len(rows):
        continue
    r = rows[idx]
    t = json.loads(r["transcript"]) if r["transcript"] else []
    pq = json.loads(r["planned_questions"]) if r["planned_questions"] else []

    print("=" * 110)
    print(f"INTERVIEW #{idx}  id={r['id'][:8]}  status={r['status']}  q_idx={r['current_question_index']}")
    print(f"  candidate: {r['cand_name']}  <{r['cand_email']}>")
    print(f"  job:       {r['job_title']}")
    print(f"  turns:     {len(t)}   planned questions: {len(pq)}")
    print("\n--- PLANNED QUESTIONS ---")
    for i, q in enumerate(pq, 1):
        print(f"  Q{i} [{q.get('category','?')}] {q.get('question','')}")
    print("\n--- TRANSCRIPT ---")
    for i, m in enumerate(t):
        role = m.get("role", "?")
        content = m.get("content", "")
        print(f"\n[{i}] {role.upper()}:")
        print(content if len(content) < 800 else content[:800] + "...[TRUNC]")
    print()
