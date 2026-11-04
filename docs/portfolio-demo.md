# Local fictional portfolio demo

For the primary installation path with your own credentials, see
[ordinary setup](real-provider-setup.md). This guide is an optional synthetic preview.

This is a local workflow demonstration with invented people and companies.
AI responses and scores are deterministic simulations. Email is captured, never
delivered. It makes no hiring-accuracy, fairness, provider-quality, or email
deliverability claim. The repository is **not public-ready**.

## Prerequisites and installation

Verified: Windows, Python 3.11.9, Node 22.16.0, npm 10.9.2. Use one backend
worker, SQLite, and the supplied Next custom server. Linux/macOS are unverified;
the launcher currently refuses them. Allow several minutes and approximately
1 GB of temporary disk space per run. Windows `robocopy` must be available.

Complete the application installation in
[quality checks](quality-checks.md#installation), the canonical locked workflow.
Then, from repository root in PowerShell:

```powershell
.venv/Scripts/python.exe backend/scripts/run_portfolio_demo.py start portfolio-1
```

Installation needs registry access. The installed demo walkthrough does not need
internet access. Do not create or copy `.env` files for this demo. Use a terminal
without `DATABASE_URL`, provider/model overrides, `NODE_OPTIONS`, `PYTHONPATH`,
or production configuration. The launcher refuses these overrides and strips
inherited credentials, including AI, email and cloud keys.

## Start, status, mailbox and stop

The run identifier is mandatory and accepts 1–48 letters, numbers, `_` or `-`.
Choose a fresh identifier for a new run. Each run gets a separate temporary
directory, migrated database, uploads, fixtures, mailbox, source/build copy,
session secret, proxy secret and ownership token.

```powershell
.venv/Scripts/python.exe backend/scripts/run_portfolio_demo.py start portfolio-1
.venv/Scripts/python.exe backend/scripts/run_portfolio_demo.py status portfolio-1
.venv/Scripts/python.exe backend/scripts/run_portfolio_demo.py stop portfolio-1
```

Start prints the dashboard URL, mailbox URL, fixture directory and local
`credentials.txt` location. Open that file privately to obtain mailbox access.
The mailbox uses HTTP Basic authentication: username `portfolio` and the random
password in that file. Enter it in the browser's authentication prompt. Do not
put credentials into shared URLs or screenshots. Neither mailbox content nor
runtime state belongs in the public repository.

Fictional application accounts (all use `PortfolioDemo123!`):

| Company | Administrator | Recruiter |
| --- | --- | --- |
| Fictional Orchard Studio | admin@example.com | recruiter@example.com |
| Fictional Harbor Workshop | admin@example.org | recruiter@example.org |

Optional fixed ports:

```powershell
.venv/Scripts/python.exe backend/scripts/run_portfolio_demo.py start portfolio-2 --ui-port 3100 --api-port 8100 --mailbox-port 9100
```

All three services bind to `127.0.0.1`. Readiness verifies the API, frontend and
proxied connection, including per-run cryptographic identity proofs. API traffic
must use the frontend's `/api/backend` proxy. Uvicorn runs with forwarded-header
trust disabled; the shared proxy secret stays on the servers.

Stop authenticates the live supervisor. The supervisor terminates only children
it started, using retained process handles and a Windows job object, then checks
paths and removes the run. A saved PID is never used as termination authority.
Repeated stop after successful cleanup is safe. Do not manually kill processes
by numbers copied from old logs.

## Walkthrough

1. Sign in as `admin@example.com`. Open the seeded Python Backend Engineer job,
   or create a new job with Python, FastAPI and SQL requirements. Copy its
   application link.
2. Open the application and submit Avery Example / `avery@example.com` with
   `strong.pdf` from the printed fixture directory. The real parser extracts
   the document; the synthetic scorer produces 92/100 and an interview invite.
3. Submit Riley Sample / `riley@example.com` with `review.docx`. The score is
   35/100 and the candidate waits for human review. Low scores are not automatically
   rejected. Use **Reject (pre-screen)** to demonstrate the HR decision.
4. Open the protected mailbox and follow Avery's **Open invitation** link.
   Complete the four-question interview with distinct, concrete fictional
   answers. The existing short/repetitive-answer guards still operate. Inspect
   the employer's saved transcript and synthetic 8/10 evaluation.
   Desktop and 390-pixel interview views have a separate demo disclosure, readable
   progress and reachable response controls; see the gallery's pre-G evidence.
5. Shortlist Avery. Verify there is no new status email. Choose **Notify
   candidate**, select Shortlist, and send. The UI allows ten seconds to undo;
   after that the mailbox captures the delivery. Rejection likewise does not
   send status email automatically.
6. Generate a report using **Share Report**, view it, revoke it, then reload
   the report. Keep the generated-link dialog open until revoking: closing it
   forgets the displayed link and its revoke control. The report includes the
   transcript and evaluation; it should show **Link unavailable** after revocation.
7. In Settings → Team & invites, invite `teammate@example.com`. Follow the
   captured link and create a fictional account. It joins as a recruiter and
   cannot administer invitations. Browser tabs share the login cookie, so
   refresh other tabs after switching accounts.
8. View analytics, update the job, and sign into `admin@example.org`. The second
   company has its own empty pipeline and cannot open the first company's job
   or candidate records.
9. Stop the named run. Its database, mailbox, uploads, copied dependencies and
   runtime files are removed; ordinary development data stays untouched.

## Controlled failures and recovery

These controls require the authenticated supervisor and are not normal API
endpoints or browser/request flags:

```powershell
.venv/Scripts/python.exe backend/scripts/run_portfolio_demo.py fail-processing portfolio-1
.venv/Scripts/python.exe backend/scripts/run_portfolio_demo.py fail-email portfolio-1
```

`fail-processing` fails the next synthetic AI operation once. Arm it just before
submitting a resume; open the failed candidate and use **Retry processing**.
`fail-email` makes the next captured email attempt return failure once. For an
interview invite, use **Retry invitation** on the prepared candidate. For a
status email, use **Notify candidate** again after the failed delivery. A failed
team invite is revoked by the normal route; send a new invitation. Do one
scenario at a time so a different operation does not consume the one-shot flag.

Startup has bounded copy, migration, seed, build and readiness steps. Failures
report a sanitized preparation phase and remove owned resources when ownership
remains valid. Check Python/Node versions, installed dependencies, available disk
space and unused ports. A stop during supervised preparation cancels that work.

Missing/tampered ownership, redirected paths or an unavailable supervisor cause
refusal rather than guessed termination or recursive deletion. A machine crash
can leave a run directory requiring local inspection; automatic stale-run
recovery is intentionally not provided. The Windows job stops attached children
when the supervisor exits, but this does not provide durable application tasks.

## Adapter and isolation boundary

| Boundary | Demo behavior |
| --- | --- |
| PDF/DOCX extraction | Real stage C isolated parser and resource limits |
| Structured resume parsing | Recognizes the two documented fictional resumes after extraction |
| Resume screening | Fixed 92/35 scores; real skill evidence and routing policies remain |
| JD/resume questions, answer assessment, interview replies | Deterministic provider responses; real controller, quality guards and transcript writes |
| Final evaluation | Clearly labeled fixed synthetic evaluation, zero provider usage |
| Interview, completion, status and team email | Reserved-domain-only local capture; no Resend call |
| Unknown AI operation / synchronous legacy provider call | Refused; no live fallback |

Activation requires server configuration plus the existing owned-workspace
proof. Production rejects activation. Requests, uploaded text, cookies and
browser storage cannot turn it on. Real provider behavior is retained with demo
mode off. Legacy seed/stress tools are not used by this demo; HTTP stress tools
remain disabled.

Python and Node runtime guards deny non-loopback TCP/UDP and external DNS via
the covered standard networking APIs. Browser CSP restricts resources and
connections to the local origin; the external font stylesheet was removed.
The demo-only banner exposes resource **origins and counts**, never full URLs,
in `data-resource-origins`, `data-resource-count` and `data-blocked-requests`
attributes for browser inspection. The mailbox escapes content and only makes
expected local interview/team links clickable.

This is defense in depth for trusted application code, not an OS firewall or
a sandbox for malicious local programs/native extensions. Same-user access to
the private run directory is trusted. Dependency installation and build tooling
are separate from runtime network isolation. Do not expose these services on a
public interface or use real resumes in this demonstration.

## Reproduce verification

```powershell
.venv/Scripts/python.exe backend/scripts/verify_release_baseline.py
.venv/Scripts/python.exe backend/scripts/verify_release_baseline.py --tests
.venv/Scripts/python.exe backend/scripts/verify_portfolio_demo.py
```

The last command performs isolated frontend lint/typecheck/tests, production
startup, real proxy workflows, failure recovery, role/tenant checks, protected
mailbox and log checks, concurrent-run isolation, port conflict, startup failure,
repeated stop and cleanup. Existing database files are compared by hash without
opening their application records. This automation complements the browser
walkthrough; it is not a substitute for UI acceptance.

The HTTP verifier checks the workflow, failure recovery and owned cleanup described above.
Sanitized fictional layout evidence: [desktop](assets/portfolio/analytics-desktop.png)
and [390-pixel narrow screen](assets/portfolio/analytics-narrow.png).

Stage E adds a real Chromium UI journey via `scripts/check.py browser`.
It complements this manual walkthrough and the broader HTTP verifier.
See [quality checks](quality-checks.md) for installation, cleanup and CI scope.
