# Integrated application verification

Phase 20 connects the delivered modules using real frontend/backend/database interactions. All accounts, documents, approval evidence and scores in these checks are **synthetic test fixtures**. No LLM inference or learner study is involved.

## Two complementary browser journeys

`frontend/tests/e2e.mjs` exercises registration, login, private PDF upload/extraction, source preview, test generation, advisory verification, deterministic validation, immutable editing, rejection, dashboards, assessment authoring, blocked mock publication and account/session failure handling. Set `E2E_LIGHTWEIGHT=1` to skip actual embedding inference. This setting does not bypass a production release gate.

`frontend/tests/integration-e2e.mjs` exercises a teacher/student classroom lifecycle. The isolated fixture seeds explicitly synthetic approved question evidence; the teacher still creates and publishes a new assessment through the actual UI/API. Ordinary mock drafts remain ineligible for publication. The two browser contexts have distinct authenticated sessions.

| Boundary | Integrated assertion |
|---|---|
| Teacher → assessment | Version selection, participant permission and publication produce a reference code |
| Code lifecycle → admission | Replaced code fails; current code admits the permitted student |
| Browser → saved answer | Response is deliberately lost **after** the server commits; retry preserves the same command and revision |
| Backend process → persisted attempt | API process shuts down cleanly and restarts against the same disposable database; pinned options, answer and review flag survive |
| Submission → score | Lost committed submission response retries safely; one attempt is recorded |
| Attempt → analytics | One submitted attempt has exactly its recorded answered-item denominator |
| Failed refresh → UI | A deliberate service error clears stale analytics; a successful retry restores source-derived data |
| Feedback → quarantine | Owner confirmation withholds the defective solution and preserves historical score |
| Quarantine → mastery/analytics/export | Three initial eligible responses become two consistently across all three consumers |
| Assessment closure → admission | No new start or rejoin succeeds after closure |
| Authentication → role navigation | Reload requires login; a student cannot use the teacher evaluation page |
| Browser → network | External requests are blocked in the new journey and the observed external-request list remains empty |

The new journey captures the actual teacher dashboard, student dashboard, assessment player and recorded-result screens at desktop and mobile sizes. Its screenshots are evidence of frontend rendering and integration, not examples of validated AI output.

## Running locally

Use the existing project virtual environment and installed frontend/database test dependencies. No new package or model download is required for this phase. From the project root:

```powershell
$env:MCQ_RUN_DB_TESTS = '1'
$env:MCQ_RUN_MODEL_TESTS = '0'
$env:NODE_OPTIONS = '--max-old-space-size=256'
$env:RAYON_NUM_THREADS = '2'
$env:TEST_PYTHON = (Resolve-Path .venv/Scripts/python.exe).Path
$env:E2E_LIGHTWEIGHT = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests -v -p no:cacheprovider
npm.cmd --prefix frontend test -- --pool=threads --reporter=verbose
npm.cmd --prefix frontend run build
npm.cmd --prefix database/tests test
.\.venv\Scripts\python.exe -m unittest discover -s database/tests -p test_migrate.py -v
node frontend/tests/e2e.mjs
npm.cmd --prefix frontend run test:integration
```

Use a writable workspace temporary directory for `TEMP`, `TMP` and pytest `--basetemp` in restricted environments. Do not reuse a directory containing valuable files as pytest temporary storage. These tests need local loopback connections; a sandbox can block Windows event-loop socket setup even without any internet access. Grant local test connectivity before starting and distinguish a sandbox startup failure from an application failure.

Set `E2E_OUTPUT` to an absolute workspace directory for screenshots and downloads. The default new-journey directory is ignored by source control. Set `E2E_BROWSER` to an already-installed Chrome/Edge executable if necessary. Test services run on dynamically allocated loopback ports and are stopped afterward. Browser and model-heavy checks should run sequentially on this 8 GB laptop; real model checks remain disabled.

## Regression coverage and limits

The backend and SQL suites cover owner-scoped retrieval, malformed/failed extraction, incomplete indexing, transactional generation/review rollback, retry keys, incorrect keys, equivalent math options, stale edits, release checks, expired/revoked access, result embargoes, feedback deduplication and evaluation export scope. See the phase completion record for the current run counts, rather than summing historical phase totals.

The browser lost-response test is deliberately different from a failed server transaction: the write succeeds, its response is withheld, and the browser must safely retry. The restart test cleanly stops only the API process, retaining the database. A test-only stdin command lets Uvicorn finish its lifespan and database cleanup on Windows; the normal application has no shutdown endpoint. This reader is explicitly enabled by `--stdin-shutdown` only in the restart journey, keeping it out of PDF-worker tests. The first forced-stop attempt left the embedded database connection unusable, so forced-kill recovery is not a passing claim. These checks do not establish database crash durability, full-machine recovery or upload-directory recovery. The disposable launcher uses temporary uploads and is not a deployment launcher.

Embedded PostgreSQL/PGlite uses a single connection and explicit role switching. The subsequent [Phase 22 native acceptance](phase-22-completion.md) passed 14 classroom browser checks, native authentication/grants, bounded independent-transaction contention, abrupt database restart, database/PDF restore and prepared local startup. The embedded journey also passed after adapting its fixture for native tests. Whole-machine power-loss recovery, physically disconnected operation and real hardware/model performance remain untested. See the [Phase 21 security report](phase-21-completion.md) for earlier hardening and regression results. Actual AI correctness, independent-checkpoint verification and learning benefit remain **To be evaluated**.
