# Phase 11 completion record — 8 October 2026

**Private verifier workflow complete under the user's lightweight/local-only instruction.** Actual LLM inference, hardware-validated model selection and research-quality evaluation remain pending. The earlier chat described Phase 11 as complete before final regression/browser verification; those checks have now finished and are recorded below.

## Delivered

- Teacher/student **Verification workspace** inside each owned saved draft: readiness, run/retry, categorical checks, saved report history, pagination and pending checks. Every report keeps publication status **Not approved**.
- Default `VERIFIER_MODE=mock`: schema and exact source-integrity checks without LLM or embedding calls. Reports always say AI quality **Not evaluated**, never claim an AI pass and carry `ai_executed=false`.
- Separate `disabled` and explicit `ollama` modes. The local adapter prepares a blind-answer call without the proposed key/explanation, then a critique call, checks verbatim evidence and model-digest continuity, and derives an advisory recommendation. It has test-double coverage; no actual inference ran.
- Strict structured schemas; authenticated, owner-scoped status/create/history APIs; bounded request bodies and no-store responses; completed-request idempotency; shared single-process compute exclusion; atomic job/report/audit persistence.
- Additive migration **004_verifier_reports.sql**, immutable report constraints and restricted runtime grants. Advisory reports cannot grant publication and remain separate from release-gate verification records. No prior migration was edited.
- [Setup/API guide](verifier.md), default configuration and current readiness documentation. No new runtime dependency, paid API, cloud fallback or model download.

The supported candidate tag is `qwen2.5:0.5b-instruct-q4_K_M` for both roles, because the existing bounded transport and tokenizer support that small checkpoint. This supersedes the earlier unsupported verifier placeholder. Same-checkpoint calls are disclosed and do not establish independent-model verification. **Hardware-validated model selection: pending.** The current test workflow needs no weights or Ollama process.

## Verification evidence

| Check | Observed result |
|---|---|
| Focused backend verifier/generator/API/database checks | 56 passed in the initial focused run |
| Database schema/migration constraints | 49 passed |
| Migration-runner checks | 7 passed |
| Frontend component/API checks | 62 passed across eight files |
| Frontend production build | TypeScript and Vite passed |
| Python lint | Ruff passed |
| Full backend regression | 159 passed; 1 intentionally skipped real embedding-model test |
| Browser integration | 32 passed with `E2E_LIGHTWEIGHT=1`; real API/database, test generation/review, no embedding/LLM inference |
| Visual inspection | Desktop and mobile review captures inspected; readable checks, test labels and unapproved status |
| Actual local verifier inference or quality evaluation | Not run, per the lightweight scope |

Tests cover ownership, report persistence/retry, failed-write rollback, source-hash mismatch, shared compute exclusion, test-draft exclusion from real-AI mode, blind key isolation, strict parsing, sequential stage order, false-source quotation rejection and changed-checkpoint rejection. Synthetic adapter responses exercise PASS/REGENERATE/REJECT without writing approval or release evidence. UI tests cover retry-key retention, private history/pagination, errors, blocked modes, same-checkpoint disclosure and inert model text.

Schema tests exercise real PostgreSQL/pgvector semantics through disposable PGlite: migration replay/upgrade, mock-AI claim rejection, publication prohibition, completed-verify-job requirement, cross-owner links, unreleased-draft requirement and immutable reports. Driver integration uses explicit restricted `SET ROLE`, not native password authentication or multi-connection contention. The rollback test injects a driver failure before report insertion and verifies earlier job writes roll back; native server-error recovery remains to be checked separately.

An initial frontend run failed because a sandbox temporary file was unavailable; its successful rerun used a writable workspace temporary directory. The migration-runner checks likewise passed after moving their temporary files into the workspace. The first quiet full-backend run was interrupted after output appeared stalled; it is not counted as a completed result. The detailed rerun completed with 159 passes and is the authoritative full-suite evidence. It emitted one existing Starlette/HTTPX deprecation warning. No application permissions were weakened to accommodate these test-environment issues.

Logs in the task workspace's `work/` directory: `phase11-backend-targeted.log`, `phase11-backend-verified.log`, `phase11-schema.log`, `phase11-migrations-final.log`, `phase11-frontend-final.log`, `phase11-build.log`, `phase11-lint.log` and `phase11-browser.log`. Fixtures are synthetic development evidence, not MCQ research results.

The browser checks cover student review creation, reopening its saved report after navigation, a separate teacher-owned report, private draft/material isolation, existing authentication/course flows, mobile fit, unavailable-backend handling and absence of external browser dependencies or runtime errors. Temporary fixture services were stopped by the runner. Application screenshots are available as [desktop](images/phase-11-review-desktop.png) and [mobile](images/phase-11-review-mobile.png); all shown question content is explicitly synthetic.

## Reproduce lightweight checks

From the project root, using the installed local dependencies:

```powershell
$env:MCQ_RUN_DB_TESTS='1'
$env:MCQ_RUN_MODEL_TESTS='0'
.\.venv\Scripts\python.exe -m pytest backend/tests -v -p no:cacheprovider
npm.cmd --prefix database/tests test
.\.venv\Scripts\python.exe -m unittest discover -s database/tests -p test_migrate.py
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
$env:E2E_LIGHTWEIGHT='1'
npm.cmd --prefix frontend run test:e2e
```

Run suites sequentially on 8 GB RAM. Where the shell restricts its default temporary directory, point `TEMP`/`TMP` and pytest `--basetemp` to a fresh writable workspace directory. Browser checks need a locally installed compatible browser and loopback connections. Token-budget unit checks use the existing small pinned tokenizer, not LLM weights.

## Remaining boundaries

- Real Ollama inference, measured peak memory/latency, tokenizer parity, model unload behavior and MCQ quality remain unvalidated. No numerical quality claim is supported by these fixtures.
- Native local PostgreSQL/pgvector installation, password authentication and retained-database migration remain deployment prerequisites. This work did not create a production account, `.env` or retained application database.
- Neither test nor AI advisory reports approve/publish questions. Deterministic math checks, broader duplicate detection and hard validation gates belong to Phase 12; teacher review and assessment workflows follow later.
- No durable in-progress queue or cross-restart job recovery; use one backend worker. A completed report can be recovered through private history after navigation.
- The presentation and research/viva artifacts were not changed to claim implementation or experimental results.

Stop at Phase 11. Phase 12 has not been implemented by this work.
