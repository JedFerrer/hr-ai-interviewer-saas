# Ordinary-mode acceptance results

November 4, 2026 (Asia/Manila). This local Windows/SQLite, single-worker test used
a fresh owned database/uploads, fictional accounts and resumes, the supported
frontend proxy, real DeepSeek and real Resend. Demo adapters and cross-provider
fallback were disabled. Existing application data was preserved. These results
do not establish production readiness, hiring validity or complete feature coverage.

## Live evidence

| Area | Observed result |
| --- | --- |
| Accounts/jobs | Browser signup, logout/login and persisted session; job creation/editing and application link; disposable job archive, pause and reactivation availability checks. |
| Applications | PDF and DOCX parsing/screening; human review, approval/invitation and pre-screen rejection; normalized duplicate refused without extra AI/email; protected resume downloads matched fixture bytes. |
| Interviews | Two five-question interviews completed with real AI; 11 saved transcript messages each; saved progress survived reload. Employer transcript/evaluation and candidate comparison viewed. |
| Manual decisions | Shortlist/reject did not send automatically. Undo prevented a queued send. Default shortlist and custom rejection notifications were accepted; cooldown and wrong-status requests caused no extra send. |
| Team/security | Admin invitation, revocation, reissue and recruiter acceptance; recruiter administration denied. Cross-company job/candidate/resume/analytics/stream access denied. |
| Reports/updates | Report generated and viewed, then revoked and unavailable. Candidate update arrived through the authenticated proxy stream. Dashboard/job counts checked against their actual definitions. |

The mailbox owner confirmed receiving/opening the participation invitation and
then asked the assistant to start and finish it with invented answers. The
assistant completed it. This verifies that delegated journey, not independently
authored owner answers. No unrelated inbox content was read.

## AI and email accounting

