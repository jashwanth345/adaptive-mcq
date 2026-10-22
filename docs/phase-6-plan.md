# Phase 6 — teacher dashboard

Authorized 6 October 2026. Objective: replace the teacher workspace placeholder with an owner-scoped overview and useful course/topic organization. Assessment authoring, uploads, AI, review and publication stay in their scheduled phases.

Before implementation: add `backend/app/teacher/` schemas/service/routes, `database/teacher_runtime_grants.sql`, a teacher dashboard frontend module and focused backend/frontend/browser tests. Update authentication's frontend request wrapper to handle protected feature calls and revoke expired sessions. Existing schemas suffice: no migration or checksum change. The operator applies narrow read/insert grants to existing course/topic tables and read-only overview tables.

API: GET teacher dashboard; GET/POST teacher courses; GET course detail; POST course topics. Role and object ownership checks occur on the backend. Limits bound courses per page and topics per course; no request can set owner, roles, publication or verification status. Writes have duplicate protection and audit records. Overview counts use stored rows, not illustrative metrics; network failures show unavailable data rather than zero.

Reuse current FREE / OPEN SOURCE stack and pinned dependencies; no package, cloud API or model installation. Test real PostgreSQL queries with two teachers and a student, cross-owner denial, validation, duplicate requests, narrow grants and role revocation. Test frontend loading/retry, API errors, creation, navigation and real-browser desktop/mobile flows. Native PostgreSQL setup remains a separately recorded limitation. Stop at Phase 6.
