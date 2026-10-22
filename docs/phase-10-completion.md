# Phase 10 completion record — 7 October 2026

**Software foundation complete under the user's revised lightweight scope. Actual local LLM inference and hardware-validated model selection remain pending.**

The user authorized Phase 10 and then instructed us not to run a memory-heavy model or download large model weights, and to use a separated mock/test generator so website development could continue. The implementation follows that instruction. This is not a claim that the full assessment platform, dual-model verification or MCQ research evaluation is complete.

## Delivered

- Shared teacher/student **Draft studio**, sidebar navigation and selected-PDF handoff. Topic and requested difficulty/cognitive level, source preview, proposed answer/explanation, page citation, private saved history and pagination work through the real API/database.
- Default `GENERATOR_MODE=mock`: deterministic excerpt questions with visibly labelled placeholder options. This path uses keyword matching and calls neither Ollama nor the embedding worker. It is deliberately not presented as semantic RAG, AI generation or educational-quality MCQs.
- Separate `disabled` and `ollama` modes. Explicit local Ollama adapter with strict structured-output parsing, CPU/context/output/memory limits, bounded HTTP responses, timeout/unload handling and no paid/cloud fallback. Actual inference has not run.
- Owner-scoped status/create/list/read endpoints, 16 KiB request cap, no-store responses, retry idempotency and atomic completed-job/run/question/version/options/source/audit storage. Model/prompt/source provenance is retained without inventing measurements.
- Shared reentrant compute gate with existing RAG. In the future Ollama path, the embedding subprocess exits before generation. No verifier is loaded or called.
- Additive restricted database grants, settings/template updates, read-only hardware reporting, optional explicit runtime/tokenizer setup helpers, [setup guide](generator.md), [hardware record](phase-10-hardware.md) and revised [phase plan](phase-10-plan.md).

The existing migrations, presentation, paper summary and viva artifacts were not changed. No production `.env`, account, database schema deployment or uploaded user PDF was created. Temporary browser/test accounts and documents were discarded. No new paid dependency or cloud service was introduced.

## Verification evidence

| Check | Actual result |
|---|---|
| Backend regression and focused recovery | **143 distinct checks passed**, assembled from the 141 passing checks in the full regression run, the corrected RAG gate-release check and one added atomic-rollback test. Generator checks were also rerun after the final mock update. |
| Real embedding-model regression | **1 intentionally skipped** in Phase 10 to respect the lightweight test direction. Prior Phase 9 real CPU embedding evidence remains in its completion record. |
| Frontend component/API tests | **56 passed** across seven files. |
| Browser integration | **29 passed** with `E2E_LIGHTWEIGHT=1`: real UI, authentication, PDF extraction, PostgreSQL persistence and mock draft workflow; embedding and LLM inference omitted. |
| Production frontend build | Passed TypeScript and Vite build. |
| Python lint | Ruff passed. |
| Visual inspection | Desktop and mobile Draft studio screenshots reviewed; heading/option readability adjusted and browser captures refreshed. |
| Actual generator model/hardware benchmark | **Not run; deferred by the user's instruction.** |

Backend checks cover anonymous access, cross-account isolation, four distinct options, strict answer index, inert untrusted prompt delimiters, actual local tokenizer budget, missing/remote/unsupported model behavior, insufficient memory, response limits, malformed/truncated output, citation mismatch, persistence, pagination, idempotent retries, shared compute exclusion, lack of release/verification privileges and rollback after a simulated source-write failure. Fixtures do not measure LLM quality.

The initial full run stalled and was stopped; a diagnostic rerun completed with one test-only Python 3.12 `RLock.locked()` compatibility failure. The corrected cross-thread acquisition assertion passed in the focused recovery run. No application error was hidden by that correction.

The test-only PGlite socket adapter became protocol-desynchronized when deliberately provoking a server-side foreign-key error. The rollback test therefore injects a SQLAlchemy failure immediately before source insertion, after earlier real writes, and verifies the real transaction removes every draft row and audit event before a same-key retry succeeds. Native server-side error recovery, native password authentication and multi-connection contention remain to be tested on native PostgreSQL. Runtime permissions were not weakened to make tests pass.

Evidence in the task workspace's `work/` directory:

- `phase10-backend-full-b.log`: full regression (141 passed, one subsequently fixed assertion, one intentional skip).
- `phase10-backend-recovery.log`: 21 passing generator/RAG checks, plus the atomic test subsequently repaired separately.
- `phase10-backend-atomic-final.log`: final atomic rollback/retry check passed.
- `phase10-frontend-final.log`: all 56 frontend tests passed.
- `phase10-build-final.log`: final production build.
- `phase10-browser-final.log` and `phase10-browser-verified.log`: 29 browser checks, with the latter verifying the final build and refreshed captures. Intermediate refresh attempts timed out in Python's internal local socketpair before the app started; restoring loopback network permission allowed startup. A subsequent sandbox temporary-storage issue was resolved by placing isolated browser-test uploads in the writable workspace; production upload rules were preserved.
- `phase10-browser/draft-studio-desktop.png` and `draft-studio-mobile.png`: actual application screenshots with clearly labelled synthetic test content.

Portable copies: [desktop preview](images/phase-10-draft-desktop.png) and [mobile preview](images/phase-10-draft-mobile.png).

## Reproduce without model inference

From the project root, with already installed local dependencies:

```powershell
$env:MCQ_RUN_DB_TESTS='1'
$env:MCQ_RUN_MODEL_TESTS='0'
.\.venv\Scripts\python.exe -m pytest backend/tests -q -p no:cacheprovider
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
$env:E2E_LIGHTWEIGHT='1'
npm.cmd --prefix frontend run test:e2e
```

Use a fresh writable `--basetemp` if the shell environment restricts the default temporary directory. Tests run sequentially and do not need Ollama, LLM weights, API credits or a cloud account. The prompt-budget unit test uses the small prepared local tokenizer; if reproducing on another computer, prepare those tokenizer files explicitly as described in the generator guide. Do not enable real-model tests merely to finish website work.

## Remaining boundaries

- **Hardware-validated model selection: pending.** Recorded available RAM was below the conservative inference threshold; no model weights were downloaded and no LLM inference ran. The earlier official runtime package/tokenizer preparation is documented separately, not disguised as a model benchmark.
- Native local PostgreSQL/pgvector setup is still required for a normal persistent user deployment. Embedded disposable tests do not complete that prerequisite.
- Test drafts cannot be published, verified or scored. Future verifier/publication code must explicitly exclude `mode=mock` records and synthetic results from research metrics.
- Independent verification, deterministic math validation, teacher assessment authoring/publishing, reference-code joining, attempts/scoring, feedback, adaptive mastery and formal evaluation remain future phases.
- One synchronous generator operation is supported per backend process. There is no durable in-progress generation queue or cross-restart recovery beyond completed-request idempotency.
- All actual MCQ correctness, difficulty accuracy, distractor quality, model latency, peak inference memory and student-study outcomes remain **To be evaluated**.

Next roadmap phase: **Phase 11 — verifier LLM**, preserving the same separation between test fixtures and real AI execution. No Phase 11 implementation was added here.
