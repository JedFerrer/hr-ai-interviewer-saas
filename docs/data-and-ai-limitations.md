# Data and AI limitations

This portfolio release is for fictional local evaluation. Engineering controls
and tests do not establish legal compliance, hiring validity, fairness or fitness
for unattended employment decisions.

## What is stored and sent

| Data | Current path and boundary |
| --- | --- |
| Employer accounts/company/team | Local DB; password hashes and authentication state; invitation email goes to configured Resend outside demo |
| Candidate name/email, job, resume | Local SQLite records and `uploads/resumes`; files are not encrypted by an application-level storage system |
| Extracted resume and job description | Bounded PDF/DOCX parser, then AI services; configured primary/fallback providers may receive content outside demo |
| Interview answers and evaluation | Saved transcript, scores, rationale and related signals in DB; content is processed by the configured AI chain outside demo |
| Notifications/invitations | Resend outside demo; captured reserved-domain messages in the owned demo mailbox |
| Shared report | Anyone holding its valid link can read the public report subset until expiry/revocation |
| Runtime logs | Sanitized supported server logs retain route templates, status/timing and safe event identifiers; external logs, build diagnostics and operator captures need separate review |

AI integrations support DeepSeek, OpenAI and Anthropic. Model names and fallback
configuration are in `backend/app/config.py`; configured fallbacks can send data
to another provider. No claim is made about provider retention, residency or
training policy. Review those separately before any real-data use. Missing keys
do not transform ordinary mode into deterministic demo mode.

Report responses exclude resume contents, candidate email, internal notes and
integrity details; they expose identity/job/company, evaluation and transcript.
Links are bearer capabilities, not anonymous aggregates. Do not put them in
issues, screenshots or logs. Report revocation marks a token revoked; it does
not erase copies already viewed or retained by recipients.

## Synthetic behavior and human review

The demo's fixture parser adapter recognizes only its documented invented
resumes after real text extraction. Screening is fixed at 92/35, final evaluation
at 8/10, and questions/replies are deterministic. Email is captured locally.
Routes, parsing, persistence, authorization, workflow guards and UI are real.
Screenshots document that experience; they do not test live-model quality.

Review resumes, transcripts and explanations yourself. Scores can be wrong;
integrity indicators are heuristics, not proof of misconduct. Similarity and
behavioral signals can have innocent explanations. No validated accuracy, bias,
accessibility or fairness assessment is claimed, and no automated hiring decision
should be inferred from the demo's outcomes.

## Retention, deletion and recovery

Archiving a job changes its status. It does **not** erase applications, files,
transcripts, evaluations, screening history or reports. There is no complete
candidate-erasure workflow. `ENABLE_TEST_EMAILS` may delete a previous same-job
application for an allowlisted address; this is a testing bypass, not a complete
erasure mechanism or delivery switch. Keep it disabled.

The demo's authenticated stop removes its own runtime directory, including its
DB, uploads and mailbox. That cleanup is not a general development-data deletion
procedure. Do not run reset/export tools against an arbitrary DB. Ordinary
operators would need a reviewed retention/export/deletion design covering files,
related rows, shared links, logs, backups and provider copies before real use.

Background work, pub/sub and locks are in memory and support one worker only.
Crashes can strand processing or interrupt delivery between send and commit.
Visible retry controls address ordinary processing/delivery failures; they do
not guarantee recovery of every crash state or exactly-once email. Limiter
state is local by default, parser limits are per operation, and total concurrency
is not a validated production capacity limit. Backups/restore and durable queues
are not provided by the portfolio launcher.

Before hosted real-candidate operation, separately review candidate notices and
provider destinations, access/retention rules, human oversight, durable recovery,
transport/ingress protections, logging, backups, abuse/cost limits, dependency
maintenance and incident response. [Open publication gates](release-checklist.md)
also remain; source visibility is a separate milestone from service deployment.
