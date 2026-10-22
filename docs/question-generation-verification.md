# Signup and question-generation verification

Completed 16 October 2026. Read [setup and test instructions](question-generation.md) for the distinction between implemented workflows and unavailable real inference.

## Results

| Area | Result | Evidence |
| --- | --- | --- |
| Backend full regression | 324 passed; two public-route inventory assertions required updating; one real-embedding check skipped | [Full run](evidence/question-generation/batch-backend-complete.log) |
| Security rerun after inventory correction | All 24 security tests passed, including the two previously failing cases | [Security rerun](evidence/question-generation/batch-security.log) |
| Unique backend checks overall | 326 passed, 1 skipped across the full run and targeted rerun; overlapping passes are not added twice | Logs above |
| Frontend | 123 passed across 15 files | [Frontend](evidence/question-generation/batch-frontend.log) |
| Database | 120 passed across core, validation/review, assessments, attempts, adaptation, feedback, analytics and evaluation | [Database](evidence/question-generation/batch-database.log) |
| Migration runner | 7 passed | [Migrations](evidence/question-generation/batch-migrations.log) |
| General browser journey | 55 passed | [Browser](evidence/question-generation/batch-browser.log) |
| Classroom browser journey | 14 passed | [Classroom](evidence/question-generation/batch-classroom.log) |
| Final production build | Passed | [Build](evidence/question-generation/batch-build-final.log) |
| Lint | Backend and new AI launcher passed Ruff | Checked locally |

The first browser pass found an ambiguous automated locator matching both the confirmation-password input and its Show button. The locator was made exact, and all browser journeys then passed. The final change styled the signup role selector; the build passed again, and native desktop/mobile screenshots plus an overflow check confirmed that change. Behavioral suites were not repeated for that styling-only change.

The public-route assertion updates reflect the deliberately added public teacher signup endpoint. Other protected routes continue to reject missing/invalid authentication before database access. Teacher signup is tested against existing-student promotion, arbitrary role input, student-route access and direct role-table write permissions.

## What was exercised

- New teacher signup through the real browser/API, common login, correct dashboard and isolated roles.
- Every count from 10 to 30 is offered. Automated frontend cases exercise both 10 and 30 sequential items, ordered indexing → generation → verification → validation, and recovery after a verifier failure without regenerating the saved draft. These cases use synthetic inference responses.
- A disposable database test exercises a 10-item batch, RAG SQL with synthetic vectors, distinct seeds, saved metadata, idempotent retries, duplicate rejection and cross-account denial. It does not measure model quality.
- The reported four-page scanned PDF successfully uploads and exposes persisted OCR text and page provenance.
- Classroom publication uses synthetic approved question fixtures. Joining, saving/submitting answers, retrying lost responses, recorded analytics, student feedback, confirmed-defect quarantine and access restrictions pass. No real student study or real AI approval evidence is implied.
- Low-memory guards prevent embedding/model startup; no cloud fallback or model download is hidden in the launchers.

## Native deployment

The earlier automatic-approval service failure was resolved on retry. Migration 013 adds only the teacher registration function; matching runtime grants were applied. Existing accounts, materials and records were retained. The database then reported healthy schema, pgvector, runtime role and authentication permissions. The website was restarted at `http://localhost:5173` in **mock mode**. A final native check verified the public signup screen and API readiness without creating a user.

## What remains unverified

Real generator/verifier weights are **not installed**, and no real LLM inference ran. The latest memory reading during verification was 0.42 GiB free out of 7.77 GiB usable. The app requires at least 1.5 GiB free before LLM inference; this threshold alone does not establish practical quality or speed. Real semantic embeddings were not rerun in this update because of memory constraints; the one corresponding model test was explicitly skipped.

Therefore **usable real MCQ generation is not yet demonstrated on this laptop**. The 10–30 workflow is implemented and tested with synthetic model responses. Mock placeholders remain visibly labelled and blocked from publication/scoring. Exact model selection remains **Hardware-validated model selection: pending**. No paid service, cloud API or large model was introduced.

## Screenshots

- [Final native teacher signup — desktop](images/question-generation/teacher-signup-desktop.png)
- [Final native teacher signup — mobile](images/question-generation/teacher-signup-mobile.png)
- [Question count and honest mock-mode readiness](images/question-generation/question-count-readiness.png)
- [Scanned PDF success](images/question-generation/scanned-pdf-success.png)

The latter two images contain synthetic test accounts. HTML-like names are security fixtures rendered as text, not script execution or real student information.
