# Phase 20 — integration testing

Authorized 14 October 2026. Scope: test the connected application, correct demonstrated integration defects, capture the actual frontend and report project progress. Do not implement Phases 21–24 or claim real model/learner results.

## Test scope

- Re-run the lightweight foundation browser journey: registration, roles, dashboards, PDF extraction, private test drafts, advisory review, math/release gates, versioned editing and blocked mock publication.
- Add a classroom integration journey against the built React frontend, actual FastAPI endpoints and disposable PostgreSQL/pgvector: teacher creates/publishes an assessment from explicitly synthetic approved fixture questions; student joins, saves, resumes and submits; analytics, feedback/quarantine and evaluation exports remain consistent.
- Inject a lost response after a committed save and verify safe retry; restart the backend while retaining the disposable database and verify saved answers; check foreign/unreleased access and deliberate service failures without displaying fabricated success.
- Exercise reference-code replacement, current role enforcement, immutable original scores and exclusion of quarantined evidence across analytics, mastery and study export.
- Run backend, frontend, migration and SQL regression checks using small workers. No model download, model inference, paid service or real learner data.
- Inspect desktop/mobile screenshots and deliver actual teacher/student frontend images. Capture logs and a reproducible integration matrix, distinguishing current checks from earlier evidence.

## Files and architecture

New browser integration script under `frontend/tests`, focused integration tests if gaps require them, test runner command, phase completion/progress documents and screenshots under `docs/images`. Existing isolated fixture launchers and synthetic question evidence are test-only; they do not relax application publication gates. No database schema or runtime dependency change is planned. Any production fix will be limited to an observed integration defect and verified at the appropriate level.

## Limits

Embedded PostgreSQL validates SQL and the real driver, not native password authentication, multi-connection concurrency or operating-system crash recovery. Native local deployment and prepared offline recovery remain Phase 22 checks. Tiny model hardware validation, semantic model quality and learner studies remain pending. A test fixture's approval is never evidence of real AI correctness.
