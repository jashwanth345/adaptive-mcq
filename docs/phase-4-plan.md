# Phase 4 — authentication and user roles

Objective: implement local student registration, login, revocable bearer sessions, current-user identity, logout/password change, role dependencies and controlled teacher enrollment.

Architecture: FastAPI JSON routes call a transactional authentication service. Argon2id hashes passwords; HS256 JWT access tokens expire after 15 minutes by default and reference database session IDs. Every protected request validates signature/issuer/audience/type/expiry and checks the active session, active user and current database roles. No refresh token or cookie is used in this phase. Teacher provisioning is a local operator CLI using migration-owner credentials, never a public registration option.

Files: `backend/app/auth/`, `backend/manage.py`, migration `003_auth.sql`, a narrowly scoped runtime grant script, settings/route/middleware updates, tests and authentication documentation. Existing migrations 001/002 remain unchanged.

Database changes: persistent authentication sessions and throttling buckets; a fixed-search-path, restricted security-definer student-registration function atomically creates user, student role, profile and audit event. Runtime SQL grants permit authentication work but not role assignment or changing account activation. No real account, secret or native migration is created automatically.

API changes: POST `/api/v1/auth/register`, `/login`, `/logout`, `/logout-all`, `/change-password`; GET `/api/v1/auth/me`; role-protected GET `/api/v1/roles/teacher` and `/student`. These role checks do not pretend to be dashboards or assessment endpoints.

Dependencies: Argon2-cffi, PyJWT and email-validator, plus the Phase 3 framework/database stack. All are FREE / OPEN SOURCE and run locally. No email service, paid identity provider, cloud API or model integration.

Tests: real hashing and JWT rejection cases; student-only registration; teacher/student/dual-role boundaries; token tampering/expiry/missing claims; persistent logout; disabled users; password change/revocation; restart behavior; transactional registration; SQL role-grant restrictions; throttling; payload bounds; safe errors/logs; regression migrations/backend tests. Native Windows PostgreSQL authentication and multi-connection races remain separate validation gates.
