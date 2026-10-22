# Phase 2 — database implementation

Objective: implement persistent records and database invariants for the approved local architecture, before adding API or UI behavior.

Files: `database/migrations/*.sql`, `database/migrate.py`, `database/tests/`, `docs/database.md`, and a phase completion record. README gains database setup and status links. No existing database is migrated automatically.

Database changes: normalized users/roles, course memberships, versioned materials and questions, provenance/verification, immutable assessment content, reference codes, attempts/answers, feedback, mastery evidence, jobs and audit events. A second migration adds dimensioned local pgvector embeddings. IDs use UUIDs; dates use timezone-aware timestamps. Application scoring, authentication, worker behavior and evaluation stay in later phases.

API changes: none.

Dependencies: PostgreSQL and pgvector, Python standard library migration runner, and PGlite plus its pgvector extension for isolated SQL tests. All are FREE / OPEN SOURCE. PGlite is test-only; native PostgreSQL remains the application database. SQLAlchemy can be added for backend access later. Alembic is not required for this initial SQL-based history; any later adoption must preserve existing migration history instead of running a second competing migrator.

Validation: execute migrations on fresh embedded PostgreSQL, exercise foreign keys, version immutability, release gates, publication snapshots, attempt/option integrity, feedback provenance, mastery bounds, vector dimensions and scoped retrieval. Verify migration checksum/replay logic and atomic failure. Check a missing vector extension fails without a fake substitute. Native Windows server bootstrap is separately checked; failure there must be disclosed rather than equated with embedded test success.

Scope decision: use a small checksum-verified SQL migration runner invoking the installed `psql` client. This keeps database behavior inspectable and avoids adding an ORM just to create schema. Migrations are forward-only; restore a verified backup for rollback. No destructive downgrade command is provided.
