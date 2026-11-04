# Ordinary local setup and integration evidence

Reviewed November 4, 2026 (Asia/Manila). This is a source-visible portfolio
prototype. Ordinary mode uses your paid provider accounts. It is not a
production-readiness, hiring-validity or regulatory-compliance claim.

## Install and start

Use Windows, Python 3.11.9, Node 22.16.0, npm 10.9.2, uv 0.12.1, SQLite and one
backend worker. Other platforms/databases and multiple workers remain unverified.
From repository root, follow the [locked installation](quality-checks.md#installation).
Do not replace an existing Python environment or dependency directory containing
work you need to preserve; use a fresh checkout/environment instead.

```powershell
.venv/Scripts/python.exe backend/scripts/setup_local.py
```

This creates `backend/.env` and `frontend/.env.local`, separate random session
and proxy secrets, and a random fresh database filename. It never prints secrets,
creates a database, seeds records, resets data, or contacts providers. It refuses
if either environment file exists. Review existing files privately against the
examples instead; do not delete them merely to run setup. If creation partially
fails, retain and review the files. Environment files are plaintext local secrets;
keep access private and do not share terminal dumps or screenshots of them.

Edit `backend/.env` privately. Set the provider/model pair and its API key below.
Keep `PORTFOLIO_DEMO=false`, `ENABLE_TEST_EMAILS=false`, `TEST_EMAILS=` and
`LLM_FALLBACK_PROVIDERS=`. The test-email flag can replace previous applications;
it does **not** suppress delivery. Root `.env.example` is a reference only.
Shell variables override files: use a clean terminal and remove stale overrides
without printing their values. Restart both processes after changing settings.

```powershell
Push-Location backend
../.venv/Scripts/python.exe -m alembic upgrade head
../.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers --no-access-log
Pop-Location
```

Alembic migrates the selected database; startup never creates tables implicitly.
Before upgrading an existing database, back it up and review migration effects:
`g7a8b9c0d1e2` revokes pending legacy team invites; reissue them. Never use reset,
seed, export, or demo ownership tooling for ordinary data.

In a second terminal at repository root:

```powershell
npm --prefix frontend run dev
```

Open `http://localhost:3000`. The custom server binds to `127.0.0.1:3000` and
proxies to `http://127.0.0.1:8000`. Use `APP_URL=http://localhost:3000`,
`API_URL=http://localhost:8000`, and allow `http://localhost:3000` in CORS.
`PROXY_AUTH_SECRET` must match in both server environment files; never expose it
through `NEXT_PUBLIC_*`. Do not substitute `next dev` or `next start` for the
provided commands. `start_backend.bat` uses the root locked `.venv` but does not
install dependencies or migrate the database.

Sign up with a fictional employer/company, then create a job using the dashboard.
Copy its application link, submit an invented PDF/DOCX and wait for screening.
Review candidates that are held for human approval. Approve an invitation if
appropriate; the employer detail page provides the prepared interview link even
when email is unavailable. Complete the interview, then review the persisted
transcript and evaluation. Status decisions do not send email automatically:
use **Notify candidate** explicitly. Team invitations require an admin.

## Implemented providers and model configuration

All ordinary async AI stages use the locked OpenAI Python SDK 2.54.0 Chat
Completions interface: extraction-to-JSON, scoring, question generation, opening,
answer assessment, interviewer replies, and final evaluation. The provider name
is validated; unknown names fail instead of selecting another provider.
`LLM_MODEL` now controls the primary model for every async stage.

| Provider | Explicit configuration | Endpoint and limits |
| --- | --- | --- |
| OpenAI | `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4.1-mini`, `OPENAI_API_KEY` | `https://api.openai.com/v1`; JSON object mode for parse/scoring. This existing model is deprecated, with announced shutdown January 14, 2027; account access still needs live verification. |
| DeepSeek | `LLM_PROVIDER=deepseek`, `LLM_MODEL=deepseek-flash`, `DEEPSEEK_API_KEY` | `https://api.deepseek.com`; JSON object mode; explicit non-thinking mode. The old `deepseek-chat` default is replaced with the currently documented Flash model. |
| Anthropic compatibility adapter | `LLM_PROVIDER=anthropic`, `LLM_MODEL=claude-sonnet-4-6`, `ANTHROPIC_API_KEY` | `https://api.anthropic.com/v1/`; prompt-driven JSON, no `json_object` response format. Set `ANTHROPIC_WORKSPACE_ID` for a key not scoped to a workspace. Retired Sonnet 4 default replaced. Native Anthropic Messages is not used. |

DeepSeek `deepseek-flash` passed the scoped local browser journey below on
November 4, 2026. OpenAI and Anthropic are implemented but not live-tested. Other
models are untested and may reject the current temperature/output parameters.
Do not assume reasoning models, Azure, Bedrock, arbitrary compatible endpoints,
or an installed SDK constitute an implemented integration.

Official references checked November 4, 2026:
[OpenAI model and pricing](https://developers.openai.com/api/docs/models/gpt-4.1-mini),
[OpenAI Chat Completions lifecycle](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create),
[DeepSeek models](https://api-docs.deepseek.com/quick_start/pricing/),
[DeepSeek thinking toggle](https://api-docs.deepseek.com/guides/thinking_mode/),
[Anthropic compatibility](https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/openai-sdk),
[Anthropic lifecycle](https://platform.claude.com/docs/en/about-claude/model-deprecations).

Fallback is disabled by default even if other keys exist. Explicitly setting
`LLM_FALLBACK_PROVIDERS=deepseek,anthropic` authorizes retrying the same candidate
content with those providers, in order, on connection/timeout, 429, or 5xx errors.
Each uses its own table default model, never the primary model override. Missing
fallback keys and unknown names fail configuration. 400/401/403/404 errors do not
trigger fallback. Keep the list empty unless you intend that extra disclosure and
spend. No automatic demo fallback exists.

Requests default to a 60-second SDK timeout, zero SDK retries and at most 4096
output tokens. Change `LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES` (0–2), and
`LLM_MAX_OUTPUT_TOKENS` deliberately. Optional `LLM_REQUEST_LIMIT` and
`LLM_MAX_INPUT_BYTES` cap async calls per worker lifetime and serialized message
bytes per call; zero disables each cap. SDK retries are additional attempts, so
use zero retries for a bounded verification. Restart resets the request counter;
these are local verification guards, not an account-wide billing limit.

## Email: optional configuration and actual behavior

Resend Python SDK 2.50.1 is implemented. Configure both `RESEND_API_KEY` and
`FROM_EMAIL` using a sender on a verified domain. Blank either to disable delivery.
The Resend test sender has recipient restrictions; use your verified sender for
approved recipients. See [Python setup](https://resend.com/docs/send-with-python)
and [idempotency](https://resend.com/docs/dashboard/emails/idempotency-keys).

| Flow | Email role and failure behavior |
| --- | --- |
| Signup/login, job creation | No email required; no verification email is sent. |
| Interview invitation | Attempted after questions/interview are persisted. Missing/rejected email leaves a prepared candidate with **Retry invitation email**. Employer can copy the interview link. |
| Completion notification | A helper exists but has no application caller. No automatic employer completion email is currently sent; review the dashboard. This is not an end-to-end implemented notification flow. |
| Shortlist/rejection notification | Explicit **Notify candidate**, with undo delay; success timestamp only after API acceptance. No automatic status email. |
| Team invitation | Delivery required by the flow. Failed delivery revokes the pending token and returns 503; retry creates a new token. |

Async sends avoid blocking the worker. A nonempty Resend response ID is required
for success. Identical payload retries use a hashed idempotency key (Resend's
24-hour window); this is not exactly-once delivery across all crashes or edits.
After an ambiguous timeout, inspect your provider's delivery log before retrying.
Team retries use a new token and may produce a second email; the older token is
revoked. API acceptance and inbox receipt are different evidence. No inbox or
webhook delivery confirmation is implemented, and UI sent timestamps mean API
acceptance only. Localhost invitation links work only on the development machine.

## Data, storage and real-mode checks

PDF/DOCX bytes remain in private local `backend/uploads/resumes` when started
from `backend`. Extraction runs in a bounded subprocess (10 MiB upload, 30 PDF
pages, 100,000 extracted characters). Scans without text need a text-based resume;
there is no OCR integration. Extracted resume text, including any contact details,
is sent to the selected AI provider for structured parsing. Later requests include
structured resume details, job descriptions, interview questions/answers and, for
evaluation, transcript plus timing/paste/tab-switch summaries. Email sends include
recipient addresses, names, job/company information and capability links.

SQLite stores parsed data, state and transcript. No private pre-seeded data,
demo ownership record or runner is needed. Cloud-storage settings do not implement
remote storage; Redis does not make tasks durable or support multiple workers.
See [data limitations](data-and-ai-limitations.md).

Confirm `PORTFOLIO_DEMO=false` in backend configuration and no shell override.
Run the ordinary Uvicorn/custom-server commands, not the demo launcher. There
should be no demo banner or captured mailbox. Missing API keys must fail AI
processing instead of returning fixed scores. Only provider request evidence
establishes real usage; absence of a banner or a passing synthetic test does not.

## Troubleshooting and evidence

- Missing key: configure the selected provider key locally and restart. Startup,
  signup and job creation intentionally work without it.
- 401/403: check account/key permissions and Anthropic workspace selection.
- 400/404/422: check the exact model, retirement status and parameter compatibility;
  the app does not silently switch providers.
- 429: check quota/billing and wait before retrying. Connection/timeout/5xx: check
  connectivity and provider status; retries may incur charges even if a response
  was lost. API responses use fixed safe diagnostics, never raw provider payloads.
- Invalid structured output: parsing fails visibly; scoring can route to human
  review without a score. Do not mistake review routing for successful screening.
- Processing error: use **Retry processing** after correction. Prepared email:
  use **Retry invitation email**, which does not regenerate questions. No durable
  queue exists; a crash can strand work. Failed auto-evaluation leaves no report;
  no general UI evaluation retry is currently implemented.
- Failed interview turn: the uncommitted answer/progress is rolled back. Reload
  saved state before retrying an ambiguous lost response to avoid submitting an
  already accepted answer twice. Overlapping start/answer requests return 409
  while another transition for that interview is running; reload and retry after
  it finishes. A repeated start resumes the saved opening/current question.
  Completed interviews refuse further starts/answers. This is a single-worker
  guard, not cross-worker coordination or client request-id deduplication.
- Proxy 503: check matching strong server-only secrets. Proxy 502: check backend
  port and internal URL. Table errors: check working directory and migrations;
  never delete an existing database to repair an unknown schema.

| Evidence | Status |
| --- | --- |
| Ordinary provider routing, explicit fallback/model selection, failure classes, demo activation guards | Mocked regression coverage; no paid calls |
| Signup/jobs, SQLite migrations, parser and existing route/tenant tests | Canonical isolated backend checks |
| Fictional full browser journey and captured email | Optional demo only; deterministic adapters |
| Live DeepSeek `deepseek-flash`, November 4, 2026 | Two completed fictional interviews plus supporting employer/team/report workflows in the [acceptance run](real-provider-acceptance.md); fallback disabled |
| Live OpenAI and Anthropic journey | Untested; no live-tested date/model claimed |
| Resend, November 4, 2026 | Six requests accepted and six delivered events observed; operator confirmed receipt/opening of one invitation. Other messages have no human confirmation. |

The earlier setup-only DeepSeek run used 17 attempts: 16 accepted and one connection
failure recovered by manual retry. It persisted one completed interview with 11
transcript messages and one evaluation. Returned usage was 15,002 input and 1,726
output tokens, approximately USD 0.0066 at peak list rates (not an invoice; failed
attempt billing was unavailable). Approval capped usage at 40 requests/USD 1.
No fallback or email request occurred. Missing email configuration produced an
honest retry error without regenerating questions. An isolated database/upload
directory was removed after verification; ordinary records were untouched.
This single fictional journey does not establish model quality or hiring validity.

The later, separately authorized [full acceptance run](real-provider-acceptance.md)
used 34 additional attempts and six real emails. Its budget, outcome and coverage
limits are recorded separately; do not combine the earlier run's counts with it.

Live tests remain manual and opt-in, outside CI. Require explicit provider/model,
request and spending approval plus exact email recipients before execution. Use
an isolated ordinary source/runtime copy with fresh database/uploads and invented
data, not an existing development database. Provider invoices are authoritative:
the UI's legacy token/cost totals are approximate, omit some failed/retried work,
and can misattribute fallback usage. They must not enforce a spending budget.
