# Publication review checklist

**Not public-ready.** Updated November 4, 2026. Local preparation is not permission
to stage, commit, push, change settings, publish or deploy.

The owner selected the existing repository with its history preserved. Usage
follows [RIGHTS.md](../RIGHTS.md). No private reporting channel will be configured;
the actual limitation is described in [SECURITY.md](../SECURITY.md), and contact
selection is not a blocker. Dependency remediation is mandatory, with no exception.

- [ ] Verify the complete selected current source and digest in
  [release/](../release/RELEASE_SOURCE_INVENTORY.md), then review the exact release commit/refs.
- [ ] Run all [canonical checks](quality-checks.md) and a complete clean-source
  rehearsal. Preserve audit failures; check the [dependency review](dependency-review.md).
- [ ] Re-scan selected current files and available publication history. Moves to
  ignored local storage do not remove earlier versions from Git.
- [ ] Complete [third-party provenance review](third-party-inventory.md), including
  remaining UI/template/font evidence. Inspect binary pixels and metadata.
- [ ] Review remote issues, attachments, releases, unavailable refs and any LFS
  content separately. Never mirror capture/checkpoint refs.
- [ ] After a separately authorized commit/push, observe hosted CI for that SHA.
  No hosted pass is claimed. Validate update-bot operation if authorized.
- [ ] Obtain explicit publication authorization naming the existing repository,
  exact SHA/refs and intended visibility/release action. Deployment is separate.

The fictional HTTP/browser demo covers normal proxy workflows, failures, roles,
tenancy, manual notification, protected mailbox and authenticated cleanup. Browser
checks cover interview layout and keyboard reachability at desktop and narrow
sizes. These local checks do not certify hiring validity or general accessibility.
