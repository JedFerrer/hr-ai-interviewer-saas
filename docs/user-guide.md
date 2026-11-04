# Fictional evaluation user guide

Start the [owned demo](portfolio-demo.md) and use its fictional accounts and
fixtures. All scores in that mode are simulations. Do not submit real resumes.

## Employer and candidate journey

1. Sign in as a fictional administrator. In Jobs, create a posting with a title,
   description, skills, interview settings and screening policy, or inspect the
   seeded Python Backend Engineer job. The policy supports auto-all, hybrid
   thresholds or manual-all. Thresholds control review/invitation routing, not
   validated hiring suitability. Copy the job's application link.
2. In a separate candidate browser context, open that link, enter a fictional
   name and reserved-domain email, and upload a supplied PDF/DOCX (up to 10 MiB).
   Submit once and wait for processing. Duplicate normalized email/job applications
   are normally refused. A closed/unavailable job is not an invitation to bypass
   the form through an old URL.
3. In the job pipeline, open the candidate to review screening evidence and
   resume. The demo's strong fixture scores 92; the review fixture scores 35.
   A low score enters human review rather than automatically rejecting the person.
   Approve or reject pre-screening explicitly. Approval may prepare an interview
   without successful delivery; check the delivery indicator.
4. Read the interview invitation in the protected local mailbox. Open it in
   the candidate context, start the interview, and provide distinct fictional
   answers. Short/repetitive-answer guards still apply. Resume a valid unfinished
   session through its link; completed sessions are not new interviews.
   Prefer desktop for this walkthrough: the demo banner overlaps the interview
   header, and on narrow screens the composer extends below the first viewport.
5. Return to candidate detail. Inspect the transcript, evaluation, strengths/gaps
   and integrity signals. Demo evaluation is a labeled fixed 8/10. Interpret
   scores and flags with human review; they are not evidence of hiring validity
   or misconduct. Internal notes and comparison views support that review.

## Decisions, notifications and retries

Shortlisting or rejecting changes status but does not automatically send a
status email. Use **Notify candidate**, choose the matching notification and
confirm. A toast offers **10 seconds to undo**: the browser delays the API call
until the timer expires. Undo cancels that queued send; it cannot recall a
message already sent. This is a browser timer, not a durable scheduled job.

The notification panel shows the latest successful kind/time. The server checks
current status and conflicting prior delivery. Explicit confirmation may be
needed for a conflicting resend; a same-kind one-minute cooldown still applies.
A failed delivery is not marked successful and can be retried. No exactly-once
guarantee exists if the process dies between sending and saving the result.

For failed application processing, candidate detail exposes **Retry processing**
after the underlying provider problem is corrected and the saved resume remains
available. **Retry invitation email** resends an already prepared invitation
without regenerating its questions. Missing files or expired links can prevent
retry. These controls do not recover every possible crash-stranded state.

Outside demo mode, Resend configuration controls actual delivery. The misleadingly
named `ENABLE_TEST_EMAILS` only allows replacing an existing same-job application
for configured test addresses; keep it off. It is not an email safety switch.

## Reports, teams and analytics

Use **Share Report → Generate share link** to obtain a read-only report URL.
It exposes candidate name, job/company, evaluation **and transcript**, but not the
resume, email, internal notes or integrity details. Anyone with the valid link
can read it. The URL is displayed once in that dialog; keep it private. Use
**Revoke** while the generated-link dialog is still open, then reload the report
to see **Link unavailable**. The current dialog forgets the link when closed;
it is not a persistent link-management screen. Do not close it before practicing
revocation. Default report lifetime is seven days (`SHARE_LINK_TTL_DAYS`).

In **Settings → Team & invites**, administrators invite a fictional reserved-domain
address and can list/revoke pending invitations. Follow the captured invitation
to create a recruiter account. Recruiters can view team membership and work with
their company's jobs/candidates/reports, but cannot administer invitations or
grant admin rights. Public signup creates a separate company administrator;
it does not join an existing company.

Team invitations expire after seven days and are single-use; revoked or accepted
links cannot create another account. Interview links have a seven-day expiry and
enforce candidate state; rejection or expiry prevents continuing. Report links
are reusable until revoked/expired, not single-use. The role-policy migration
revokes **all pending legacy invitations**, leaves existing users unchanged and
requires administrators to reissue invitations as recruiter invitations.

View job analytics for application/status counts, funnel and available score
summaries. These summarize saved workflow data, not independent measures of hiring
success. Tabs in one browser context share login cookies; refresh after account
switches. The second fictional company demonstrates a separate pipeline.

Archiving a job is a status change, not candidate erasure. To remove the complete
fictional run, use its named authenticated **stop** command in the demo guide.
See [data limits](data-and-ai-limitations.md) and [fictional screenshots](assets/portfolio/README.md).
