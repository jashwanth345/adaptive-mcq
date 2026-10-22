# Phase 22 — local deployment and recovery complete

Verified 15 October 2026. **22 of 24 roadmap phases are complete; two remain.** The approved free build tools and pgvector are installed, a dedicated native project database is configured, and native application startup/recovery acceptance passed. The primary application remains local and uses lightweight mock AI.

## Installed and configured

- Visual Studio Build Tools 2022 **17.14.37806.7**, C++ toolchain and Windows SDK; installer reports complete/launchable and no restart required. This is a **free proprietary development tool**, not an open-source runtime dependency.
- **pgvector 0.8.7**, compiled from the official source commit `f37c13f68b57d2c3472b2214fbcff699d6d34876` for the existing **PostgreSQL 18.4** installation. Installed DLL matches the locally built DLL's SHA-256. [Installation evidence](evidence/phase-22-installation.json).
- Separate project cluster under `data/native-postgres/cluster`, listening only on **127.0.0.1:55432**, with SCRAM authentication, 64 MB shared buffers and 20 maximum connections. The pre-existing PostgreSQL service/data was not modified; extension binaries were added to the PostgreSQL installation as authorized.
- Dedicated owner and restricted application roles, all **12 migrations** and **15 module grant files**. The API uses the restricted role, never the cluster administrator.
- Private generated database/JWT configuration in `.env`; operator credentials in `data/native-postgres/operator.json`. Windows ACLs limit these files/directories to the user, SYSTEM and administrators. No password is printed in this report. The normal `adaptive_mcq` application database has no seeded/default website account.

Use [Start-Project.cmd](../Start-Project.cmd) to start the database and website. Use [Create-Teacher.cmd](../Create-Teacher.cmd) once to supply your own teacher identity and password through the existing validated operator flow. Students can register through the website. See the [operator guide](local-deployment.md) for shutdown, backup and recovery. Frontend: `http://localhost:5173`; API: `http://127.0.0.1:8000`; local docs: `http://127.0.0.1:8000/docs`.

## Verification evidence

| Check | Recorded result |
|---|---|
| Deployment/launcher/config/database regression | **58 passed**, including 24 deployment checks; no skipped check in this selected run |
| Existing embedded classroom browser journey after fixture adaptation | **14 passed** |
| Native PostgreSQL classroom browser journey | **14 passed**, including publication/admission, saved answers, clean API restart, lost-response retry, released scores, analytics, feedback/quarantine and study export |
| Native extension/runtime readiness | Actual vector cosine operation, all migrations, pgvector, non-owner role and auth grants passed |
| Native PDF/mock generation | Authenticated PDF upload/extraction and explicitly labelled mock draft generation passed; no LLM inference |
| Native transaction contention | Independent connection IDs and bounded conflicting row-lock behavior passed |
| Native abrupt database restart | Application table fingerprints remained unchanged; saved PDF metadata/source preview remained accessible |
| Full application backup/restore | Actual native dump plus three referenced PDFs restored into a separate empty native database; all non-session table fingerprints and file hashes matched |
| Restored permissions/sessions | Runtime readiness passed; original non-admin function ownership preserved; previous sessions revoked; fresh login and source preview passed |
| Retained configuration/supervised startup | Prepared frontend/API proxy, login route and security headers passed on the real project configuration; both application children stopped and ports were released |
| Code checks | Python lint/formatting passed; changed JavaScript files passed syntax checks |

See the [native acceptance report](evidence/phase-22-native-acceptance.json) and [retained startup report](evidence/phase-22-native-startup.json). The acceptance run contains eight grouped checks; its 14 browser checks are part of those groups, not an additional research sample. The earlier seven-check [primitive native probe](evidence/phase-22-native-probe.json) remains historical evidence from before extension installation.

All classroom questions, approvals, users, scores and exports in these tests are explicitly synthetic. Native tests ran in separate `mcq_acceptance_*` databases with local PDFs; the restored target is separate too. They do not create real research results or validate LLM quality. The retained application's database stayed empty of user accounts. The protected native cluster remains available; the website processes were stopped after the startup smoke check.

Prepared runs used local dependencies and mock AI. Browser tests rejected external requests and observed none; embedding files were checked without loading a model, and offline model flags were set. We did not disable the laptop's network adapter or claim a sustained full-stack embedding/LLM hardware benchmark.

## Corrections found by native testing

An empty libpq `service` parameter, accepted by an earlier mocked boundary test, caused native operator connections to fail. It is now omitted, inherited `PGSERVICE` is explicitly rejected, and a regression covers both behaviors. The test client's default `testserver` Host was correctly rejected by existing security middleware; the acceptance harness now uses the required loopback URL. Neither fix weakens request or database boundaries.

Windows installer resume completed successfully after an interruption; completion was checked through the installer inventory and compiled output, not assumed from a launched process. The source-build command's initial path invocation was corrected before the passing compile. Failed acceptance attempts remain separate test databases/files and are not claimed as passing runs.

## Recovery behavior and limits

The operator tools provide readiness checks, mutually exclusive startup/backup/restore, a consistent exported database snapshot, referenced-PDF hash checks, non-overwriting restore rehearsal and read-only orphan reconciliation. Restore does not change the live `.env`, overwrite live uploads or drop a database. It preserves object owners, reapplies runtime grants and revokes restored sessions. Incomplete output is retained for inspection. Tested restore does not authorize an automatic live cutover.

Backups contain private records and password hashes; they exclude application/operator configuration secrets and model weights. Native operator credentials and `.env` still require local account protection. Same-disk backups do not cover hardware loss. Whole-machine/power-loss recovery, exhaustive concurrency testing and public-internet hosting certification are not established.

Hardware-validated model selection, actual AI quality, independent-model verification and learner benefits remain **To be evaluated**. No model was downloaded or run. Ordinary mock questions remain blocked from approval/publication. The dedicated question-bank screen and other previously stated feature deferrals remain unchanged.

Next: **Phase 23 — final documentation**, then **Phase 24 — final evidence and presentation update**. Those phases have not started.

Technical sources: [pgvector Windows build instructions](https://github.com/pgvector/pgvector#windows), [Microsoft installer parameters](https://learn.microsoft.com/en-us/visualstudio/install/use-command-line-parameters-to-install-visual-studio?view=visualstudio), [PostgreSQL pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html), [PostgreSQL pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html).
