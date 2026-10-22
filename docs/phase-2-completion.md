# Phase 2 completion record

Date: 5 October 2026. Authorization: the user's “continue” after Phase 1 was taken as instruction to proceed with the next roadmap phase. Scope: database schema, versioned migrations and validation; no later feature phase was implemented.

**Database implementation delivered; embedded validation passed. Native deployment readiness remains pending.**

## Delivered

- Two forward-only SQL migrations: 27 core tables, 2 embedding tables, derived scores view, constraints, indexes and lifecycle triggers. Migration metadata is stored separately.
- Immutable question/content versions, explicit verification/release records and frozen published assessments.
- Teacher/course/student relationships, private practice, code digests, attempts/answers, feedback, mastery evidence, jobs and audit storage.
- Standard-library Python migration runner with an advisory transaction lock, checksum history, local target validation, replay protection and atomic application.
- Repeatable isolated SQL tests, runner tests, pinned test dependencies, and the [database operating guide](database.md).

## Actual checks

| Check | Observed result |
|---|---|
| SQL migrations and workflow/integrity tests | **40 passed**, embedded PostgreSQL 18.3 (PGlite 0.5.8), pgvector 0.8.1 |
| Python migration-runner tests | **7 passed**, Python 3.12.14 supplied by the document/workspace runtime |
| JavaScript test runtime | Node.js 22.19.0 |
| Missing vector extension | Full transaction failed and core schema rolled back; explicitly selected core-only migration succeeded |
| Replay / tampered checksum / older target | Replay preserved history; tampered checksum and older target rejected |
| Native PostgreSQL client | psql/initdb 18.4 binaries callable |
| Isolated native server initialization | Failed: Windows sandbox restricted-token creation/re-execution and data-directory initialization errors |
| Native pgvector files | Not present in checked PostgreSQL installation |
| Actual application database | Not created or migrated |

“47 passed” refers to software checks, **not** MCQ accuracy, student scores, generation quality or a project experiment. All fixture questions, scores and model names exist solely inside the disposable tests. They are not seeds for a real assessment database.

## Dependencies and deviations

PostgreSQL, pgvector, Python, Node.js and the PGlite testing packages are FREE / OPEN SOURCE. No paid service, API key, cloud database or model download was used.

The SQL runner replaces the initially considered Alembic-only migration approach for this phase: it preserves versioning and atomic/checksum protection without introducing an ORM before the backend exists. SQLAlchemy remains a possible backend dependency. PGlite is an added **test-only** dependency because native server startup was blocked; it does not replace the planned native PostgreSQL application database.

The installed user Python 3.13.1 could not be launched in this sandbox during Phase 2. The tests therefore used the existing bundled Python 3.12.14. This is not a claim that the user's interpreter or app environment has been configured.

## Remaining validation and next boundary

Native Windows PostgreSQL/pgvector startup, native migration application, multiple-connection races, runtime-role grants and backup/restore remain unverified. PGlite's single-connection execution cannot establish concurrency correctness. Constraints and row/advisory locks have been implemented, but native concurrent tests are still required.

Phase 3 is backend foundation: environment loading, database connection/session lifecycle, health/readiness endpoints and error handling. It should expose missing pgvector/server readiness clearly. Authentication, roles at API level, UI, worker execution, PDF/RAG/LLMs and adaptive algorithms remain their later phases. No claim of a running application, completed assessment platform or hardware-validated model selection is made.
