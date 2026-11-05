# Publication review checklist

**Publication not authorized.** Updated November 4, 2026. Local preparation is not permission
to stage, commit, push, change settings, publish or deploy.

The owner selected the existing repository with its history preserved. Usage
follows [RIGHTS.md](../RIGHTS.md). No private reporting channel will be configured;
the actual limitation is described in [SECURITY.md](../SECURITY.md), and contact
selection is not a blocker. Dependency remediation is mandatory, with no exception.

PR #6 merged at `093545bf6afda2ea8b35faf3966fd68f1de9c8b3`; the owner confirms
CI passed for that merge. This review did not poll CI. Prior clean-source,
application, dependency and screenshot evidence may be reused where exact content
matches; new changes require their own relevant checks and CI for the new SHA.
The checklist below describes publication gates, not a claim that earlier checks
never ran. Review records remain in ignored local storage.

- [ ] Verify the complete selected current source and digest in
  [release/](../release/RELEASE_SOURCE_INVENTORY.md), then review the exact release commit/refs.
- [ ] Reconcile all [canonical checks](quality-checks.md) and clean-source rehearsal
  evidence to the candidate; run checks for changed content or unresolved gaps.
  Preserve audit failures; check the [dependency review](dependency-review.md).
- [ ] Re-scan selected current files and available publication history. Moves to
  ignored local storage do not remove earlier versions from Git.
- [ ] Complete [third-party provenance review](third-party-inventory.md), including
  remaining UI/template/font evidence. Inspect binary pixels and metadata.
- [ ] Review remote issues, attachments, releases, unavailable refs and any LFS
  content separately. Never mirror capture/checkpoint refs.
- [ ] For any follow-up commit, obtain passing hosted CI for its exact SHA.
  The owner-confirmed merge pass above covers only that merge. Validate update-bot
  operation if authorized; hosted update PR creation remains untested.
- [ ] Obtain explicit publication authorization naming the existing repository,
  exact SHA/refs and intended visibility/release action. Deployment is separate.

The fictional HTTP/browser demo covers normal proxy workflows, failures, roles,
tenancy, manual notification, protected mailbox and authenticated cleanup. Browser
checks cover interview layout and keyboard reachability at desktop and narrow
sizes. These local checks do not certify hiring validity or general accessibility.
