# Phase 12 completion record — 8 October 2026

**Phase 12 complete within the documented bounded-arithmetic and lexical-duplicate scope.** Delivered lightweight mathematical validation, private duplicate detection and hard release/publication prerequisites. No LLM inference, weights, new runtime package or paid service. Real-model quality and hardware validation remain pending.

## Delivered

- Exact bounded arithmetic with Python's standard library: strict full-stem grammar, independent rational calculation, exactly one matching proposed answer, equivalent-option detection, undefined-operation rejection and resource limits. No eval/exec. Unsupported cases cannot pass.
- Owner-scoped latest-version duplicate comparison: normalized exact stems and token-overlap candidates, 2,000-question scan cap, incomplete-scan blocking and stored corpus freshness fingerprint. No embedding/LLM call or cross-user content exposure.
- Private **Validation workspace** within Draft studio, saved report history/pagination, retry handling, blocker/check details and an unsaved **arithmetic preview**. Reports never approve or publish content.
- Strict authenticated APIs, bounded requests, no-store responses, idempotent retries and atomic report/audit persistence. Shared compute exclusion and owner lock reuse.
- Additive migration 005 and narrow runtime grants. Immutable validation reports remain separate from AI judgments and release records. Database approval/publication checks reject missing/currently failing/stale evidence, mock content, unsupported/failed math, duplicates, superseded or archived questions, archived sources and disabled owners.
- Classroom publication retains owning-teacher approval. Eligible automatic student-practice release follows the original blueprint and cannot satisfy classroom publication. Neither release path is exposed as a new application action in this phase; SQL tests exercise their contracts using synthetic fixtures.
- [Supported scope and setup/API guide](validation.md), [phase plan](phase-12-plan.md) and current project documentation. No earlier migration was edited.

## Verification evidence

| Check | Observed result |
|---|---|
| Initial focused backend suite | 53 passed |
| Database checks | 50 baseline/upgrade checks + 20 Phase 12 release-gate checks passed |
| Migration runner | 7 passed |
| Frontend suite | 68 passed across nine files; all six validation tests reran successfully after final wording changes |
| Production frontend build | Final TypeScript/Vite build passed |
| Python lint | Passed |
| Full backend regression | 191 passed; 1 intentionally skipped real embedding-model test |
| Browser integration | 35 passed with `E2E_LIGHTWEIGHT=1` |
| Visual inspection | Desktop and mobile validation results inspected; no horizontal overflow in the browser checks |
| Actual model quality / inference benchmark | Not run |

Arithmetic fixtures include decimal exactness, negative powers, parentheses, no matching option, wrong key, equivalent numeric options, rounding mismatch, division by zero, unsupported prose/units/functions and oversized or adversarial expressions. These are correctness tests of the narrow calculator, not MCQ answerability research results.

API checks cover ownership, anonymous access, client-verdict injection rejection, request caps, retry key reuse/conflict, history pagination, duplicate discovery after a second draft, unsaved math preview, rollback of a report when the audit write fails and no release-write privileges. Synthetic generator/verifier responses test technical readiness separately from model quality.

SQL tests cover valid and invalid evidence paths, missing/wrong-version AI reports, wrong blind answer, failed/incomplete duplicates, unsupported math, stale corpus, later failed validation, later AI rejection, ownership/reviewer rules, immutable reports, new edits, archived sources, disabled teachers and the automatic-practice/classroom distinction. Historical synthetic attempt scores survive migration; quarantine remains possible. Existing historical schema fixtures run through version 004 and then test upgrade/replay to 005. Dedicated Phase 12 tests start from the full fresh schema.

An initial new SQL fixture used an invalid short placeholder password hash; it was corrected to meet existing constraints. During review, the first all-suite run was stopped to preserve the blueprint's automatic private-practice release path alongside classroom teacher approval. That interrupted run is not counted as a completed regression. Synthetic legacy dashboard fixtures were extended with required evidence without weakening production checks. The first browser run reached the new validation/math flows, then its old screenshot selector matched both panels; the selector was made explicit and the complete 35-check rerun passed.

## Evidence and reproduction

Workspace logs: `phase12-backend-targeted.log`, `phase12-backend-verified.log`, `phase12-schema-verified.log`, `phase12-migrations.log`, `phase12-frontend.log`, `phase12-frontend-final.log`, `phase12-build-final.log`, `phase12-lint-final.log` and `phase12-browser-final.log`. The full regression emitted one existing Starlette/HTTPX deprecation warning.

Browser evidence includes a private blocked validation report, persisted history after navigation, an exact arithmetic pass, failure for equivalent numeric options, existing student/teacher workflows, responsive layout and no external browser dependencies/runtime errors. Test services were stopped by the runner. Actual synthetic application screenshots: [desktop](images/phase-12-validation-desktop.png) and [mobile](images/phase-12-validation-mobile.png). These are development fixtures, not experimental results.

From the project root with installed local dependencies:

```powershell
$env:TEST_PYTHON=(Resolve-Path .venv/Scripts/python.exe).Path
npm.cmd --prefix database/tests test
.\.venv\Scripts\python.exe -m unittest discover -s database/tests -p test_migrate.py
$env:MCQ_RUN_DB_TESTS='1'
$env:MCQ_RUN_MODEL_TESTS='0'
.\.venv\Scripts\python.exe -m pytest backend/tests -v -p no:cacheprovider
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
$env:E2E_LIGHTWEIGHT='1'
npm.cmd --prefix frontend run test:e2e
```

Run memory-consuming suites sequentially. Use a fresh writable workspace TEMP/TMP and pytest basetemp if the shell restricts its default temporary folders. Browser tests need an installed compatible browser and local loopback connections. No model loading is required; existing small tokenizer assets serve prompt-contract tests.

## Limitations and handoff

Math supports only the [documented exact arithmetic grammar](validation.md). Word problems, units, symbolic algebra, rounding policies and broader numerical generation remain unsupported/planned. The conceptual-math screen is conservative triage, not a proof of absence of mathematics. Duplicate detection is lexical; the 0.85 token threshold is uncalibrated, semantic paraphrases can be missed and larger corpora are blocked as incomplete. Large-corpus latency and native multi-connection contention remain untested.

Tests use disposable embedded PostgreSQL/pgvector with a restricted runtime role, not native Windows password authentication. Native PostgreSQL/pgvector setup and retained-database migration remain pending. No production `.env`, account, user upload or retained database was created/modified by this phase. Historical already-published data is preserved by migration; future assessment work must handle legacy eligibility and dynamic selection explicitly.

No research accuracy, LLM quality, learning gain or latency result is claimed. No model weights were downloaded. **Hardware-validated model selection: pending.** The existing presentation/paper/viva artifacts were not changed to invent results.

Next: Phase 13 — teacher review, versioned editing and approval. That phase must explicitly bridge current validation/advisory reports to release evidence without fabricating the legacy schema's score fields. No Phase 13 implementation is included here.
