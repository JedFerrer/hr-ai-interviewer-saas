# Reproducible release checks

Supported verification scope: **Windows, Python 3.11.9, Node 22.16.0, npm
10.9.2, uv 0.12.1, SQLite, one backend worker**. PostgreSQL and other operating
systems remain unverified. Registry access is needed for installation/audits;
tests and the fictional demo do not require provider credentials.

## Installation

Canonical locked installation, from repository root in PowerShell, without
application/provider overrides. Use a fresh checkout or new environment; do not
replace an existing environment containing work you need to preserve.

```powershell
py -3.11 -m pip install uv==0.12.1
uv venv .venv --python 3.11.9
uv pip sync backend/requirements.lock --python .venv/Scripts/python.exe --require-hashes
npm --prefix frontend ci --fetch-retries=0
```

The application/demo needs the commands above. For security and browser checks,
also install the separate scanner environment and locked Chromium:

```powershell
uv venv .security-venv --python 3.11.9
uv pip sync security/requirements.lock --python .security-venv/Scripts/python.exe --require-hashes
node frontend/node_modules/playwright/cli.js install chromium
```

## Canonical checks

```powershell
.venv/Scripts/python.exe scripts/validate_source.py
.venv/Scripts/python.exe scripts/validate_ci.py
.venv/Scripts/python.exe scripts/check.py lint
.venv/Scripts/python.exe scripts/check.py backend
.venv/Scripts/python.exe scripts/check.py frontend
.venv/Scripts/python.exe scripts/check.py demo
.venv/Scripts/python.exe scripts/check.py browser
.venv/Scripts/python.exe scripts/check.py dependencies
.venv/Scripts/python.exe scripts/check.py secrets
```

The dependency command fails on every finding, without severity filtering or
exceptions. See [the remediation and coverage review](dependency-review.md).

`scripts/rehearse_release.py` copies only `release/RELEASE_SOURCE_FILES.txt` into
a newly owned temporary directory, installs both hashed Python locks and npm
from scratch, then runs all seven checks. It prints each exit status and returns
nonzero if any check fails. It reads original Git history through the explicit
`HR_CHECK_HISTORY_ROOT` boundary; no original environment file, database,
node_modules, build output or `.release-work` helper is copied. Package download
caches may be reused, but every installation and production build is fresh.

## Jobs and cleanup

`.github/workflows/quality.yml` runs on pull requests, pushes to `main`, and manual
dispatch. Feature-branch pushes do not start a separate push run; updating an open
PR runs its checks. A merge into `main` runs checks on the resulting commit.
Recommended future required job names: `backend`, `frontend`, `windows-demo`,
`browser-smoke`, `dependencies`, `secrets`. Do not enable protections until the
owner has reviewed findings and observed hosted runs. The owner confirms CI passed
for PR #6's merge; see the [publication checklist](release-checklist.md). That
dated result does not cover later changes.

The backend job covers correctness lint, the full test suite, three disposable
SQLite migration paths and credential-free API startup. Frontend covers clean
npm install, Oxlint plus compatibility checks, strict TypeScript, Node contract/network tests and production
build. Windows demo covers HTTP transitions, failures, tenancy, ownership,
concurrent runs and cleanup. Browser smoke covers real Chromium UI controls for
employer login, fictional PDF application, interview completion and saved employer
evaluation through the frontend proxy. Invitation retrieval authenticates to the
existing protected fixture mailbox; it never creates completed database records.
The browser journey also checks interview geometry and keyboard reachability at
1440×1000 and 390×844; this does not replace broader mobile/accessibility acceptance. Chromium 156.0.8078.4 / Playwright build 1248 is selected by
Playwright 1.64.1 in the npm lock.

Jobs use Windows 2022 ephemeral runners, read-only contents permission, immutable
action revisions, no persisted checkout credentials, no production secrets,
35-minute bounds and per-ref cancellation. There is no `pull_request_target`,
artifact upload or runtime cache. Browser tracing, screenshots, videos, HAR and
raw exception reports are disabled; failures print only fixed phase labels.

Ordinary failure invokes authenticated stop in `finally`; demo/browser jobs also
have an `always()` cleanup step for their exact job-specific IDs. Canonical demo
checks set a 25-minute supervisor lease. If the checking process is cancelled,
the surviving supervisor expires, stops only retained child handles and performs
ownership-checked removal. Abrupt supervisor/machine death can still leave local
directories: the Windows job closes child processes, hosted runners are discarded,
and uncertain local ownership requires inspection. No saved-PID killing or broad
directory deletion is a fallback. An expired one-second lease is exercised by
the HTTP verifier during preparation. Interactive demo runs have no lease unless
explicitly set.

## Lint, warnings and provider policy

