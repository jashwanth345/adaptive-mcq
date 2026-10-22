# Backend foundation — setup and contracts

> Current handover: [documentation index](README.md), [setup guide](setup-guide.md), [user guide](user-guide.md) and [limitations](limitations.md). This module reference preserves its phase-specific history. Later implementation and Phase 22 native setup supersede earlier planned/pending statements and partial bootstrap instructions. Use the current guides for everyday operation.

Phase 3 provides the FastAPI process, validated settings, connection/session management and diagnostics. Phase 4 adds [authentication and role checks](authentication.md). Assessments, uploads, RAG and LLM inference remain planned. Native PostgreSQL/pgvector provisioning remains pending on the student's installation.

## Start locally

Run commands from the `adaptive-mcq` project root. The project-local `.venv` created in this session uses Python 3.12.14. It is disposable, ignored by Git and not portable to another laptop. The student's separate Python 3.13.1 installation was not used for these tests. When moving the project, recreate the virtual environment with an available compatible Python and rerun the checks.

For a new environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

On this workspace the dependencies are already installed. No paid service or account is required. Package installation initially needs internet; the prepared backend makes no cloud requests or downloads.

Create a project-root `.env` from `.env.example` only if you do not already have one. Edit an existing `.env` rather than overwriting it. Supply the actual local database name, restricted login and private password. Set a separate, stable, randomly generated `JWT_SECRET` of at least 32 characters. Phase 4 uses it for tokens and throttling-key digests.

You may supply secrets to the current PowerShell process instead of putting them in a file:

```powershell
$env:DATABASE_PASSWORD = [Net.NetworkCredential]::new('', (Read-Host 'Local database password' -AsSecureString)).Password
$env:JWT_SECRET = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
.\.venv\Scripts\python.exe -m backend.app
```

These assignments do not print secret values. Process settings override `.env`. Generate the JWT secret once and preserve it privately for subsequent starts; do not regenerate it each time. Changing it invalidates tokens and changes throttling-key digests. No real secret or active `.env` has been created by this phase.

Default addresses while the process is running:

- API documentation: `http://127.0.0.1:8000/docs`
- OpenAPI contract: `http://127.0.0.1:8000/openapi.json`
- Liveness: `http://127.0.0.1:8000/api/v1/health/live`
- Database readiness: `http://127.0.0.1:8000/api/v1/health/ready`

Use Ctrl+C to stop. The supported launcher binds loopback, uses one worker, disables proxy-header trust and avoids raw URL access logs. It never starts PostgreSQL/Ollama, applies migrations, downloads models or creates uploads. The local docs page needs no CDN and can run its diagnostic requests offline.

## What starts and what fails

| Condition | Behavior |
|---|---|
| Missing/blank database password; short/blank JWT secret; invalid local configuration | Startup exits with code 2 and setting names only |
| Remote database/API host; cloud model URL; cloud-enabled flag; multiple inference jobs | Configuration rejected |
| PostgreSQL unreachable or credentials rejected | API can start; liveness 200, readiness 503 |
| pgvector not enabled; migration history missing/changed/incomplete | Readiness 503 with a specific check status |
| Runtime login lacks migration metadata read permission | Readiness 503, `missing_readiness_permissions` |
| Runtime role is superuser, database/schema owner or has administrative capabilities | Readiness 503, `unsafe_privileges` |
| All foundation checks pass | Readiness 200, explicitly scoped to `backend_foundation` |

Do not use a 200 liveness response as deployment readiness. A 200 readiness response confirms only the Phase 3 database foundation. It does not establish model availability, learner features, API authorization, every future table privilege or full database consistency.

## Configuration contract

The loader uses the project-root `.env` regardless of working directory. Precedence: explicitly supplied settings in tests/factories, then process environment, then `.env`, then safe defaults. Unknown `.env` keys are rejected to catch spelling errors; unrelated process variables are ignored. Error messages list setting names without values. Secrets use Pydantic `SecretStr` and are not printed in object representations.

| Group | Relevant controls |
|---|---|
| API | `API_HOST`, `API_PORT`, one `FRONTEND_ORIGIN`; HTTP loopback only |
| Database | Host/port/name/user/password as separate fields; no interpolated connection string |
| Resource limits | Pool size 2, no overflow; pool wait 2 seconds; connect timeout 3 seconds; statement timeout 2,000 ms; lock timeout 1 second |
| AI configuration only | Model identifiers, `LOCAL_ONLY=true`, `OLLAMA_NO_CLOUD=1`, one inference job, bounded context/output/retries |
| Language/storage | English baseline; future upload location fixed to `backend/uploads` |
| Model evidence | `MODEL_SELECTION_STATUS=pending_hardware_validation`; no other status is accepted by this phase |

