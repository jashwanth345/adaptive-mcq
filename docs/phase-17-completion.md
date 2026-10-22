# Phase 17 completion — 13 October 2026

**Phase 17 is complete within the local software scope: student feedback, quarantine and owner review.** No real-model quality, student-study result or calibrated feedback threshold is claimed.

## Delivered

- Completed-attempt reports linked to the exact question version: 11 issue categories including other, optional comments and helpful/poor ratings. Unknown, ongoing and foreign attempts are rejected.
- Repeat-request recovery and deduplication across attempts by student/version/category. Original comments/ratings remain intact. My feedback shows only the student's records and status.
- Owner-only review queue and case details, paginated reports, distinct reporter/exposure counts and configurable priority badges. Students can review their own private practice; classroom-linked review requires the owning teacher role, including after role changes.
- Revision-checked reviewing, dismissal and explicit defect confirmation, with required notes and append-only decision/audit history. Failed writes roll back the whole action.
- Confirmed defects permanently quarantine the exact version, block new use/reapproval and exclude its adaptive evidence. Existing attempts and scores are preserved; defective solutions are withheld and results marked under review.
- Score-review task and acknowledgement with follow-up notes. Already-admitted attempts finishing later reopen that task. Acknowledgement never regrades or restores the version.
- Correction link into existing teacher editing. A new immutable version requires fresh checks and approval. The approval screen explicitly explains why a confirmed defective version cannot be reapproved.
- Migration 010, restricted grants, student/owner routes and navigation, responsive screens, [workflow/API guide](feedback.md), [phase scope](phase-17-plan.md) and updated module documents.

## Verification

| Check | Result |
|---|---|
| Backend regression | 236 passed; one real embedding snapshot test intentionally skipped |
| Final feedback/teacher regression | 21 passed, already included in the 236-test scope |
| Database execution | 106 passed: 54 schema/upgrade, 36 validation/review/publication, 8 attempt/adaptive and 8 feedback checks |
| Migration runner | 7 passed |
| Frontend regression | 100 passed across 13 files |
| TypeScript/production build | Passed |
| Python lint | Ruff passed |
| Real-browser feedback journey | 14 passed |
| Visual review | Student history and owner review inspected at desktop and 390-pixel mobile widths; owner queue inspected on desktop |

The final 21-test API run and final database suite cover the later role-change restriction, confirmed-defect explanation and scoped database helper. The full backend run preceded those final refinements. The 14 browser checks cover start/save/submit, report/rating persistence, duplicate handling, owner review, explicit quarantine, score-review acknowledgement, correction navigation and the student's preserved score/recomputed learning profile. No browser runtime errors or external service requests occurred in the successful journey.

Database tests deliberately inject audit failures to verify rollback of reports, cases, quarantine and decisions. They also verify distinct denominators, private-owner isolation, no direct runtime writes, permanent reapproval blocking, and late-completion reopening. API tests cover role/ownership boundaries, schema rejection, revision conflicts, retry keys, result embargo and score/evidence effects. Frontend tests cover forms, confirmation, retained input/retry keys on failure, empty states and review notes.

The first new test collection had a Python dictionary typo, corrected before the passing runs. Browser startup required restoring sandbox loopback permission after continuation. The initial browser correction-link check exposed incomplete source/report metadata in the synthetic fixture; completing that fixture allowed the full journey to pass. No production validation gate was weakened. The existing Starlette/HTTPX deprecation warning remains.

All positive quality/release records are explicitly synthetic and exist only in disposable test databases. Screenshots are actual application captures with synthetic accounts/content, not results of LLM generation or a learner experiment. Default mock drafts still cannot be approved, published or scored.

## Saved evidence

- [Student feedback history — desktop](images/phase-17-feedback-history-desktop.png)
- [Student feedback history — mobile](images/phase-17-feedback-history-mobile.png)
- [Owner review queue — desktop](images/phase-17-feedback-queue-desktop.png)
- [Confirmed defect and score review — desktop](images/phase-17-feedback-review-desktop.png)
- [Confirmed defect and score review — mobile](images/phase-17-feedback-review-mobile.png)

Workspace `work/` logs: `phase17-backend.log`, `phase17-targeted-final.log`, `phase17-database-final.log`, `phase17-migrations.log`, `phase17-frontend.log`, `phase17-build-final.log`, `phase17-lint-final.log` and `phase17-browser-final.log`.

## Setup and reproduce

Apply migrations through 010 using the trusted local database operator, then [feedback runtime grants](../database/feedback_runtime_grants.sql) after all prior module grants. Native setup remains separate; no retained native database, production account or active environment file was changed here. Configure the optional priority settings in the existing environment file; defaults do not trigger automatic quarantine.

From the project root, run prepared development checks sequentially on the 8 GB laptop:

```powershell
$env:MCQ_RUN_DB_TESTS = '1'
$env:MCQ_RUN_MODEL_TESTS = '0'
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe -m unittest discover -s database/tests -p test_migrate.py -v
.\.venv\Scripts\ruff.exe check backend
npm.cmd --prefix database/tests test
npm.cmd --prefix frontend test -- --pool=threads
npm.cmd --prefix frontend run build
$env:E2E_LIGHTWEIGHT = '1'
node frontend/tests/feedback-e2e.mjs
```

Browser tests need loopback access. If Windows sandbox temporary-directory cleanup is restricted, set `TEMP` and `TMP` to an existing writable project scratch directory. Fixtures stop their temporary services and discard their databases. No model inference is needed for these workflow checks.

## Limits and next phase

The existing stack remains **FREE / OPEN SOURCE**. No paid/cloud service, dependency, model download or automatic AI job was added. Hardware-validated model selection and real quality/learning evaluation remain pending. Review priority thresholds are **to be evaluated**. Feedback does not automatically retrain a model or change prompts.

Native Windows PostgreSQL/pgvector setup, native password authentication and concurrent multi-connection behavior remain unverified by these embedded tests. Automated retroactive regrading, report editing/retraction, notifications and evaluated prompt-rule updates are not implemented. Owner acknowledgement records a review; it does not imply a score correction or a validated resolution of educational impact. The [feedback guide](feedback.md) describes the exact boundaries.

**17 of 24 implementation phases are complete; 7 remain. Next: Phase 18 — analytics.** Native deployment and real-model evaluation remain explicit project gates regardless of phase count. Research slides and experimental claims were not changed.
