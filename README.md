# HR Interviewer

An AI-assisted screening **portfolio prototype**: employers create jobs, review
applications and interviews, and make their own candidate decisions. Candidates
apply with a resume and complete a text interview through an invitation link.
The supported evaluation is local, fictional, and credential-free. This is not
a hosted hiring service or a validated hiring assessment.

![Fictional candidate analytics showing two applications and one completed interview](docs/assets/portfolio/analytics-desktop.png)

Synthetic demo, captured in Stage D; no real candidates or live-model results.
See [screenshot provenance and gallery](docs/assets/portfolio/README.md).

## Try the local demo

Start with the [guarded Windows demo](docs/portfolio-demo.md). It creates its own
database, fictional resumes and captured mailbox, uses deterministic AI adapters,
and removes only its own resources when stopped. No API credits or real email
delivery are needed. Installation requires registry access.

- **Employer:** inspect/create a job → copy the application link → review screening
  → inspect transcript and evaluation → shortlist/reject → explicitly notify →
  share/revoke a report, inspect analytics, and invite recruiters.
- **Candidate:** submit a fictional PDF/DOCX → wait for screening or human review
  → follow the captured invitation → complete the interview.

The demo genuinely exercises parsing, routes, authentication, persistence,
permissions and UI transitions. Its fixed scores and replies demonstrate workflow,
not AI quality. Ordinary mode supports DeepSeek, OpenAI and Anthropic configuration
and Resend delivery; live integrations were not verified in this release work.
`ENABLE_TEST_EMAILS` is a duplicate-application bypass that can replace an earlier
application for listed addresses, **not an email-delivery gate**.

## Implementation and documentation

The browser calls `/api/backend/*` on the supplied Next custom server
(`frontend/server.mjs`). That server proxies to FastAPI with authenticated client
identity. FastAPI uses async SQLAlchemy/Alembic, SQLite and private local uploads.
Do not replace the custom server with `next start`.

| Layer | Current implementation |
| --- | --- |
| UI | Next.js 16.4.1 App Router, React 19, TypeScript 5, Tailwind 4, Radix/shadcn components |
| API | FastAPI, Pydantic 2, Uvicorn; exact packages in the hashed Python lock |
| Persistence | SQLAlchemy 2, Alembic, SQLite; local PDF/DOCX uploads |
| Integration | Provider adapters, Resend; deterministic replacements in the owned demo |
| Verified runtime | Windows, Python 3.11.9, Node 22.16.0, npm 10.9.2, uv 0.12.1; one worker |

PostgreSQL, Linux/macOS, multiple workers and hosted real-candidate operation
remain unverified.

- [Backend setup](backend/README.md) and [frontend setup](frontend/README.md)
- [User guide](docs/user-guide.md) and [architecture](docs/architecture.md)
- [Data and AI limitations](docs/data-and-ai-limitations.md)
- [Canonical installation and quality checks](docs/quality-checks.md)
- [Development workflow](docs/development-workflow.md) and [contributor guidance](CONTRIBUTING.md)

## Verification and release status

November 3, 2026 evidence: Stage E recorded **248 backend tests passed, 1 live
provider test skipped**, frontend checks/build and seven Node tests passed,
three SQLite migration paths, HTTP demo, Chromium smoke and source-secret checks
passed locally. The [gallery](docs/assets/portfolio/README.md) records fictional
screenshot provenance. These are dated local results, not hosted CI results.

**Not public-ready.** Hosted GitHub Actions has not run. The
[dependency remediation](docs/dependency-review.md) replaces the affected ESLint
tooling with pinned Oxlint and preserves required lint coverage. The owner selected
the existing repository/history and no private reporting channel. Exact published
refs, provenance review, hosted CI and publication authorization remain open.
See the [publication checklist](docs/release-checklist.md).

Usage follows [RIGHTS.md](RIGHTS.md): clone, configure, build, test, and run an
unmodified local copy solely for portfolio evaluation. No open-source license is
granted. General modification, business/commercial use, hosting and derivative
products require prior written permission. Third-party terms remain applicable. [Security reporting](SECURITY.md) has no configured private channel by owner decision.
