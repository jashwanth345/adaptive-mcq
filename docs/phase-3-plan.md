# Phase 3 — backend foundation

Objective: create a runnable local FastAPI foundation with strict configuration, bounded database connections, diagnostics, consistent errors and tests.

Architecture: an application factory validates settings, a lifespan context owns a small synchronous SQLAlchemy/Psycopg connection pool, and synchronous database endpoints run in FastAPI's thread pool. This avoids an asynchronous Psycopg event-loop compatibility requirement on Windows. Database work uses explicit transactions; sessions never auto-commit at request exit. Config errors stop startup; database outages keep liveness available but fail readiness.

Files: `backend/app/` for settings, database access, errors, middleware, health routes, offline API documentation and launcher; `backend/tests/` for unit/API/database integration tests; pinned Python requirements; updated `.env.example`, README and phase reports. The existing test-only PGlite harness gains a loopback PostgreSQL socket adapter for real driver tests.

Database changes: none. Existing migration files/checksums remain unchanged. Readiness reads PostgreSQL, pgvector and migration history; it never creates tables, applies migrations, grants permissions or downloads models. Runtime login privilege checks require a non-superuser/non-owner role with metadata-read permission; role provisioning remains a manual administrator step until authentication/setup phases.

API additions: `GET /api/v1/health/live`, `GET /api/v1/health/ready`, `/openapi.json`, and local `/docs`. No authentication, student, teacher, upload, generation or worker endpoints are implemented here.

Dependencies: Python, FastAPI, Pydantic Settings, SQLAlchemy, Psycopg, Uvicorn, pytest, HTTPX, Ruff and test-only PGlite/socket/pgvector packages. All are FREE / OPEN SOURCE; no paid or cloud service. Resolve/pin installed versions. Python environment and test packages stay inside the project.

Tests: configuration precedence and local-only rejection, secrets redaction, liveness/readiness HTTP semantics, migration/vector/privilege diagnostics, origin/host restrictions, request IDs/error responses, connection disposal, rollback/commit behavior, live loopback HTTP smoke checks, and real driver queries against disposable embedded PostgreSQL if supported. Native Windows PostgreSQL deployment and real multi-connection concurrency remain separate evidence gates.
