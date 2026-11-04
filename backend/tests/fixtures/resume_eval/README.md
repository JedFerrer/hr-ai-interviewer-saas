# Synthetic resume evaluation fixtures

`cases.jsonl` contains ten hand-crafted fictional scenarios with reserved-domain
identities, resume lines, job requirements and expected parse/skill/score ranges.
`docx/` contains one document per case, generated from those resume lines.
Retain both as fixture inputs. No personal uploads are used as fixtures.

Coverage includes strong and partial fits, role mismatches, seniority, aliases,
skills embedded in experience, overqualification and career changes. Fixture
scores express test expectations, not validated recruiter or hiring judgments.

The old `latest_results.json` was generated live-model output and has been moved
to ignored local development storage. No test or utility consumes it; it is not
a baseline required for clean verification. Historical versions remain in Git.

Ordinary verification uses the locked [quality checks](../../../../docs/quality-checks.md)
and the [fictional portfolio demo](../../../../docs/portfolio-demo.md), without
paid AI or real delivery. The guarded `run_resume_parsing_eval.py` utility is a
separate live-provider benchmark: it requires a fresh runner-owned workspace and
explicit provider opt-in through `run_owned_utility.py`. Outputs must remain
within that owned workspace, never overwrite this fixture directory or existing data.

To extend this pack, add a fictional case and regenerate its DOCX from the case's
`resume_lines` using python-docx in a fresh output directory. Preserve source
provenance and review metadata. Do not turn ordinary CI into a live-provider run
or relax expected ranges merely to make an observed model result pass.
