# Phase 13 — teacher review, versioned editing and approval

Implement a teacher-only review queue with owned question/source inspection, immutable edit history, rejection and explicit approval. A saved edit creates a new version, retains original generation/source provenance and quarantines a previous release. Every new version needs fresh verifier and deterministic reports. Mock ancestry remains mock after editing.

Approval will link an immutable teacher decision to the exact current validation and advisory reports. The legacy numerical-score verification path remains available for historical data; the new categorical path must not invent scores. Restricted runtime functions will atomically record decisions, releases and audit events; the application will not receive direct release-write privileges. Approval is not assessment publication.

Rejecting a version requires an edit before reconsideration. Stale edits and decisions fail; request keys support safe retries. Queue and version history are private and paginated. Existing student draft/review flows and the planned automatic private-practice release contract remain intact.

Verification: restricted-role disposable PostgreSQL, real API tests with synthetic AI doubles for eligible approval, frontend tests, production build, and lightweight browser flows with mock data. No model downloads or inference. Native Windows PostgreSQL authentication and multi-connection races remain separate deployment checks. Phase 14 publication/reference codes are outside this phase.
