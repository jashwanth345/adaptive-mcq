# Phases 15 and 16 completion — 13 October 2026

**Both requested phases are complete within the local implementation scope.** Phase 15 delivers assessment attempts and server-side grading. Phase 16 delivers reproducible topic profiles and a bounded adaptive-practice policy. These are software workflow results, not measured AI accuracy or educational effectiveness.

## Delivered together

- Start/resume an authorized classroom assessment. Preserve question versions, points, shuffled question order, shuffled options and server deadline across sessions. Enforce attempt limits and current admission for new starts.
- Choose/clear answers, navigate, flag questions and explicitly save progress. Revision checks prevent silently overwriting another tab; retained request keys make retries safe. Unsaved changes are labelled and must be saved before submission.
- Confirm submission and grade from immutable server keys. Repeated submissions return the existing result without adding scores or learner evidence. Late requests grade only previously saved choices. Unexpected failures roll back the grading transaction.
- Release results immediately or after teacher closure. Scores, correct answers, explanations, source excerpts and related learning evidence remain absent while embargoed. Quarantined solutions are withheld; original scores remain visible as under review when released.
- Start an eligible owned private question through categorical automatic evidence. This path requires real passing verifier/validation reports and never turns a test-generated draft into scored content. Classroom publication still requires teacher approval.
- Derive topic profiles from retained first-exposure responses. Exclude skips, expired attempts, repeats, withheld results and quarantined questions. Expose coverage and an explicitly provisional performance index; display **Insufficient evidence** when coverage is missing.
- Use declared priors, decay and evidence thresholds to move difficulty by at most one level per eligible response. Recommend an unseen eligible private item, or honestly report an empty bank. Fixed classroom tests never adapt.
- Add student attempt/result and My learning pages, history/navigation links, migrations 008/009, narrow runtime grants and the [workflow/API/policy guide](attempts-and-adaptive.md).

## Verified evidence

| Check | Result |
|---|---|
| Backend regression | 226 passed; one real embedding snapshot test intentionally skipped |
| Database execution | 97 passed: 53 schema/upgrade, 36 release/review/assessment gates, 8 attempt/adaptive checks |
| Migration runner | 7 passed |
| Frontend regression | 92 passed across 12 files |
| TypeScript and production build | Passed |
| Python lint | Ruff passed |
| Existing browser regression | 48 passed |
| New attempt/learning browser journey | 9 passed |
| Visual review | Attempt and learning pages inspected at desktop and 390-pixel mobile widths; released result inspected on desktop |

The new checks exercise ownership/role isolation, pre-release answer withholding, option mapping, save/resume, revision conflicts, retry behavior, deadline expiry, maximum attempts, post-start code revocation, atomic rollback, private automatic release, mock blocking, duplicate evidence suppression, quarantine exclusion and reproducible adaptive decisions. The browser journey uses the real FastAPI endpoints and disposable PostgreSQL fixture.

Synthetic eligible fixture records exercise the positive release/scoring path. They exist only in disposable test databases and are labelled as synthetic. Their scores and profile percentages demonstrate software behavior, not actual model or student-study results. Normal mock generation remains blocked from release and scored practice.

A policy test initially used an incorrect expected rounded value; it was corrected against the stated formula before the final successful backend run. The migration runner initially encountered Windows sandbox temporary-directory cleanup restrictions; using the project's scratch directory resolved that environment issue and all seven checks passed. Browser startup initially lacked local network access; rerunning with that permission passed. No application security checks were weakened. The backend retains an existing Starlette/HTTPX deprecation warning.

## Saved evidence

Actual application captures with disposable synthetic accounts:

- [Attempt player — desktop](images/phase-15-attempt-desktop.png)
- [Attempt player — mobile](images/phase-15-attempt-mobile.png)
- [Released result — desktop](images/phase-15-results-desktop.png)
- [Learning profile — desktop](images/phase-16-learning-desktop.png)
- [Learning profile — mobile](images/phase-16-learning-mobile.png)

Workspace `work/` logs: `phase15-16-backend.log`, `phase15-16-database.log`, `phase15-16-migrations.log`, `phase15-16-frontend.log`, `phase15-16-build-final.log`, `phase15-16-lint-final.log`, `phase15-16-browser.log`, `phase15-16-browser-final.log` and `phase15-16-regression-browser.log`.

## Local setup and reproduction

Apply all migrations through 009 with the trusted database operator, then `database/attempt_runtime_grants.sql` and `database/adaptive_runtime_grants.sql` after existing module grants. See the [database guide](database.md) and [backend guide](backend.md). The runtime has no direct attempt, answer, score or mastery-evidence writes. No retained native database, production account or production environment file was changed by this work.

From the project root, after the existing development dependencies are prepared:

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
node frontend/tests/e2e.mjs
node frontend/tests/attempt-e2e.mjs
```

Run these sequentially on the 8 GB laptop. Browser checks require local loopback access. In the Windows sandbox, point `TEMP` and `TMP` to an existing writable project scratch directory if the default temporary-directory cleanup is restricted. Browser fixtures stop their services and discard their in-memory databases.

## Explicit limits and handoff

All core components remain **FREE / OPEN SOURCE**. No paid/cloud dependency, model download or LLM inference was added. **Hardware-validated model selection remains pending.** Real generator/verifier quality, independent-model verification and learning benefits are **to be evaluated**. Research slides and experimental claims were not altered.

Native Windows PostgreSQL/pgvector setup, native password authentication and concurrent multi-connection behavior remain to be validated; embedded PostgreSQL tests do not establish those properties. Deadline finalization occurs on the next server interaction, not a background timer job. Private practice currently has one item per session. Topics retain their own context identity, so identically named topics across banks are not merged. Profile replay uses the latest 5,000 eligible responses and considers up to 50 ready private candidates. Detailed policy assumptions, exposure rules and limitations are documented in the workflow guide.

**Roadmap: 16 of 24 implementation phases completed; 8 remain. Next: Phase 17 — student feedback, version reports, quarantine and review.** Native deployment and real-model validation are still explicit project gates, regardless of the software phase count.
