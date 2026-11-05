# Frontend setup

Follow the [ordinary real-provider setup](../docs/real-provider-setup.md) first.
The [guarded fictional demo](../docs/portfolio-demo.md) is an optional preview.
Verified: Windows, Node 22.16.0 and npm 10.9.2. Other platforms are unverified.

## Stack and prerequisites

The frontend presents employer jobs/candidates, interview and application pages,
reports and team settings. A running backend is required for application behavior.

| Area | Implementation and responsibility |
| --- | --- |
| Pages | Next.js App Router, React, TypeScript; routes and interactive UI |
| UI and forms | Tailwind, Radix/shadcn components, React Hook Form and Zod |
| Server | Custom Node server; serves Next and proxies same-origin API requests |
| Checks | Oxlint, TypeScript, Node contract tests and Playwright Chromium smoke |

See [package.json](package.json) and [package-lock.json](package-lock.json) for
dependency specifications and exact locked versions.

## Install and configure

Use the locked `npm ci` installation in [quality checks](../docs/quality-checks.md#installation).
For fresh ordinary configuration, follow the shared `setup_local.py` step in
the [ordinary setup guide](../docs/real-provider-setup.md#install-and-start).
It creates both components' private environment files and matching proxy secrets,
and refuses to overwrite either file. Preserve existing files and review them
privately against [.env.example](.env.example).

| Setting | Value/purpose |
| --- | --- |
| `BACKEND_INTERNAL_URL` | `http://127.0.0.1:8000`; server-side upstream |
| `PROXY_AUTH_SECRET` | Same separately generated secret as backend; at least 32 characters |
| `PORT` | Optional process setting; default 3000 |

Neither secret nor upstream configuration belongs in a `NEXT_PUBLIC_*` variable.
No AI/email credentials are required in the browser or frontend environment.
Use `http://localhost:3000` consistently for ordinary development; the demo
prints its own loopback origin and allocated ports.

## Start, stop, and restart

From repository root in PowerShell, with the backend running:

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

Ctrl+C in the frontend's terminal stops it; stop the backend separately in its
own terminal. Rerun `npm --prefix frontend run dev` to restart development, or
`npm --prefix frontend run start` for an existing production build. Rebuild after
source changes when inspecting a production build. Restart both components after
configuration changes. Ordinary shutdown preserves the database and uploads.

For the optional demo, use its [authenticated stop command](../docs/portfolio-demo.md#start-status-mailbox-and-stop)
with the exact run identifier. That removes owned preview data; a new preview is
a fresh run, not a restart of ordinary development data.

## Responsibilities and request flow

Pages and components call [the typed API client](src/lib/api.ts), which sends
requests to `/api/backend/*` on the browser's own origin. [server.mjs](server.mjs)
handles that prefix before Next routing, removes `/api/backend`, and forwards
the remaining path to FastAPI at `BACKEND_INTERNAL_URL`. For example,
`/api/backend/jobs` reaches backend `/jobs`; responses return through the same
proxy. Candidate update streams also use this path.

Keep route UI in `src/app`, shared UI in `src/components`, and API/types/session
helpers in `src/lib`. Provider calls, persistence, screening and decisions belong
to the backend. The [architecture guide](../docs/architecture.md) explains
authentication and proxy trust in detail.

## Source structure

Selective tracked-source map; route folders contain their pages and layouts.

```text
frontend/
├── src/
│   ├── app/
│   │   ├── dashboard/
│   │   │   ├── jobs/                # Job creation/editing, candidates, analytics
│   │   │   └── settings/            # Account, email templates, team
│   │   ├── interview/
│   │   │   ├── [token]/             # Application page
│   │   │   └── session/[token]/     # Interview session
│   │   ├── accept-invite/[token]/
│   │   ├── report/[token]/
│   │   ├── login/
│   │   └── signup/
│   ├── components/
│   │   ├── layout/                  # Dashboard shell and navigation
│   │   └── ui/                      # Shared UI primitives
│   └── lib/
│       ├── api.ts                   # Requests and candidate event stream
│       ├── auth.tsx                 # Session UI state
│       ├── types.ts
│       ├── dates.ts
│       └── utils.ts
├── server.mjs                       # Required startup/proxy entrypoint
├── server/                          # Proxy, logging and demo network helpers
├── scripts/lint-compat.mjs
├── tests/                           # Node contracts and Chromium smoke
├── .env.example
├── next.config.ts
├── package.json
└── package-lock.json
```

## Checks

Run from repository root with the locked interpreter after canonical installation:

| Check | Command | Scope |
| --- | --- | --- |
| Frontend | `.venv/Scripts/python.exe scripts/check.py frontend` | Isolated fresh npm install, lint, types, Node tests and production build |
| Browser smoke | `.venv/Scripts/python.exe scripts/check.py browser` | Owned demo journey through Chromium and the custom proxy |

See [quality checks](../docs/quality-checks.md) for Chromium/scanner prerequisites
and shared `demo`, `dependencies` and `secrets` commands. UI smoke uses owned
fictional data, not an existing candidate database. Dependency findings must be
resolved without exceptions. These commands describe available checks; dated
results and their limits remain in the [provider coverage summary](../docs/real-provider-setup.md#troubleshooting-and-evidence).

## Troubleshooting

- 503 on API requests: missing/short shared secret; compare both server settings.
- 502: backend unavailable or internal URL/port mismatch.
- Login/navigation appears stale: tabs share the session cookie; refresh after
  changing accounts. Full-page logout/expiry navigation deliberately clears state.
- AI/email unavailable: inspect backend configuration or use the demo; the
  frontend does not fabricate successful live-provider results.
- Port occupied: stop your known server or choose coordinated ports. Do not
  kill a process identified only by an old PID.

## Related guides and verification limits

Runtime behavior and supported limits: [architecture](../docs/architecture.md),
[user guide](../docs/user-guide.md), [data limits](../docs/data-and-ai-limitations.md).
Return to the [system overview](../README.md) for screenshots and dated evidence.
Usage follows [RIGHTS.md](../RIGHTS.md); component instructions do not grant
general modification or hosting permission.
