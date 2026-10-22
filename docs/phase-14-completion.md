# Phase 14 completion record — 12 October 2026

**Phase 14 complete: assessment publication and reference codes.** The core remains free and local. Mock-generated content cannot publish; positive publication tests use synthetic evidence and make no claim about real LLM quality.

## Delivered

- Teacher assessment library and draft editor: owned course, up to 50 current question versions, fixed ordering, one point per item, time/attempt limits, randomization settings and result-release policy.
- Revision-checked saves and idempotent actions. Explicitly confirmed publication reruns release checks and atomically saves publication, an expiring reference code, operation history and audit event.
- Published question versions/settings remain immutable. Teachers can replace/revoke codes, close an assessment and allow/remove registered students. No invitation or message is sent automatically.
- Student code entry checks participant authorization, current role/account, code expiry/revocation, assessment state, attempt allowance and current release evidence. Joining stores admission/course membership and returns metadata only; no answer keys, private documents or attempt is exposed/created.
- Persistent rate limiting, digest-only code storage, bounded collision recovery, repeat-request recovery and safe error messages. A failed code replacement preserves the previously active code.
- Forward migration 007, restricted runtime functions, fixed schema paths and an attempt-insert admission guard for newly managed publications. The guard runs before the older attempt trigger so owner/assessment locks follow publication order. Historical records and scores remain intact.
- Teacher/student navigation, responsive pages, [workflow and setup guide](assessments.md), [phase scope](phase-14-plan.md), updated project/module guides and saved screenshots.

## Verification

| Check | Result |
|---|---|
| Backend regression | 215 passed; one real embedding test intentionally skipped |
| New focused backend tests | 13 passed, included in the regression total |
| Final database tests | 52 schema/upgrade checks + 36 validation/teacher/assessment gate checks passed |
| Migration runner | 7 passed |
| Frontend regression | 84 passed across 11 files |
| Production build | TypeScript/Vite passed |
| Python lint | Ruff passed |
| Browser integration | 48 checks passed with `E2E_LIGHTWEIGHT=1` |
| Visual review | Teacher/student pages inspected at desktop and 390-pixel mobile widths; no horizontal overflow |

The final database and browser runs include the trigger-order correction made after the full backend regression. The initial focused UI run found an ambiguous participant control label; explicit accessible labels fixed it and all nine new frontend tests passed in the full regression. The first added SQL fixture used a password-hash placeholder shorter than the existing schema permits; the fixture was corrected, without weakening the constraint, before the successful final database run. The backend retains the existing Starlette/HTTPX deprecation warning.

Tests cover teacher ownership and role checks, mock blocking, revision conflicts, retry behavior, publication rollback, private student responses, permit/remove/restore access, replacement/revocation/expiry, code collision rollback, persistent guessing limits, immutable publication, admission-required attempt inserts, attempt limits and preservation of historical scores. Browser checks exercise the real local API and disposable database: draft authoring, saved settings/participants, blocked mock publication, navigation persistence and rejected unknown student codes. Successful publication/join paths are covered with synthetic passing evidence in API/SQL tests, not represented as real-model browser results.

## Saved evidence

Workspace `work/` logs: `phase14-backend.log`, `phase14-assessments.log`, `phase14-database-final.log`, `phase14-migrations.log`, `phase14-frontend.log`, `phase14-build-final.log`, `phase14-lint.log` and `phase14-browser.log`.

Actual application screenshots with disposable test accounts:

- [Teacher assessments — desktop](images/phase-14-assessments-desktop.png)
- [Teacher assessments — mobile](images/phase-14-assessments-mobile.png)
- [Student code entry — desktop](images/phase-14-join-assessment-desktop.png)
- [Student code entry — mobile](images/phase-14-join-assessment-mobile.png)

The browser runner stops its temporary services and discards its in-memory database. No production account, retained database, real upload or production environment file was created or modified. No LLM weights were downloaded, no LLM inference ran, and no paid/cloud dependency was introduced. Existing research slides and evaluation claims were not changed.

## Reproduce and continue

Use installed dependencies and a writable TEMP/TMP folder. Run memory-intensive suites sequentially. Backend: `MCQ_RUN_DB_TESTS=1`, `MCQ_RUN_MODEL_TESTS=0`, then `pytest backend/tests -v -p no:cacheprovider` with a fresh basetemp. Database: set `TEST_PYTHON` to the project interpreter, then `npm.cmd --prefix database/tests test`. Frontend: `npm.cmd --prefix frontend test -- --pool=threads`, followed by its build. The verified Node test settings use one configured worker and a 256 MiB heap cap. Browser: `E2E_LIGHTWEIGHT=1`, set a writable `E2E_OUTPUT`, then run `node frontend/tests/e2e.mjs` using installed Chrome/Edge.

Native Windows PostgreSQL/pgvector installation, real database password authentication and multi-connection contention remain unvalidated. PGlite tests use PostgreSQL SQL through an explicitly selected restricted runtime role; they do not establish native deployment or concurrent behavior. Apply all migrations and the new restricted grant script through the trusted operator process before normal native use. **Hardware-validated model selection remains pending.**

Next: **Phase 15 — assessment attempts and scoring**. This must implement start/resume, question/option snapshots, timing, answer submission, scoring and result release. Phase 14 stores these settings and protects admission, but supplies no attempt player or scoring endpoint. No measured model accuracy, latency or learning outcomes are claimed.
