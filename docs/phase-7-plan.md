# Phase 7 — student dashboard

Authorized 6 October 2026. Before implementation: deliver a student-only overview of stored counts, active enrolled courses (latest six), paginated read-only attempt history and saved starting-difficulty preference. Joining assessments, attempting questions, released scores, feedback submission, generation and adaptive mastery stay in later phases.

Files: `backend/app/student/` routes/models/service, `database/student_runtime_grants.sql`, `frontend/src/student/` screens/styles, focused backend/frontend tests, extended real-browser tests and setup/completion documentation. Reuse the protected API client and existing student profile, membership, attempt and material tables. No migration/checksum changes, new dependencies, models or cloud services. Existing dependencies remain FREE / OPEN SOURCE.

API: GET student dashboard; GET paginated student attempts; POST own preferences. Server identity selects the student; owner/student IDs are never accepted in request bodies. History contains metadata only, without answers, keys or scores. Preference is a stored choice, not an evaluated mastery estimate or implemented adaptive algorithm. Writes are audited.

Check student/teacher role gates, two-student isolation, active versus inactive memberships, archived material exclusion, history ordering/pagination, no answer leakage, enum/extra-field validation, profile absence, preference persistence, error/retry states, desktop/mobile layout, and prior authentication/teacher behavior. Native PostgreSQL setup remains pending; tests use the disposable adapter. Stop at Phase 7.
