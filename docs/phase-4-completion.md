# Phase 4 completion record

Date: 5 October 2026. Authorized scope: **authentication and user roles**, resumed after the user's “continue”.

**Implemented and tested:** student registration, Argon2id password hashing, JWT login, active-session validation, current-user profile, logout/logout-all, password change, role gates, persistent throttling and a local operator CLI for teacher enrollment/account activation.

## Delivered

- Authentication schemas, security utilities, service and routes under `backend/app/auth/`.
- Migration `003_auth.sql`: sessions, rate-limit buckets, immutable revocation and restricted student-registration function. Migrations 001 and 002 retain their original checksums.
- `database/auth_runtime_grants.sql`: explicit operator-applied authentication permissions, without runtime role-assignment or account-activation privileges.
- `backend/manage.py`: teacher creation, grant/revoke teacher, disable/enable user. No public administrator API, default account or password.
- Updated readiness checks, CORS for authenticated POST requests, 16 KiB authentication body bound, safe errors and no-store identity/token responses.
- Pinned FREE / OPEN SOURCE dependencies and [authentication setup/contracts](authentication.md).

## Actual validation

| Check | Observed result |
|---|---|
| Backend regression + authentication suite | **82 passed**: 65 unit/API/startup checks and 17 disposable-database integration tests |
| SQL migration/schema suite | **41 passed**, including populated version-2 upgrade to version 3 without modifying existing accounts |
| Migration runner suite | **7 passed** |
| Password/JWT tests | Salted Argon2id hashes verified; wrong passwords and unsigned/expired/future/wrong-key/wrong-algorithm/malformed JWTs rejected |
| Identity and roles | Student-only registration, student/teacher/dual-role gates, fresh role lookup, teacher operator restrictions and disabled-account denial passed |
| Session lifecycle | Current/all-session revocation, app-recreation persistence, database expiry, password-change revocation and irreversible session revocation passed |
| Throttling | Generic failed login responses, persisted account limits, Retry-After and ignored forwarded client headers passed |
| Runtime SQL rights | Role inserts/deletes, account-activation writes and session-expiry rewrites rejected |
| Ruff and dependency consistency | Passed |
| Native application accounts/migration | **Not created or applied**; test accounts existed only in disposable databases |

Tests ran on the existing Windows/Python 3.12.14 environment with Node.js 22.19.0 and embedded PostgreSQL/PGlite. Native installed PostgreSQL authentication was not used. Test timings are not application latency or project evaluation results. No MCQ-quality experiment was run.

The backend suite retains one upstream warning about Starlette's HTTPX TestClient deprecation. A sandbox temporary-directory access error was resolved by using a fresh workspace-local test directory; no tests were skipped to obtain the final 82-pass result.

## Remaining validation and boundaries

The embedded socket adapter failed when a SQL error was followed by wire-level rollback. Expected permission/constraint failures are asserted inside PostgreSQL exception blocks, which fail if the expected rejection does not occur. Native aborted-transaction recovery and multi-connection races therefore remain unverified. Regular explicit commit/rollback and API-level failure behavior are covered separately.

Native Windows PostgreSQL/pgvector startup, real database login credentials, runtime grants, and retained-database migration still require setup/verification. The backend now refuses authentication operations when its database/authentication readiness checks fail. Liveness alone does not establish that accounts can be used.

No real users, teacher credentials, persistent JWT secret or active `.env` were created. Temporary servers were stopped by the test harness. No paid service, email service, cloud authentication, model download or paid fallback was introduced.

Email ownership verification, forgotten-password recovery, MFA, refresh tokens, frontend login screens and automated authentication-record cleanup are not implemented. Course/material/answer ownership authorization must accompany their later feature endpoints; role gates alone are not those controls.

**Hardware-validated model selection remains pending.** Presentation artifacts remain unchanged; implementation tests are not presented as research results.

Next phase: **Phase 5 — frontend foundation**. This turn stops at Phase 4.