`ruff.toml` defines E4/E7/E9/F/B correctness rules across all shipped Python app,
migration, script, prototype and test source. It does not depend on evolving
Ruff defaults or impose a formatting rewrite. Only import-order E402 is excepted
in entrypoints that must install logging, ownership checks or module paths before
application imports. FastAPI dependency/parameter declarations are recognized
as intentional immutable default calls. No application/security test is excluded.

The deprecated custom pytest event loop was removed; test session factories no
longer look like collectable tests; fictional JWT keys meet the supported HMAC
length. Credential-free startup uses HTTPX ASGITransport with the real lifespan,
avoiding Starlette's deprecated TestClient compatibility fallback. The React Hook Form description subscription uses `useWatch` instead of
compiler-incompatible `watch`. The two auth navigation warnings remain visible: expiry/logout use full document
navigation to clear in-memory sensitive state. Additional unused-variable warnings
are visible under the expanded correctness checks. Pinned Oxlint replaces unsupported
ESLint 9; rule mapping, compatibility limits and regression checks are documented
in the [dependency review](dependency-review.md).

The one live-provider evaluation stays opt-in (`RUN_SCREENING_EVAL` unset in CI).
Verification strips credentials and blocks external test sockets; demo Python,
Node and browser-origin guards remain enabled. Paid/live provider evaluations
are outside ordinary PR CI and require explicit operator opt-in in the guarded
utility flow. Synthetic scores do not validate real AI quality.

## Secret scan scope

`scripts/check_secrets.py` runs detect-secrets 1.5.0 with default detectors,
credential verification disabled and a fresh detection canary on every run.
It scans the proposed current manifest plus every unique blob reachable from
available local heads, remote-tracking refs, tags and HEAD. In CI, checkout uses
`fetch-depth: 0`; HEAD includes the PR merge changes. GitHub does not fetch every
possible server-side PR/ref. Local Codex capture/checkpoint refs are intentionally
outside publication scope; earlier A/B evidence found private artifacts in them.
Do not mirror those refs. Remote issue attachments, release assets, unavailable
refs, LFS content not present locally and credential validity are not inspected.

DOCX XML and metadata, PDF text/metadata and PNG textual metadata are extracted.
Images require human review; text extraction cannot certify hidden content or
personal-data provenance. Unreadable binaries fail. Stage D's two screenshots
were visually rechecked: fictional analytics, no browser chrome/token URLs or
credentials. Four portfolio PDF/DOCX fixtures retain fictional/fixed metadata.
Private uploads, local captures and generated snapshots remain excluded.

Syntactically complete SHA256 lock hashes and npm integrity checksum lines
are filtered. The current source digest is checked against every recomputed file
hash and the exact expected schema before only its hash values are filtered;
paths and other metadata remain scanned. Stale/extra fields fail closed. Historical
digests are independently recomputed from their containing commit and exact schema
before filtering only verified hash fields; unmatched or tampered metadata fails
closed. Historical baseline bytes identical to the current reviewed baseline are
excluded from recursive scanning; other versions remain scanned. Regression tests
verify these boundaries. `security/secrets-baseline.json` contains reviewed fingerprints
bound to the entire normalized file content, detector and secret hash, plus a
reason. Its own hash-only entries are not scanned recursively. Exceptions cover
specific examples/test literals, revision IDs and public action hashes; changing
file content requires renewed review. Reports print locations/categories only.
New unreviewed findings fail. Never regenerate and accept a baseline blindly.

## Updating locks and checks

Runtime dependency inputs are in `backend/requirements.in`; the compatibility
`backend/requirements.txt` delegates to it. Development inputs remain separate.
Use these exact commands; Renovate's header parser requires `--python-version=`:

```powershell
Push-Location backend
uv pip compile requirements.in requirements-dev.in --python-version=3.11 --generate-hashes --output-file=requirements.lock
Pop-Location
uv pip compile security/requirements.in --python-version=3.11 --generate-hashes --output-file=security/requirements.lock
```

`renovate.json` configures `pip-compile` for both `.lock` outputs, npm and GitHub
Actions, with no automatic merging. Both runtime/dev sources are explicit in
the lock header. `scripts/validate_updates.cjs <installed-renovate-package-dir>`
tests real Renovate extraction and hashed-command reconstruction. It was checked
with Renovate 41.132.5 on Node 22 as a local compatibility probe; that older
Renovate version is not a deployed bot or a recommendation for hosting. Installing
or authorizing a maintained Renovate app remains an owner action at publication.
No nominal Dependabot pip configuration that cannot maintain the hashed lock was
added. Hosted update PR creation is untested.

Local workflow validation: `scripts/validate_ci.py` checks tool versions and
safety invariants; `go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.7
.github/workflows/quality.yml` checks syntax/expressions. Neither proves a hosted
Actions run. Recheck all locks, scanners and action pins before publication.
