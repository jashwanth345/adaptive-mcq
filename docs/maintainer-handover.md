# Maintainer handover

Phase 23 adds documentation only. It does not change API routes, database schema, runtime configuration or release policy. Use the [setup guide](setup-guide.md) for operation, [user guide](user-guide.md) for workflows and [limitations](limitations.md) for claims.

## Source map

| Location | Responsibility |
|---|---|
| `frontend/src/` | React navigation, account state and role-specific feature screens |
| `backend/app/` | FastAPI configuration, authentication and scoped feature modules |
| `backend/manage.py` | Trusted operator account enrollment/activation commands |
| `database/migrations/` | Immutable forward migrations 001–012 and database integrity gates |
| `database/*_runtime_grants.sql` | Fifteen module permission sets for the restricted application role |
| `deployment/local.py` | Configure, doctor, supervised start, backup, verify-backup, restore and reconcile |
| `deployment/native.py` | This project's Windows cluster and interactive teacher provisioning |
| `evaluation/` | Synthetic/experimental runner, rubric, report/review tooling |
| `backend/tests/`, `frontend/tests/`, `database/tests/` | Engineering tests and isolated fixtures |
| `docs/evidence/`, `docs/images/` | Recorded reports/screenshots; observe provenance and synthetic-data labels |

The API authenticates the user and scopes ownership; application users share a restricted database role. SQL constraints/functions enforce additional lifecycle integrity. Models propose candidates; verifier reports are advisory; validation and teacher/release gates decide eligibility. Never make frontend visibility the sole authorization check.

## Configuration and retained state

Process environment overrides private `.env`. Keep one backend worker, loopback bindings, mock AI and existing bounded settings for this laptop. `GENERATOR_MODEL` and `VERIFIER_MODEL` select supported profiles only; changing a string does not validate another checkpoint. The supervisor accepts paired mock or paired local-Ollama modes. Start-Local-AI.cmd checks memory and installed files before starting the local runtime; see question-generation.md.

Private `.env` contains generated database/JWT credentials; `data/native-postgres/operator.json` contains privileged operator credentials. Do not log, print, commit or submit these. Normal API access uses `adaptive_mcq_app`; migration/account work uses an isolated owner terminal. Never launch the website with owner/admin credentials. Close the privileged terminal or clear its overrides after the operation.

The default native helper is Windows/PG18/path-specific, not a portable service installer. It does not manage the pre-existing PostgreSQL service. Keep the API's source release, all migration/grant files and the backup's source release aligned. Never edit already-applied migrations; add a reviewed forward migration, take a backup and verify a separate restore before upgrading retained data.

## Backup and handover package

Use the [tested backup/restore guide](local-deployment.md). Stop application writers, leave the database running, create a bundle, verify it and rehearse restoration into a new empty database. Preserve original role ownership. Do not merge partial uploads into live state. A live cutover is a deliberate operator action; no tool automatically overwrites `.env` or the source database.

For a college source submission, select source, lockfiles, `.env.example`, docs and reviewed synthetic evidence. Exclude active `.env`, operator state, uploaded documents, database clusters/dumps, backups, logs, local evaluation exports, `.venv`, `node_modules` and unreviewed personal data. `.gitignore` helps version control but does not protect a manually created ZIP. Do not archive the entire working folder indiscriminately. This phase does not create a submission archive.

For a private operational transfer, move verified backups and needed prepared assets through a protected channel separately from the source submission. Backup bundles contain password hashes and educational records; they exclude configuration secrets and model weights. Retain/recreate private credentials securely and preserve matching source/lockfiles. Same-disk copies do not cover disk loss. Recreate Python environments on another machine; do not assume a copied `.venv` is portable.

## Verification strategy

Use tests relevant to changed behavior. Documentation edits need link/route/command checks, not repeated model inference. For a future deployment-code change, the selected lightweight regression used in Phase 22 is:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_deployment.py backend/tests/test_launcher.py backend/tests/test_config.py backend/tests/test_database.py
```

For frontend changes, the existing commands are:

```powershell
npm.cmd test --prefix frontend
npm.cmd run build --prefix frontend
```

The [integration guide](integration-testing.md) documents isolated browser/database checks. Keep lightweight mode explicit for foundation browser tests. Never point fixture seed commands at retained user databases. Native acceptance deliberately stops/restarts its project cluster and refuses real accounts in the normal application database; it is not a routine check or a permission to remove that guard. Use an isolated cluster for future destructive recovery experiments.

Phase 23 does not rerun these application suites. Its evidence is documentation consistency, not a new pass count for functional behavior. Refer to [Phase 22](phase-22-completion.md) for targeted native acceptance, [Phase 21](phase-21-completion.md) for broader security regression and [Phase 20](phase-20-completion.md) for integration/database checks.

## Final handoff

- **Phase 24 is complete:** use the [final evidence package](phase-24-completion.md). No numbered roadmap phase remains.
- Retain the team/guide names and institution exactly as supplied in the academic material.
- Maintain the PPT from verified evidence; its actual UI screenshots are synthetic tests and actual LLM/learner outcomes remain **To be evaluated**.
- Keep deferred features and the mock publication block visible. Documentation completion does not imply the full research vision has been validated.
