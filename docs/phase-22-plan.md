# Phase 22 — local deployment and recovery

Authorized 15 October 2026. Keep the core free, local and in mock AI mode. No LLM inference or downloads. Do not modify the existing PostgreSQL service or its data.

Deliver a read-only readiness command, explicit private configuration, a supervised local frontend/backend launcher, consistent database/PDF backups, non-overwriting restore rehearsal, upload reconciliation and an operator runbook. Startup must refuse missing database/schema/permissions rather than silently substitute the disposable test database. Recovery must preserve user files and never automatically delete orphan uploads.

Validate with small automated fixtures and, where available, an isolated native PostgreSQL cluster. Exercise authentication, transactions, restart, backup integrity and restore without touching existing databases. Missing pgvector or restricted native-process execution must remain an explicit deployment blocker. Do not count Phase 22 complete until the actual native PostgreSQL/pgvector application and recovery acceptance checks pass.

Initial observations: PostgreSQL 18 binaries exist; pgvector extension files and a project `.env` are absent. No compiler toolchain was found in the usual Visual Studio locations. The first sandboxed isolated initdb attempt stalled during shared-memory probing and was interrupted. Native verification will use a bounded process and an isolated workspace directory.