Database pool size may be configured between 1 and 4; increasing it does not permit simultaneous LLM inference. A readiness call performs several bounded queries, so its overall duration is not a promise of exactly one statement-timeout period.

`localhost` database/API hosts normalize to numeric loopback. The driver explicitly sets host address, port, credentials, database, SSL mode and PostgreSQL options. `PGSERVICE` is rejected because an inherited libpq service could change connection behavior. Explicit connection options take precedence over inherited `PGHOSTADDR`/`PGOPTIONS`. Do not set SQL echo/debug logging in deployment: it may reveal private parameters.

The Ollama fields describe the intended separately launched process. They do not reconfigure an already running Ollama instance, verify installed model licenses, or prove that it is offline. Those checks belong to the later local-model integration. No LLM adapter is present in Phase 3. **Hardware-validated model selection remains pending.**

## Database setup and permissions

Use the [Phase 2 guide](database.md) to prepare native PostgreSQL and install/enable pgvector. Migrations must run as a separate migration-owner account. Do not make the application login a database owner just to get a health check to pass.

After creating a non-administrative `adaptive_mcq_app` login and applying migrations, an administrator can grant the diagnostics-only permissions below in the correct local database:

```sql
GRANT CONNECT ON DATABASE adaptive_mcq TO adaptive_mcq_app;
GRANT USAGE ON SCHEMA mcq, mcq_meta TO adaptive_mcq_app;
GRANT SELECT ON mcq_meta.schema_migrations TO adaptive_mcq_app;
```

These statements are the Phase 3 diagnostics-only grants, not automatically executed setup. **They are insufficient for Phase 4:** also apply the authentication-specific grant script in the [authentication guide](authentication.md). Readiness now checks `auth_permissions` and authentication fails closed when setup is incomplete. Schema equality uses migration history, not an exhaustive audit of every object/data row.

The readiness checker uses a read-only transaction. It compares the complete stored migration map to the checked-in migration files. A newer, older or altered map is not accepted. pgvector must appear in `pg_extension`. It does not install the extension or repair history.

## Connections and transactions

One `Database` instance owns one bounded SQLAlchemy pool for the application's lifespan. The pool opens connections lazily, validates reused connections and is disposed on shutdown. Synchronous DB endpoints run in FastAPI's thread pool, avoiding Psycopg asynchronous Windows event-loop constraints.

The `get_session` dependency provides a session that rolls back remaining uncommitted work on exit. It never commits automatically. Future services must use an explicit transaction:

```python
with database.session() as session, session.begin():
    # Make all related authorized changes here.
    # An exception rolls the whole transaction back.
    ...
```

Services should finish transactions before returning a successful response. Do not share a session between threads or requests. No ORM table definitions, duplicate migration framework or auto-create operation is introduced; Phase 2 SQL remains the schema authority.

## HTTP behavior

| Route | Result |
|---|---|
| `GET /api/v1/health/live` | 200 with `status: alive`; no DB access |
| `GET /api/v1/health/ready` | 200 or 503 with `status`, `scope` and `checks` |
| `GET /openapi.json` | Current API contract only |
| `GET /docs` | Self-contained local diagnostic/API documentation |

Readiness status names include `ok`, `missing`, `migration_mismatch`, `unavailable`, `busy`, `timeout`, `not_checked`, `missing_readiness_permissions` and `unsafe_privileges`. A SQL/connection exception is converted to these safe states; raw driver messages, connection strings and SQL are not returned.