DeepSeek `deepseek-flash`: **34 external attempts, 34 accepted, zero retries or
failures**; **31,017 input and 3,541 output tokens**. At the official peak list
rates checked that day (USD 0.30/M uncached input and 1.20/M output), the estimate
is **USD 0.0135543**, leaving USD 0.9864457 of the USD 1 authorization. No cache or
off-peak discount is assumed. This is an estimate, not an invoice.
[Official pricing](https://api-docs.deepseek.com/quick_start/pricing/).

A persistent test-only guard reserved USD 0.0133152 before each attempt using
28,000 input and 4,096 output tokens as conservative per-request bounds; serialized
input was limited to 24,000 UTF-8 bytes, output to 4,096 tokens and timeout to 60
seconds. Total reservations were USD 0.4527168, with USD 0.5472832 remaining.
The guard would refuse further calls before either the USD 1 or 100-attempt
limit; calls were disabled after the completed run. SDK retries were zero;
missing/unreliable usage would pause calls.
The application's displayed cost cards were not used to enforce this budget.

Resend: **6 requested, 6 accepted, 6 observed `delivered` events**: two interview
invitations, a default shortlist notification, two team invitations (first revoked,
second accepted), and a custom rejection notification. All actual sends passed
an exact single-recipient test guard; extra To/Cc/Bcc recipients were blocked.
Subjects carried the test label via fictional company/template content. No DNS,
account or sender configuration was changed. Only the participation invitation
has explicit human receipt/opening confirmation. A provider delivery event does
not establish inbox placement or human reading.
[Resend delivery lookup](https://resend.com/docs/api-reference/emails/retrieve-email).

## Fixes and verification

SQLite UTC timestamps without an offset were interpreted as browser-local time,
shifting displayed ages/expiry by eight hours in Manila. A shared date parser now
handles them consistently; explicit offsets remain unchanged. Regression cases
cover Manila, New York and UTC. The team timestamp label now says Created because
reissuing an invitation retains that record's creation time. The empty notification
panel now explicitly refers to status notifications, not all invitation email.

The awaiting-decision KPI was incorrectly labeled as older than 48 hours, and
dashboard comparisons/trends used mismatched or unavailable denominators. Labels
now describe the supplied values; unsupported comparisons were removed. A regression
separates recent undecided interviews from the aged action list and verifies that
completion rate divides by invitations, not applications.

Local canonical results: **278 backend tests passed, 1 opt-in provider test skipped**;
three SQLite migration paths and credential-free startup passed. Frontend lint,
typecheck, **11 Node tests** and production build passed. Canonical lint, HTTP demo,
Chromium smoke, dependency and secret checks passed. Dependency audit reported
zero known advisories for 71 application Python packages, 29 scanner packages and
the npm lock. Source links/manifest/digest and CI configuration were checked.
Existing frontend warnings remain visible: eight unused-symbol warnings and two
intentional full-document auth-navigation warnings. Hosted CI was not run for
these uncommitted changes.

Subsequent commit review: **283 backend tests passed, 1 opt-in provider test
skipped**, including the five new persistence cases below; all three migration
paths and credential-free startup passed. Canonical lint and frontend checks
(11 Node tests, typecheck and production build) passed again. Dependency audits
again found zero advisories. No additional paid calls or emails were made.
The earlier HTTP demo/Chromium results above remain dated acceptance evidence;
they were not repeated during this focused review.

## Coverage limits

- Expiry, hostile parser inputs, concurrent team acceptance/status notification,
  provider-boundary failures, processing retry,
  invitation retry and notification retry/idempotency have deterministic regression
  coverage. External failure injection was not attempted; no paid retry is claimed.
- A subsequent deterministic review closed the interview rollback/concurrency
  gaps using real ASGI routes and services with provider doubles, file-backed
  disposable SQLite, independent request sessions and fresh inspection sessions.
  Five regression cases in `backend/tests/test_interview_integrity.py` passed:
  failed intermediate/final replies leave committed transcript, question index,
  integrity signals, token/cost totals, completion and evaluation state unchanged;
  retry saves each answer once at the correct question. Overlapping starts save
  one opening; overlapping answers and completion save one transition and one
  evaluation. Busy requests return 409; completed interviews refuse further input.
  Previously, serialization queued overlapping answers onto the next question;
  the single-worker guard now rejects overlaps instead. This is deterministic
  persistence evidence, not additional live-provider coverage or request-id
  deduplication. The original live-call and email accounting above is unchanged.
- Live applications used manual review. Auto-all/hybrid routing is covered by
  deterministic tests, not a separate real-provider acceptance journey.
- The funnel's rejected/shortlisted counts use completion time and current status.
  A pre-screen rejection is excluded. An initial assertion expecting both rejection
  types failed; source review established this limit, which is now documented.
  This is not a complete history of all HR decisions.
- Automatic employer completion email has a helper but no application caller.
  Internal notes have no implemented UI. Durable queues, general evaluation retry
  and client request-id deduplication are unavailable.
- OpenAI/Anthropic, hosted deployment, multiple workers, PostgreSQL and other
  operating systems were not verified. Live captures are desktop only; separate
  synthetic browser checks do not establish broad accessibility/responsive support.

## Screenshots and cleanup

The [seven primary screenshots and provenance](assets/real-provider/README.md)
show actual DeepSeek output with invented content. Scores and paste-related
warnings are unchanged. Earlier [synthetic captures](assets/portfolio/README.md)
remain in the optional demo gallery.

The owned services were stopped through authenticated control; their three ports
were verified closed. The owned database, uploads, credentials, tokens, temporary
email evidence and raw logs were removed. Existing database/WAL/SHM hashes were
unchanged; ordinary uploads were excluded from the test copy and all test upload
destinations remained inside the owned runtime. Only sanitized test summaries and
selected screenshots were retained. No commit,
push, deployment or repository visibility change was performed. Usage remains
subject to [RIGHTS.md](../RIGHTS.md).
