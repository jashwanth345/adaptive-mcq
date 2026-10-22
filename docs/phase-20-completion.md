# Phase 20 — integration testing

**Phase 20 is complete within the local software integration scope, 14 October 2026.** Both browser journeys passed. Real-model evaluation and native deployment remain separate pending work.

## Connected workflows

The new classroom journey uses the built React frontend, real FastAPI routes and an isolated embedded PostgreSQL/pgvector fixture. Separate teacher and student browser sessions exercise publication, replacement reference codes, admission, saved answers, a clean API restart, submission, analytics, feedback review, quarantine, mastery and evaluation export.

Save and submission responses are deliberately lost **after their writes commit**. Retrying sends the same command and preserves one submission. Quarantining one of three synthetic items leaves the original score intact, withholds that solution and consistently reduces eligible evidence from three to two in mastery, analytics and study export. These numbers are test expectations, not project evaluation results.

## Changes

- Added `frontend/tests/integration-e2e.mjs` and `npm --prefix frontend run test:integration` with 14 connected checks and desktop/mobile captures.
- Fixed the attempt page retaining an earlier success notice when reloading failed. Starting a reload now clears that notice; an added component test covers success followed by failure.
- Added a **test-only** stdin shutdown command to the browser API launcher, allowing Uvicorn lifespan/database cleanup before a Windows process restart. The production application has no shutdown endpoint.
- Added bounded action/PDF-fixture timeouts to the foundation browser runner so a paused step reports a failure instead of waiting indefinitely.
- Added the [integration guide](integration-testing.md), [current progress report](project-progress.md) and eight real frontend screenshots. No schema, runtime dependency, paid service or model download was added.

## Verification

| Check | Observed result |
|---|---|
| Full backend suite | **264 passed**, one prepared real-embedding test intentionally skipped |
| Full frontend suite before the small notice fix | **114 passed** across 15 files |
| Final attempt-component suite after the fix | **9 passed**, including one added regression; eight overlap with the full frontend run |
| Final production build | Passed |
| Database suite | **119 passed**: 56 schema/migration, 36 validation/publication, 8 attempt/adaptive, 8 feedback, 6 analytics, 5 evaluation |
| Migration runner | **7 passed** |
| Final backend lint and formatting | Passed; 88 backend files formatted |
| New classroom browser journey | **14 passed**, including final loaded-state captures; no browser runtime errors or external requests |
| Existing foundation browser journey | **48 passed** in lightweight mode, including real PDF extraction; no browser runtime errors or external requests |
| Visual inspection | Teacher/student dashboards, assessment player and results inspected at desktop 1440 × 1000 and mobile 390 × 844 viewports; full-page images may be taller |

Test counts describe different suites and overlap; do not add them into an experimental sample size. The existing Starlette/httpx deprecation warning remains. The real-embedding skip avoids fresh model inference in this phase; earlier Phase 9 evidence is separate.

## Issues resolved and limits

The initial forced API stop left the disposable database connection unavailable. The passing restart check uses graceful shutdown and does **not** establish forced-kill recovery. An early browser assertion recorded a URL before navigation completed; the test now waits for the attempt URL. Screenshots initially captured loading placeholders; final captures wait for loaded dashboards and absence of error notices. The foundation runner initially paused and subsequently reported a PDF processing timeout with the new stdin shutdown reader active. Making that reader opt-in with `--stdin-shutdown` only for the restart journey restored the passing PDF workflow; the application PDF timeout and extraction implementation were unchanged. The passing foundation run supersedes those earlier attempts.

All accounts, material snippets, question approvals and scores are explicitly synthetic fixtures. Ordinary mock drafts remain blocked from classroom approval/publication. No local LLM, cloud API, real learner study, independent rating study or model-quality experiment was run. The core remains local and free, with mock/test generation as the default.

Embedded PostgreSQL uses a single connection and role switching. Native PostgreSQL authentication, independent transaction concurrency, database crash durability, persistent upload recovery and prepared offline startup remain deployment work. A successful API restart against a retained test database is not full-machine recovery. Hardware-validated model selection, actual AI quality and learning benefits remain **To be evaluated**.

## Actual frontend images

These are screenshots of the running application, not generated interface concepts. The classroom and results contain synthetic test records.

| Screen | Desktop | Mobile |
|---|---|---|
| Teacher workspace | [Image](images/phase-20-teacher-dashboard-desktop.png) | [Image](images/phase-20-teacher-dashboard-mobile.png) |
| Student workspace | [Image](images/phase-20-student-dashboard-desktop.png) | [Image](images/phase-20-student-dashboard-mobile.png) |
| Assessment player | [Image](images/phase-20-assessment-player-desktop.png) | [Image](images/phase-20-assessment-player-mobile.png) |
| Recorded results | [Image](images/phase-20-assessment-results-desktop.png) | [Image](images/phase-20-assessment-results-mobile.png) |

The mobile student history table scrolls within its panel. No page-wide horizontal overflow was observed in the new journey.

## Roadmap status

**20 of 24 phases complete; four remain:** Phase 21 security hardening, Phase 22 local deployment/offline recovery, Phase 23 documentation, and Phase 24 final evidence/presentation update. This is a count of roadmap phases, not a measured completion percentage. No work in those later phases was started here. Earlier model, native-database and dedicated question-bank-screen deferrals remain explicit in the progress report.
