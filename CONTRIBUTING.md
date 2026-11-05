# Contributor guidance

Usage follows [RIGHTS.md](RIGHTS.md), matching the reference portfolio project.
Local evaluation of an unmodified copy is permitted; general modification and
redistribution of modified copies require prior written permission. Obtain owner
permission before preparing code contributions. This review process grants no
additional rights and establishes no contributor assignment or agreement.

For authorized work, follow [development workflow](docs/development-workflow.md)
and [AGENTS.md](AGENTS.md). Preserve existing changes, use the locked toolchain,
keep scope focused, and record relevant check results and known failures. The
dependency gate is mandatory for every candidate. The owner confirms CI passed
for PR #6's merge; see the [publication checklist](docs/release-checklist.md) for
the exact SHA and follow-up requirements.

Bug reports should include fictional reproduction steps, expected/actual behavior,
runtime versions and sanitized evidence. Feature requests should explain the
user's problem and whether it belongs to local evaluation or a future hosted
service. PRs should explain behavior changes, tests and data/migration effects.

Never attach credentials, provider keys, personal resumes, cookies, databases,
raw transcripts or token-bearing application/interview/invitation/report URLs.
Use reserved-domain examples and inspect screenshot pixels and metadata.
Do not disclose sensitive vulnerabilities publicly: [SECURITY.md](SECURITY.md)
states the current reporting limitation. No private reporting channel is configured.
