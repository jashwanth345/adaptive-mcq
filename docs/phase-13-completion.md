# Phase 13 completion record — 9 October 2026

**Phase 13 complete within the documented conceptual-question editing and teacher-approval scope.** Default mock content remains blocked from approval and publication. No model inference or weights were required.

## Delivered

- Teacher-only review queue with private source inspection, current-version status, editable conceptual fields, review notes, decision confirmation and version history.
- Immutable new versions preserve original generation/source ancestry. Fresh verifier and deterministic reports are required. Mock ancestry remains blocked after editing. Editing quarantines a preceding release without rewriting its content or completed attempt history.
- Explicit rejection requires a corrected new version before reconsideration. Approval binds the teacher decision to the current exact validation/advisory evidence and does not publish an assessment.
- Additive migration 006 bridges categorical evidence to releases without fabricating the legacy seven quality-score fields. Historical legacy releases and the separate student-practice contract are retained.
- Restricted runtime functions, revoked PUBLIC execution, fixed schema paths, owner/version locks, request-key retries and atomic audit/release/content writes. Source links are sealed after advisory or deterministic review.
- New publication gates reject teacher-rejected versions and stale approval evidence. The application receives no direct release writes or assessment publication privileges.
- [Workflow/setup/API guide](teacher-review.md), [phase scope](phase-13-plan.md), updated project entry point and module guides. No new runtime dependency, paid API, cloud service, model download or inference.

## Verification

| Check | Evidence |
|---|---|
| Focused backend | 11 passed |
| Database | 51 schema/upgrade checks + 28 validation/teacher checks passed |
| Migration runner | 7 passed using a writable workspace temporary folder |
| Focused teacher UI | 7 passed; rerun after editor-label and option-letter corrections |
| Production build | Final TypeScript/Vite build passed |
| Full backend regression | 202 passed; 1 intentionally skipped real embedding-model test |
| Full frontend regression | 75 passed across 10 files |
| Python lint | Passed |
| Browser integration | Final 42 checks passed with `E2E_LIGHTWEIGHT=1` |
| Visual inspection | Desktop and mobile screenshots inspected; no horizontal overflow |

Positive AI-approval paths use synthetic generator/verifier/embedding doubles in a disposable database. They verify application logic, not actual model correctness or learning outcomes. No research scores, latency benchmarks or quality percentages are claimed.

Coverage includes ownership, live roles, mock approval blocking, version ancestry, no inherited reports, stale-base conflicts, retry reuse/conflicts, teacher rejection, exact approval evidence, source sealing, immutable events, temporary-table shadowing and atomic rollback after a write/audit failure. SQL checks preserve historical attempt scores across the migration and require renewed teacher approval after a later validation report.

The first focused run exposed an embedded socket-adapter error while rolling back expected raised business refusals. Expected refusals now use a bounded structured result after the function subtransaction rolls back; unexpected database failures still fail and roll back. Native release constraints were not weakened. A separate SQL test exercises an internal audit failure, while an API test exercises failure after writes and before commit. The first general runner attempt used a restricted system temporary directory; it was rerun in a writable workspace folder. Initial UI runs were stopped after remaining unresponsive; later focused and full thread-pool runs completed with a bounded Node heap and one worker at a time. Initial TypeScript test-selector and lint issues were corrected before the successful build. The backend emitted one existing Starlette/HTTPX deprecation warning.

Browser verification exposed an ambiguous textarea label; explicit accessible labels resolved it. Visual review added option letters and a singular queue count. A screenshot wait initially contained an incorrectly encoded test string; the file was repaired as UTF-8 and the wait now targets the named saved-report region. The final complete browser run passed after these corrections. Earlier incomplete runs are not counted as completed regressions.

## Saved evidence

Workspace logs: `phase13-focused2.log`, `phase13-schema.log`, `phase13-migrations-final.log`, `phase13-backend.log`, `phase13-lint-final.log`, `phase13-frontend-final.log`, `phase13-frontend-review-verified.log`, `phase13-build-verified.log` and `phase13-browser-final.log`.

Actual application screenshots using clearly labelled synthetic fixtures: [desktop review](images/phase-13-teacher-review-desktop.png) and [mobile editor/history](images/phase-13-teacher-review-mobile.png). The browser exercises generation, editing, fresh mock checks, blocked approval, rejection, another edit, version-history persistence and responsive navigation. Positive approval is tested with synthetic passing evidence in API/SQL tests. Test services and disposable accounts were stopped/discarded by the runner.

## Reproduction and limits

Use the installed local dependencies, set TEMP/TMP to a fresh writable workspace folder, and run memory-consuming checks sequentially. Backend: enable `MCQ_RUN_DB_TESTS=1`, keep `MCQ_RUN_MODEL_TESTS=0`, run `pytest backend/tests -v -p no:cacheprovider` with a fresh basetemp. Database: `npm.cmd --prefix database/tests test` with `TEST_PYTHON` pointing to the project Python. Frontend: run its tests and build; the verified focused test used `--pool=threads` with one configured worker and a 256 MiB Node heap cap. Browser integration uses `E2E_LIGHTWEIGHT=1` and installed Chrome/Edge.

Native Windows PostgreSQL/pgvector deployment, real password authentication and multi-connection contention remain unvalidated. Embedded PostgreSQL tests explicitly switch to a restricted runtime role; their single-connection adapter is not proof of native concurrent behavior. No production `.env`, real account, user upload or retained database was created or modified.

Editing currently supports conceptual questions and the existing remember/understand targets. Source/topic/type changes require a newly generated question. Mathematical and duplicate checks retain their Phase 12 bounds. **Hardware-validated model selection: pending.** The existing research presentation and review artifacts were not altered to invent implementation or experimental results.

Next: **Phase 14 — assessment publication and reference codes**. No Phase 14 application implementation is included here.
