# Current source boundary

Updated November 4, 2026 (Asia/Manila). This is operational verification metadata,
not publication authorization. The owner selected the existing repository and
preserved history. RIGHTS.md remains the adopted policy. No private reporting
channel is being configured; contact selection is not a publication prerequisite.

`RELEASE_SOURCE_FILES.txt` is the sorted, explicit current-source allowlist.
`RELEASE_SOURCE_DIGEST.json` records SHA-256 and size for that selection: UTF-8 text uses LF line endings,
while PDF/DOCX/image bytes remain exact. Format v2 is stable under Git autocrlf;
no other text content is normalized.
The digest accompanies the export; its own bytes are excluded from hashing to avoid recursion.
Run `python scripts/validate_source.py` to check links, paths and digests; use
`--refresh` only after deliberately reviewing changes to the selected files.
The script does not automatically add paths to the manifest or stage anything.

| Retained public material | Purpose |
| --- | --- |
| Backend/frontend application, all migrations, root CLI prototype | Complete source and schema history; guarded provider utilities remain opt-in |
| Tests, synthetic JSONL and twelve DOCX/two PDF fixtures | Reproducible fictional coverage; no historical generated evaluation is a test input |
| Locks, CI, update configuration, scripts and scanner baseline | Clean installation, checks and full available publication-history scanning |
| README/component guides, user guide, architecture, demo and limitations | Current setup, workflow and supported Windows/SQLite/one-worker scope |
| RIGHTS, notices, contributor guidance and AGENTS | Usage policy, third-party provenance and repository instructions |
| Eight fictional screenshots and provenance captions | UI illustration, with stated verification and font-provenance limits |
| release/ metadata | Public verification inputs; no private handoffs or decision packets |

Historical plans, roadmaps, worker handoffs, owner decision packets, publication
proposals and the generated resume-evaluation snapshot are kept under ignored
`.local-dev/`. The historical inventory/digest is preserved there as evidence.
Neither `.local-dev/` nor `.release-work/` is an input to public checks.
Uploads, personal resumes, databases, tokens, environments and runtime captures
remain excluded and were not inspected or copied for this organization.

Moving tracked working files produces unstaged deletions. It does not erase Git
history: earlier plans and results remain reachable in preserved commits.
The secret scanner still scans all available local heads, remote-tracking refs,
tags and HEAD, including historical versions of moved files. Capture/checkpoint
refs remain outside the existing scope and must not be mirrored. Remote assets,
unavailable refs and provenance review require separate publication review.

No staging, commit, push, deployment, remote/settings change or history rewrite
is authorized. Hosted CI, exact published refs, remaining notice/provenance review
and explicit publication authorization are still outstanding. See the
[release checklist](../docs/release-checklist.md).
