# Resume Parsing + Scoring Eval Pack

End-to-end fixtures, runner, and frontend test flow for verifying that resume parsing and HR-style scoring behave like a real recruiter.

## What's in here

- `cases.jsonl` — 10 hand-crafted scenarios. Each line includes a synthetic job (title, JD, required skills), a synthetic resume (as plain lines), and explicit expectations for parsing, deterministic skill match, LLM score band, and screening decision.
- `docx/` — One `.docx` per case, generated from `resume_lines`. Use these to exercise the real upload pipeline (PDF/DOCX extraction → parser → scorer → screener) end-to-end, exactly like a candidate uploading a resume.
- `latest_results.json` — Most recent eval run snapshot (LLM scores drift slightly between runs; this gives a known-good baseline).

## Case coverage

| Case | What it stresses | Expected decision |
|------|------------------|-------------------|
| `backend_strong_fit` | Senior backend, all skills present | auto_invite |
| `backend_partial_missing_k8s` | 5/6 must-haves, missing K8s but Docker present | auto_invite (softer penalty for adjacent skill) |
| `frontend_strong_fit` | Senior frontend, all skills + aliases (`React.js`) | auto_invite |
| `frontend_to_backend_mismatch` | Strong frontend resume vs senior backend JD | review (heavy penalty) |
| `data_engineer_strong_fit` | Data role, requires `Apache Airflow` alias resolution | auto_invite |
| `junior_backend_vs_senior_job` | 2y junior applying to senior role — seniority cap kicks in | review (score capped ≤50) |
| `overqualified_for_junior_role` | 9y staff engineer applying to junior role | auto_invite (no overqualification penalty) |
| `alias_only_match_devops` | All skills only present as aliases (`k8s`, `nodejs`, `continuous integration`) | auto_invite (alias matcher must work) |
| `hidden_skills_in_highlights` | Skills not in resume `Skills` section, only in experience bullets | auto_invite (deterministic match over highlights) |
| `career_changer_bootcamp` | Bootcamp grad, 1y exp, missing AWS | review (gated by experience + missing must-have) |

These cover: strong fits, partial fits, hard mismatches, seniority misalignment, overqualification, alias normalization, evidence in highlights vs skill list, and career-changer edge cases.

## Backend automated flow

```bash
cd backend
source venv/Scripts/activate

# Run all 10 cases through the live pipeline (LLM call per case)
python scripts/run_resume_parsing_eval.py \
  --use-upload-files \
  --output tests/fixtures/resume_eval/latest_results.json
```

Flags:
- `--use-upload-files` — sends the `.docx` through the real `extract_text_from_bytes` path (the same code that runs on candidate upload). Without this flag, the runner feeds `resume_lines` directly to the parser.
- `--auto-invite-threshold` / `--review-threshold` — override `ScreeningPolicy` thresholds (defaults: 75 / 55).
- `--cases` — point at a different jsonl file.

Expected outcome: **10 / 10 PASS**. The runner exits non-zero on any failure so you can wire it into CI.

What each case asserts:
1. **Parse**: `years_experience` ≥ expected, `current_role`/`current_company` substring match, key skills present in parsed `skills`, ≥ N experience entries.
2. **Deterministic match**: recall in expected range, required matched/missing skills appear.
3. **LLM score**: integer falls inside the band you encoded in the fixture.
4. **Screening decision**: `auto_invite` / `review` / `reject` matches.

Bands are intentionally **wide** (not point-estimates) because LLM output drifts run-to-run. They encode HR-style intent: "this candidate should land in interview", "this candidate should land in human review", etc.

## Frontend manual verification flow

Use this when you want to confirm the same fixtures look right in the UI (resume tab, pre-screen tab, deterministic_match block).

### 1. Boot both services

```bash
# Terminal 1 — backend
cd backend && source venv/Scripts/activate
uvicorn app.main:app --port 8001 --reload

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open `http://localhost:3000` and log in.

### 2. Create one job per case

For each line in `cases.jsonl`, create a job in the dashboard with:
- **Title** ← `job_title`
- **Description** ← `job_description`
- **Required skills** ← `required_skills`

Tip: name the job after the `id` (e.g. `EVAL: backend_partial_missing_k8s`) so it's easy to map back later.

### 3. Upload the matching resume

For each job, open the public apply link (or use HR "Add candidate") and upload the corresponding file from `backend/tests/fixtures/resume_eval/docx/<case_id>.docx`.

Background processing typically completes in ~20–40 seconds.

### 4. Verify the Resume tab against `expected.parse`

For each candidate, check:
- `current_role` contains the expected substring.
- `current_company` contains the expected substring.
- `years_experience` ≥ `years_experience_min`.
- All `skills_should_include` appear in the parsed skills list (case-insensitive).
- At least `experience_min_count` experience entries are rendered.

### 5. Verify the Pre-Screen tab against `expected.score` + `expected.decision`

- Score badge falls in the expected band.
- Decision matches (`auto_invite` shows the green "Invite" path; `review` lands in the review queue).
- `deterministic_match` block is visible and shows:
  - `matched_skills` chips for everything in `deterministic.matched_should_include`.
  - `missing_skills` chips for everything in `deterministic.missing_should_include`.
  - `recall` value within `recall_min`/`recall_max`.
  - Evidence quotes (≤120 chars) attached to matched skills.

### 6. Cross-reference with `latest_results.json`

The backend script writes a JSON summary per case (parsed fields, deterministic report, LLM score, decision). When the UI shows something surprising, diff against `latest_results.json` to isolate whether the regression is in the API, the persistence layer, or the frontend rendering.

## When a case fails

1. **Parse failure** — open the candidate detail page, look at the raw resume text. If extraction is wrong, suspect `extract_text_from_bytes`. If extraction is fine but parsed fields are wrong, suspect the LLM extraction prompt or schema.
2. **Deterministic recall too low** — likely a missing alias in `app/services/skill_matcher.py`. Add the alias, re-run the eval.
3. **LLM score consistently outside the band** — first re-run twice (LLM noise). If it stays outside, decide: tighten the prompt (principled rule, not overfitting) **or** widen the fixture band because the LLM is right and the fixture was overconfident.
4. **Decision mismatch but score is in band** — confirm `ScreeningPolicy` thresholds match what production uses.

## Adding a new case

1. Append a JSON line to `cases.jsonl` with the same shape.
2. Regenerate the docx pack:
   ```bash
   python -c "
   import json
   from pathlib import Path
   from docx import Document
   for line in open('tests/fixtures/resume_eval/cases.jsonl'):
       case = json.loads(line)
       doc = Document()
       for ln in case['resume_lines']:
           doc.add_paragraph(ln)
       doc.save(f\"tests/fixtures/resume_eval/docx/{case['id']}.docx\")
   "
   ```
3. Re-run the eval and iterate until the LLM lands in your expected band on 2–3 consecutive runs.

## Design principles for the fixture bands

- **Wide bands, not point-estimates.** LLMs jitter ±5–10 points. Encode HR intent ("strong fit", "review band", "reject"), not exact scores.
- **Decision matters more than score.** A score of 78 vs 85 is noise; `auto_invite` vs `review` is the user-visible behavior change.
- **Each case stresses one axis.** Don't bundle "missing skill" and "wrong seniority" into one fixture — you won't know which rule caught it.
- **No fixture overfitting.** If the LLM disagrees with you, ask: would a real HR also disagree? If yes, update the fixture, not the prompt.
