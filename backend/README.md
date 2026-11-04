# Backend setup

Start with the [ordinary real-provider setup](../docs/real-provider-setup.md).
This component reference covers Windows, SQLite and one worker. The
[fictional demo](../docs/portfolio-demo.md) is an optional credential-free preview.

## Install and configure

Follow the locked application installation in [quality checks](../docs/quality-checks.md#installation).
Do not install the unpinned requirements inputs as a substitute for the lock.
Python 3.11.9 is verified; PostgreSQL and other platforms are not.

In a fresh development checkout, copy `backend/.env.example` to `backend/.env`
only if `.env` does not already exist. Review an existing file rather than
overwriting it. The backend reads `.env` relative to its working directory;
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

For fresh files, run `.venv/Scripts/python.exe backend/scripts/setup_local.py`
from root to generate both secrets directly into private environment files. It
refuses to overwrite existing files. Review existing files locally if present.
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

## Checks and troubleshooting

Canonical checks are in [quality checks](../docs/quality-checks.md); backend scope
is `python scripts/check.py backend` from root using the locked interpreter.
This isolates tests, migrations and startup from development data.

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
