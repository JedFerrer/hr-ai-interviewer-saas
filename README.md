# HR Interviewer

An AI-assisted screening **portfolio prototype**: employers create jobs, review
applications and interviews, and make their own candidate decisions. Candidates
apply with a resume and complete a text interview through an invitation link.
Ordinary local setup uses your own AI provider credentials and optional Resend
email configuration. On November 4, 2026, an isolated ordinary-mode test completed
two fictional interviews with DeepSeek `deepseek-flash`; six Resend messages had
observed delivery events, and the operator confirmed receiving/opening one invitation.
See the [acceptance results and coverage limits](docs/real-provider-acceptance.md).
Other AI providers remain unverified. This is not a hosted
hiring service or a validated hiring assessment.

## Product screenshots

![Dashboard with three fictional applications and two completed interviews](docs/assets/real-provider/dashboard.png)

Fictional candidate data; real DeepSeek responses. Dashboard captured before the
remaining manual decisions; displayed cost is the application's approximate metric.

![Active fictional five-question interview with a real DeepSeek opening](docs/assets/real-provider/interview.png)

Fictional candidate data; real DeepSeek responses.

![Completed evaluation with the original score and paste-related caution](docs/assets/real-provider/evaluation.png)

Fictional candidate data; real DeepSeek responses. The assistant supplied fictional
answers; the model's caution is preserved. These results do not validate hiring decisions.
[Screening, transcript, report, analytics and capture provenance](docs/assets/real-provider/README.md).

## Run locally

Verified scope: Windows, Python 3.11.9, Node 22.16.0, npm 10.9.2, uv 0.12.1,
SQLite and one backend worker. From repository root in PowerShell, for a fresh
environment:

```powershell
py -3.11 -m pip install uv==0.12.1
uv venv .venv --python 3.11.9
uv pip sync backend/requirements.lock --python .venv/Scripts/python.exe --require-hashes
npm --prefix frontend ci --fetch-retries=0
.venv/Scripts/python.exe backend/scripts/setup_local.py
```

Preserve existing environments and work; see [canonical installation](docs/quality-checks.md#installation).
Setup refuses to overwrite either environment file. It generates strong private
session/proxy secrets without printing them, chooses a fresh database filename,
and leaves all provider credentials blank.

Edit `backend/.env` privately: the example selects `LLM_PROVIDER=openai` and
`LLM_MODEL=gpt-4.1-mini`; supply `OPENAI_API_KEY`. Review the
[provider/model table and lifecycle notes](docs/real-provider-setup.md#implemented-providers-and-model-configuration)
for DeepSeek and Anthropic alternatives. Keep `PORTFOLIO_DEMO=false` and
`LLM_FALLBACK_PROVIDERS=`. Do not paste keys into chat or commit environment files.
Ordinary usage sends candidate text to the selected provider and may incur charges.

For email, set `RESEND_API_KEY` and a verified `FROM_EMAIL`; leave both blank
for no delivery. Signup/jobs and copied interview links work without email.
Team invitations require delivery. Status emails are manual; automatic completion
notifications are not wired. [Email behavior and retry limits](docs/real-provider-setup.md#email-optional-configuration-and-actual-behavior)
distinguish API acceptance from receipt.

Start the backend after migrating the selected database:

```powershell
Push-Location backend
../.venv/Scripts/python.exe -m alembic upgrade head
../.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers --no-access-log
Pop-Location
```

In a second terminal at repository root:

```powershell
npm --prefix frontend run dev
```

Open `http://localhost:3000`, sign up, create your first job, copy its application
link and submit a fictional resume. Review screening, approve an interview when
needed, complete it and inspect its transcript/evaluation. No demo seed is needed.
The frontend uses `http://127.0.0.1:8000` internally and the shared server-only
proxy secret. Do not run `next start` directly.

Read the [complete setup, real-mode checks and troubleshooting](docs/real-provider-setup.md)
for provider errors, migrations, storage, email, data disclosure and evidence limits.

## Optional quick preview

Use the [guarded fictional demo](docs/portfolio-demo.md) for a credential-free
preview after locked installation:

```powershell
.venv/Scripts/python.exe backend/scripts/run_portfolio_demo.py start portfolio-1
```

It creates its own database, invented resumes and captured mailbox, uses fixed
synthetic AI responses, and cleans up only its owned resources. It does not prove
live AI quality or email delivery. Stop using the documented authenticated launcher.

The optional [synthetic screenshot gallery](docs/assets/portfolio/README.md)
retains the earlier demo captures with their original provenance.

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

November 4, 2026 acceptance evidence includes real-provider browser/API workflows
and separate deterministic regression checks. The [verification summary](docs/real-provider-acceptance.md)
records exact counts, fixes, delivery evidence and untested flows. These are dated
local results, not hosted CI results.

The public-readiness PR was merged and its deterministic demo and hosted CI
passed, as reported by the owner. That earlier evidence has a separate scope from
the ordinary-mode acceptance run. Current integration status is recorded in the
[setup evidence table](docs/real-provider-setup.md#troubleshooting-and-evidence).
See [dependency remediation](docs/dependency-review.md) and the
[publication checklist](docs/release-checklist.md) for their separate scopes.

Usage follows [RIGHTS.md](RIGHTS.md): clone, configure, build, test, and run an
unmodified local copy solely for portfolio evaluation. No open-source license is
granted. General modification, business/commercial use, hosting and derivative
products require prior written permission. Third-party terms remain applicable. [Security reporting](SECURITY.md) has no configured private channel by owner decision.