Other request errors use:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "request_id": "server-generated-uuid",
    "details": [{"location": ["body", "field"], "type": "validation_type"}]
  }
}
```

This is a contract illustration, not a stored real response. Validation details omit rejected input values. HTTP errors do not echo arbitrary exception details. Unexpected exceptions return a generic 500. Readiness uses its documented diagnostic body instead of this generic error envelope.

Every HTTP response gets a server-generated `X-Request-ID`, including CORS preflight and rejected Host requests. Caller IDs are not trusted. Health/error responses disable caching. `X-Content-Type-Options: nosniff` is added. Logs include correlation ID, status and elapsed time, omitting request bodies, query strings, credentials and raw exceptions.

Only local Host headers are accepted. CORS allows the exact configured frontend origin, GET/POST requests and explicit allowed headers. Cookie credentials remain disabled; authentication uses explicit bearer tokens. CORS itself is not authentication or authorization and does not prevent another local process from making requests.

## Files and dependencies

| Path | Responsibility |
|---|---|
| `backend/app/config.py` | Validated immutable settings and safe startup diagnostics |
| `backend/app/database.py` | Connection pool, sessions and database readiness |
| `backend/app/main.py` | App factory, lifespan, dependency provider and routes |
| `backend/app/errors.py` | Consistent safe request errors |
| `backend/app/middleware.py` | Host checks, request IDs and safe request logging |
| `backend/app/__main__.py` | Supported loopback launcher |
| `backend/app/docs.html` | Offline diagnostic documentation |
| `backend/tests/` | Configuration, API, driver, lifecycle and startup tests |
| `database/tests/backend-server.mjs` | Test-only disposable PostgreSQL protocol adapter |

All selected technologies are **FREE / OPEN SOURCE**. The main tested versions are FastAPI 0.142.2, Pydantic 2.13.5, Pydantic Settings 2.15.0, SQLAlchemy 2.0.54, Psycopg 3.3.6 and Uvicorn 0.54.0. Full exact version lists are in `backend/requirements.txt` and `backend/requirements-dev.txt`; `.in` files record intended direct dependency ranges. Re-resolve and test intentionally before upgrading. These locks describe the tested Windows/Python environment; other environments require verification.

PGlite 0.5.8, pgvector adapter 0.0.9 and socket adapter 0.2.11 are test-only npm dependencies. The core application uses native PostgreSQL and needs no Node process for database access. Initial package downloads require internet; runtime and prepared tests are local. OpenTelemetry API is a transitive dependency only; no exporter, monitoring account or telemetry destination is configured.

## Reproduce tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe -m pip check
```

The default test command skips the explicit PostgreSQL integration tests (17 after Phase 4). To include them:

```powershell
npm ci --prefix database/tests --ignore-scripts --no-audit --no-fund
$env:MCQ_RUN_DB_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests -q
Remove-Item Env:MCQ_RUN_DB_TESTS
```

Set `TEST_NODE` to an absolute Node executable if it is not on PATH. The harness uses the active test interpreter to render the existing migrations. It starts isolated in-memory databases on automatically selected loopback ports and stops them afterward. The HTTP smoke test similarly starts/stops a temporary Uvicorn process. No fixtures are inserted into a native application database.

The adapter executes real PostgreSQL SQL and the actual Psycopg/SQLAlchemy driver. Its session role is explicitly set for SQL privilege tests; it does **not** verify native password authentication. Its single embedded database connection also cannot establish native multi-connection concurrency guarantees. Native startup, real login grants and concurrent transactions remain to be validated on the installed PostgreSQL server.

References used: [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/), [Pydantic settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/), [Psycopg concurrency/Windows notes](https://www.psycopg.org/psycopg3/docs/advanced/async.html), [PGlite socket limitations](https://pglite.dev/docs/pglite-socket).


## Phases 15 and 16 update

New student attempt and learning routes are included in application version 0.16.0. Apply migrations 008/009 and their attempt/adaptive grants after earlier module setup. Scoring, state changes and learner events commit atomically; no client-supplied score is accepted. Read [the API and policy guide](attempts-and-adaptive.md) for endpoint contracts and release behavior.


## Phase 18 update

Version 0.18.0 adds read-only student, teacher and assessment-specific analytics. Migration 011 and analytics runtime grants are required. Scores derive from immutable attempt snapshots; student release rules apply before aggregation. See [analytics contracts and endpoints](analytics.md).

## Phase 17 update

Version 0.17.0 adds attempt-linked reports, private history, scoped owner reviews and atomic quarantine decisions. Migration 010 and feedback runtime grants are required. `FEEDBACK_MIN_REPORTERS` and `FEEDBACK_REPORT_RATIO` configure priority only, not automatic quarantine. See [API and policy](feedback.md).


## Phase 19 update

Version 0.19.0 adds teacher-owned synthetic evaluation runs, blinded review exports and consent-confirmed adaptive-study exports. Apply migration 012 and evaluation runtime grants. The website cannot invoke real models through these routes. See [evaluation contracts and limits](evaluation.md).
