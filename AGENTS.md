# Repository working instructions

Scope: source-visible portfolio prototype for fictional local evaluation.
Verified: Windows, Python 3.11.9, Node 22.16.0, npm 10.9.2, SQLite, one worker.
Read `docs/quality-checks.md` for canonical locked installation and checks,
`docs/portfolio-demo.md` for owned lifecycle, and `release/RELEASE_SOURCE_INVENTORY.md`
for the proposed publication boundary.

- `backend/app`: FastAPI routes/services/models; `backend/alembic`: migrations;
  `backend/tests`: tests and synthetic fixtures; `backend/scripts`: owned runners.
- `frontend/src/app`: Next App Router; `frontend/server.mjs`: required custom
  server/proxy; `frontend/tests`: Node contracts and Chromium smoke.
- `scripts`: canonical checks; `security`: scanner lock/baseline; `docs`: current
  guides; `release`: public verification metadata; `.local-dev`: ignored internal records.

Preserve existing modified/untracked work. Do not revert or stage unrelated files.
Keep edits focused; do not rewrite historical migrations or remove owner plans.
Routine reversible fixes and documentation do not require extra approval.

From repository root, after canonical installation:

```powershell
.venv/Scripts/python.exe scripts/check.py lint
.venv/Scripts/python.exe scripts/check.py backend
.venv/Scripts/python.exe scripts/check.py frontend
.venv/Scripts/python.exe scripts/check.py demo
.venv/Scripts/python.exe scripts/check.py browser
.venv/Scripts/python.exe scripts/check.py dependencies
.venv/Scripts/python.exe scripts/check.py secrets
```

Run checks relevant to the change; keep dependency findings visible. For docs,
check links, referenced files, command consistency and current-source secrets.
Never blindly regenerate the secret baseline. Use fictional fixtures/reserved
domains, no real candidates, paid AI or real delivery in ordinary verification.
Never copy `.env`, uploads, DBs, captures or `.release-work` into publishable source.
Do not run reset/export/seed tools against existing data: their authorization is
limited to fresh runner-owned targets. Preserve authenticated stop/cleanup,
single-worker limits, proxy trust, role checks and manual notification semantics.

Usage follows RIGHTS.md; owner-authorized work remains authorized. Use the existing
repository and preserve history. No private reporting channel is being configured;
contact selection is not a blocker. Dependency remediation is mandatory without
exceptions. Follow-up changes need CI for their own SHA. Exact public refs and explicit publication authorization
remain owner decisions. No public-ready, legal-compliance,
hiring-validity or broad platform-support claims. Contributor process is not a
license grant. Before release preparation, review the source inventory and canonical checks,
reconcile exact source/refs, review provenance and remote assets, and obtain
explicit publication authorization. Never mirror capture/checkpoint refs.
Local preparation does not authorize staging, commits, pushes, settings changes
or deployment; follow the owner-authorized scope for those actions.
