# Frontend setup

Follow the [ordinary real-provider setup](../docs/real-provider-setup.md) first.
The [guarded fictional demo](../docs/portfolio-demo.md) is an optional preview.
Verified: Windows, Node 22.16.0 and npm 10.9.2. Other platforms are unverified.

Use the locked `npm ci` installation in [quality checks](../docs/quality-checks.md#installation).
In a fresh checkout copy `frontend/.env.example` to `frontend/.env.local` if it
does not already exist. Preserve and review any existing file.

| Setting | Value/purpose |
| --- | --- |
| `BACKEND_INTERNAL_URL` | `http://127.0.0.1:8000`; server-side upstream |
| `PROXY_AUTH_SECRET` | Same separately generated secret as backend; at least 32 characters |
| `PORT` | Optional process setting; default 3000 |

Neither secret nor upstream configuration belongs in a `NEXT_PUBLIC_*` variable.
No AI/email credentials are required in the browser or frontend environment.
Use `http://localhost:3000` consistently for ordinary development; the demo
prints its own loopback origin and allocated ports.

From repository root:

```powershell
npm --prefix frontend run dev
```

For a local production-build check, stop the dev server first:

```powershell
npm --prefix frontend run build
npm --prefix frontend run start
```

Both `dev` and `start` run `server.mjs`, which binds to loopback, strips forged
forwarding headers and proxies `/api/backend/*` using the shared server secret.
Direct `next dev` or `next start` bypasses that implementation. A production
frontend build does not certify a production deployment.

Canonical isolated frontend checks are `python scripts/check.py frontend` from
root with the locked interpreter; see [quality checks](../docs/quality-checks.md)
for the complete command and its fresh-install/build behavior. UI smoke uses
the owned demo and installed Chromium, not an existing candidate database.

- 503 on API requests: missing/short shared secret; compare both server settings.
- 502: backend unavailable or internal URL/port mismatch.
- Login/navigation appears stale: tabs share the session cookie; refresh after
  changing accounts. Full-page logout/expiry navigation deliberately clears state.
- AI/email unavailable: inspect backend configuration or use the demo; the
  frontend does not fabricate successful live-provider results.
- Port occupied: stop your known server or choose coordinated ports. Do not
  kill a process identified only by an old PID.

Runtime behavior and supported limits: [architecture](../docs/architecture.md),
[user guide](../docs/user-guide.md), [data limits](../docs/data-and-ai-limitations.md).
