# Backend setup

Start with the [ordinary real-provider setup](../docs/real-provider-setup.md).
This component reference covers Windows, SQLite and one worker. The
[fictional demo](../docs/portfolio-demo.md) is an optional credential-free preview.

## Stack and prerequisites

The API owns employer/job/candidate data, resume screening, text interviews,
evaluations, reports and delivery. The frontend supplies the browser UI and
required proxy; AI and optional email credentials stay on the backend.

| Area | Implementation and responsibility |
| --- | --- |
| HTTP API | FastAPI, Pydantic and Uvicorn; validation, routes and request handling |
| Persistence | Async SQLAlchemy, Alembic and SQLite; records and explicit migrations |
| Documents | PDF/DOCX extraction in a bounded subprocess; private local uploads |
| Integrations | Configured AI provider adapters and optional Resend delivery |
| Request controls | Authentication, tenant/role checks, body limits and rate limiting |

Use the root locked Python environment. [requirements.in](requirements.in)
declares runtime inputs; [requirements.lock](requirements.lock) pins runtime and
development dependencies. Installed adapters do not establish live-provider or
database support beyond the [documented evidence](../docs/real-provider-setup.md).

## Install and configure

Follow the locked application installation in [quality checks](../docs/quality-checks.md#installation).
Do not install the unpinned requirements inputs as a substitute for the lock.
Python 3.11.9 is verified; PostgreSQL and other platforms are not.

For fresh configuration, run `.venv/Scripts/python.exe backend/scripts/setup_local.py`
from repository root after locked installation. It generates both components'
private environment files and secrets, refuses to overwrite either file, and
selects a fresh database filename. Review existing files privately against
[.env.example](.env.example) instead of replacing them.
The backend reads `.env` relative to its working directory;
run it from `backend`. Root `.env.example` is a matching reference, not a second
required file. Shell environment values override file values.

| Configuration | Local development requirement |
| --- | --- |
| `ENVIRONMENT` | `development`; this is not authorization to reset data |
| `DATABASE_URL` | SQLite; select a new filename for first run, e.g. `sqlite+aiosqlite:///./hr_local_fresh.db`; confirm it does not exist |
| `JWT_SECRET_KEY` | Generate a private random value of at least 32 characters; never reuse an example |
| `PROXY_AUTH_SECRET` | Separate random value, at least 32 characters, identical in backend `.env` and frontend `.env.local` |
| `TRUSTED_PROXY_IPS` | `["127.0.0.1","::1"]` for the supplied loopback proxy |
| `APP_URL`, `API_URL`, `ALLOWED_ORIGINS` | Use `http://localhost:3000`, `http://localhost:8000`, and include `http://localhost:3000` respectively |
| Provider keys/model/fallbacks | Optional for startup; needed for real AI operations outside the demo |
| `RESEND_API_KEY`, `FROM_EMAIL` | Optional for startup; required for real delivery outside the demo |
| `REDIS_URL` | Leave blank for this single-worker scope; Redis alone does not make the app multi-worker safe |
| `ENABLE_TEST_EMAILS`, `TEST_EMAILS` | Keep false/empty. Bypass can delete a previous same-job application before re-testing; it does not suppress email |

Cloud storage settings in the template do not enable cloud uploads: the current
application writes local files. Leave them blank for this evaluation scope.

## First run without reset

From repository root, after configuring the new database:

```powershell
Push-Location backend
../.venv/Scripts/python.exe -m alembic upgrade head
../.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers --no-access-log
Pop-Location
```

The server runs until Ctrl+C; `Pop-Location` then returns to root. Start the
[frontend](../frontend/README.md) in a second terminal and use its signup/login UI.
Do not use reset/seed/export utilities for ordinary first run. Their ownership
guards authorize only runner-created temporary targets, never arbitrary existing
development databases. For an existing database, back it up and review migrations
before upgrading: `g7a8b9c0d1e2` revokes all pending legacy team invitations, changes
new invitations to recruiter, and leaves existing members unchanged. Reissue
pending invitations; downgrade does not restore them.

Without provider keys, account/job operations start, but AI-dependent processing
cannot produce real results. Inspect the error state and retry processing after
configuration is corrected. Missing email configuration does not mean delivery
succeeded: prepared interview email has a retry action; failed team delivery
revokes the unusable invitation and returns an error. Use the demo for a complete
credential-free journey.

## Stop and restart

Ctrl+C in the backend's owning terminal stops it; stop the frontend separately.
Ordinary shutdown preserves the database and uploads. The startup command has
no automatic reload. To restart from repository root:

```powershell
Push-Location backend
../.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers --no-access-log
Pop-Location
```

Restart both components after configuration changes. Startup does not create or
migrate tables; review and apply needed migrations separately using the first-run
guidance. Never reset or seed an existing database as a restart step. Stopping
does not provide durable recovery for unfinished background work.

The optional demo has a different lifecycle: use its
[authenticated stop command](../docs/portfolio-demo.md#start-status-mailbox-and-stop)
with the exact run identifier. It removes owned preview resources. Start another
preview with a fresh identifier; do not use saved PIDs to kill unknown processes.

## Responsibilities and request flow

Browser requests pass through the frontend custom server to FastAPI. The proxy
removes `/api/backend` before forwarding, so `/api/backend/jobs` reaches `/jobs`.
[main.py](app/main.py) assembles middleware and mounts the application routers.
Routers validate inputs and access; services implement screening, interviews,
evaluation, reporting and delivery; models and the database layer persist state.

Application processing stores the upload locally, extracts PDF/DOCX text in a
bounded subprocess, and uses the configured AI provider to structure and screen
it. Interview and evaluation services save progress and results. Background
tasks, candidate event streams and operation locks coordinate within one worker;
they do not constitute a durable queue. Redis configuration alone does not make
this multi-worker safe. The optional demo replaces AI/delivery with guarded
synthetic adapters while retaining real extraction and application writes.

Keep HTTP contracts in routers/schemas, business behavior in services, and schema
changes in new Alembic revisions. Preserve tenant/role checks and manual status
notifications. See [architecture](../docs/architecture.md) for authentication,
proxy trust and coordination details, and [data limits](../docs/data-and-ai-limitations.md)
for disclosure and recovery boundaries.

## Source structure

Selective tracked-source map; `app/main.py` determines which routers are mounted.

```text
backend/
├── app/
│   ├── main.py                # Assembly, middleware and mounted routes
│   ├── config.py              # Settings
│   ├── database.py            # Async persistence setup
│   ├── routers/               # HTTP contracts and access checks
│   ├── schemas/               # Request/response models
│   ├── services/              # Screening, interviews, evaluation, delivery
│   ├── models/                # SQLAlchemy entities
│   ├── middleware/            # Body limits and rate limiting
│   ├── utils/                 # Security, storage, parser, locks and events
│   └── demo/                  # Guarded synthetic adapters and runtime
├── alembic/
│   ├── env.py
│   └── versions/              # Preserved migration history
├── scripts/                   # Setup and owned verification utilities
├── tests/
│   ├── eval/
│   └── fixtures/
│       ├── portfolio/
│       ├── resume_eval/
│       └── screening_eval/
├── .env.example
├── alembic.ini
├── requirements.in
├── requirements-dev.in
├── requirements.lock
└── requirements.txt
```

## Checks and troubleshooting

Run from repository root with the locked interpreter after canonical installation:

| Check | Command | Scope |
| --- | --- | --- |
| Backend | `.venv/Scripts/python.exe scripts/check.py backend` | Isolated tests, migrations and credential-free startup |
| Python lint | `.venv/Scripts/python.exe scripts/check.py lint` | Repository Python correctness checks |

See [quality checks](../docs/quality-checks.md) for the shared `demo`, `dependencies`
and `secrets` commands and scanner prerequisites. Dependency findings must be
resolved without exceptions. Tests use isolated targets, not development data.
These commands describe available checks; dated results and their limits remain
in the [provider coverage summary](../docs/real-provider-setup.md#troubleshooting-and-evidence).

### Troubleshooting

- Database/table errors: check cwd and the chosen URL, then apply migrations;
  do not delete the DB to repair an unknown schema.
- Proxy 503/configuration error: both server-side secrets must match and meet
  the minimum length. Restart both servers after configuration changes.
- API unavailable: verify port 8000 and the frontend internal URL. Keep Uvicorn
  forwarded-header trust disabled.
- Resume rejected: PDF/DOCX only, maximum 10 MiB; malformed or parser-limited
  documents may fail asynchronously. Use the supplied fictional fixtures.
- Stuck processing after a crash: no durable recovery queue exists. Inspect
  state; do not promise every stranded operation has an automatic retry.

See [data limits](../docs/data-and-ai-limitations.md) before changing the scope.
Return to the [system overview](../README.md) for screenshots and dated evidence.
Usage follows [RIGHTS.md](../RIGHTS.md); component instructions do not grant
general modification or hosting permission.
