# Development workflow

Read [AGENTS.md](../AGENTS.md), the [source inventory](../release/RELEASE_SOURCE_INVENTORY.md)
before changing this worktree. Existing uncommitted and
untracked feature work is intentional; preserve it. Historical roadmap documents
are not the current setup or release contract.

1. Install with [canonical locked commands](quality-checks.md#installation).
   Use [the demo](portfolio-demo.md) for evaluation or the component guides for
   ordinary development. Do not copy local `.env`, uploads or databases into a
   test environment.
2. Make a focused change. Keep manual status notifications, tenant/role checks,
   custom proxy, owned utility guards and deterministic adapters intact. Add a
   migration for schema changes; do not rewrite applied revisions. Account for
   the pending-invitation transition when testing upgrades.
3. Run the relevant canonical `scripts/check.py` command using locked Python:
   `lint`, `backend`, `frontend`, `demo`, `browser`, `dependencies`, `secrets`.
   The full command list and bounds are in [quality checks](quality-checks.md).
   Backend covers tests plus migrations/startup; frontend covers fresh install,
   lint/typecheck/tests/build. Browser/demo checks own their temporary resources.
4. Review diffs and include sanitized evidence. Documentation-only work needs
   link/file/command review and a fresh source scan; do not repeatedly run every
   costly test without a behavior/configuration reason. Update the proposed
   manifest deliberately when adding a required file.
5. Describe the resulting behavior, test outcomes and remaining limits in the
   PR template. Follow [contributor guidance](../CONTRIBUTING.md) and
   [project rights](../RIGHTS.md); this workflow itself grants no usage permissions.

`scripts/rehearse_release.py` installs and checks a fresh manifest-only copy.
It must report every dependency finding as a failure. No risk
exception is authorized. Do not weaken severity thresholds, guards or tests
to turn a failing gate green. Lock regeneration has one canonical workflow in
[quality checks](quality-checks.md#updating-locks-and-checks).

Keep live-provider evaluation off in ordinary checks. Use synthetic fixtures and
reserved domains; never submit real resumes, paid-provider requests or real email
as incidental test traffic. Do not paste raw logs, cookies, credentials, invitation
links or report URLs into issues or PRs. Use fixed phase labels and redacted
descriptions, then inspect screenshots and document metadata yourself.

## Source and publication boundaries

Documentation review does not authorize commit, push, deployment, visibility
changes or rights decisions. Publication requires review of the selected source,
exact commit/refs and explicit owner authorization; deployment is separate.

Before release preparation, reconcile the source allowlist and digest, relevant
canonical checks and clean-source rehearsal evidence. Follow-up commits need
passing hosted CI for their own SHA. Dependency remediation remains mandatory.
Scan current source and available history; archiving files does not erase commits.
Review [attribution and provenance](third-party-inventory.md), binary pixels and
metadata, and remote issues/attachments/releases, unavailable refs and LFS content
separately. Never mirror capture/checkpoint refs. Hosted dependency-update PR
creation remains untested. Public verification uses the retained source and
[operational metadata](../release/RELEASE_SOURCE_INVENTORY.md), not private records.
