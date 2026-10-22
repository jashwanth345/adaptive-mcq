# Local deployment and recovery — Phase 22

Status on 15 October 2026: **Phase 22 complete.** PostgreSQL 18.4 + pgvector 0.8.7 is configured in a dedicated project cluster at `127.0.0.1:55432`. Native classroom, PDF, abrupt-restart and application backup/restore checks passed. Private `.env` configuration and owner/runtime roles are provisioned; no default website account was created. See [verified evidence and limits](phase-22-completion.md).

## Quick start on this laptop

1. Double-click **`Start-Project.cmd`** in the project folder. It starts the dedicated database if necessary and then the prepared frontend/backend. Keep its terminal open.
2. Open **http://localhost:5173**. Use website registration and select Teacher or Student. The optional `Create-Teacher.cmd` operator flow remains available. No shared/default password exists.
3. Press **Ctrl+C** in the website terminal to stop the frontend/backend. The database remains available. After stopping the website, **`Stop-Database.cmd`** stops only the dedicated project database.

Equivalent terminal commands from the project folder:

```powershell
.\.venv\Scripts\python.exe -m deployment.native start
.\.venv\Scripts\python.exe -m deployment.local start
```

The database uses port **55432**, API **8000**, and frontend **5173**. The database's private admin/owner/runtime credentials are generated and stored under `data/native-postgres/operator.json`; never publish that file or `.env`. They are protected with Windows account ACLs. Do not rerun `native init` or `local configure` here; both refuse to overwrite prepared state.

The installation/bootstrap sections below are for a fresh machine or an operator-managed replacement. They are not steps to repeat on this configured laptop. The acceptance databases contain synthetic records and are separate from the normal empty `adaptive_mcq` database.

## Local architecture and cost

| Component | Classification | Operation |
|---|---|---|
| React/Vite/Tailwind and Node.js | FREE / OPEN SOURCE | Prepared frontend build, served on loopback |
| Python/FastAPI/Uvicorn | FREE / OPEN SOURCE | One backend worker; bounded database pool |
| PostgreSQL + pgvector | FREE / OPEN SOURCE | Native local database; persistent data |
| PyMuPDF | FREE / OPEN SOURCE (AGPL distribution) | Existing local PDF extraction; retain its license obligations |
| Sentence Transformers/local MiniLM snapshot | FREE / OPEN SOURCE | Existing local embedding files; no download during startup |
| Ollama/local LLM adapters | FREE / OPEN SOURCE runtime | Default launcher uses mock mode; Start-Local-AI.cmd explicitly enables prepared local inference |
| PostgreSQL dump/restore + Python filesystem tools | FREE / OPEN SOURCE | Local backup bundles and non-overwriting rehearsal |

Core service/subscription cost remains **₹0**. Initial dependency preparation can require internet; a prepared startup does not install packages or download models. Electricity, existing hardware and optional removable backup media are outside the service-cost claim. No cloud deployment is required.

## One-time native prerequisites

Use a normal Windows terminal for native PostgreSQL operations. The restricted automation sandbox can prevent native initialization. PostgreSQL binaries were observed at `C:\Program Files\PostgreSQL\18\bin`. The Phase 22 probe used a separate workspace cluster and did not modify the installed service or data directory.

1. Install a pgvector build compatible with the PostgreSQL major version and Windows architecture. Follow the [maintainer's Windows build instructions](https://github.com/pgvector/pgvector#windows). This laptop now has the approved Visual C++ Build Tools/SDK and a locally compiled pgvector 0.8.7 extension. Keep extension installation separate from routine startup. Microsoft Build Tools is free proprietary development software; pgvector is free/open source.
2. Configure the intended PostgreSQL instance to listen only on `127.0.0.1` (and optionally `::1`). Require `scram-sha-256` for TCP loopback logins in `pg_hba.conf`; do not use `trust` for the application connection. Record the actual database port and service name. Do not overwrite an existing cluster's configuration blindly.
3. With a trusted local PostgreSQL administrator, create dedicated accounts and database. Example SQL in interactive `psql`, only after confirming these names do not already exist:

```sql
CREATE ROLE adaptive_mcq_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
\password adaptive_mcq_owner
CREATE ROLE adaptive_mcq_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
\password adaptive_mcq_app
CREATE DATABASE adaptive_mcq OWNER adaptive_mcq_owner;
\connect adaptive_mcq
REVOKE ALL ON DATABASE adaptive_mcq FROM PUBLIC;
GRANT CONNECT ON DATABASE adaptive_mcq TO adaptive_mcq_owner, adaptive_mcq_app;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE EXTENSION vector;
```

The administrator enables the installed extension; migration 002 then encounters the existing extension. The runtime role must never own the database/schemas or inherit the owner/admin role. Do not store the administrator password in the application's `.env`.

4. Run the existing migration runner as the owner. All **12 migrations** are applied together with checksum verification. Supply the password through a protected PostgreSQL password file or a short-lived process environment; never put it in command history/arguments. Example after securely setting `PGPASSWORD` in that operator terminal:

```powershell
.\.venv\Scripts\python.exe database/migrate.py apply --psql 'C:\Program Files\PostgreSQL\18\bin\psql.exe' --host 127.0.0.1 --port 5432 --database adaptive_mcq --user adaptive_mcq_owner
```

5. Apply **all 15 module grant files** as the owner. In PowerShell, from the project root, with the same private process password:

```powershell
$mcqModules = 'auth','teacher','student','material','rag','generator','verifier','validation','review','assessment','attempt','adaptive','feedback','analytics','evaluation'
foreach ($mcqModule in $mcqModules) {
    & 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U adaptive_mcq_owner -d adaptive_mcq -v runtime_role=adaptive_mcq_app -f "database/$($mcqModule)_runtime_grants.sql"
    if ($LASTEXITCODE -ne 0) { throw 'Grant application failed. Do not start the app.' }
}
Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
```

These commands are operator instructions, not an automatically executed installation. Use the same migration/grant release for restore. `doctor` checks the existing backend readiness contract; full module workflows still need native acceptance testing.

## Prepare the application

Run commands from the `outputs/adaptive-mcq` project directory. Use the existing `.venv`; do not reinstall dependencies on every startup.

```powershell
.\.venv\Scripts\python.exe -m deployment.local configure
npm.cmd run build --prefix frontend
.\.venv\Scripts\python.exe -m deployment.local doctor
```

`configure` prompts for the existing restricted database login/password and generates a random JWT secret. It refuses to overwrite `.env`, does not create database roles and does not print secrets. Defaults are database `adaptive_mcq`, port 5432, API `127.0.0.1:8000`, frontend `http://localhost:5173`. Edit `.env` if the confirmed database port differs. Environment variables override `.env`; clear stale test/operator overrides before launching. Keep `GENERATOR_MODE=mock` and `VERIFIER_MODE=mock`.

Protect `.env`, `backend/uploads`, `data`, `backups` and `logs` using your own Windows account's file permissions. These folders must not be publicly shared. Source ignore rules prevent accidental source inclusion but are not encryption or an access-control boundary. Avoid symlinks/junctions in managed state directories; operator tools reject them.

`doctor` verifies database reachability, exact migration history, pgvector, non-owner runtime privileges and the backend authentication grants; checks frontend/build tools, free disk space and available ports; and hashes the prepared embedding snapshot without loading a model. It returns a nonzero status when prerequisites fail. The reported `backend_foundation` readiness scope does not prove every native classroom workflow has passed.

Provision the first teacher using the existing [operator account commands](authentication.md#teacher-enrollment-and-account-administration). Run them in a separate owner-credential terminal; never launch the normal API with that owner login. Students register through the website. There is no default password or seeded production account.

## Everyday startup and shutdown

1. Start the configured native PostgreSQL instance using Windows Services/pgAdmin or the operator-managed cluster process. Use the actual service/cluster, not a guessed name. Ensure no other copy of the application is running.
2. From the project folder:

```powershell
.\.venv\Scripts\python.exe -m deployment.local start
```

3. When the terminal prints **Ready**, open `http://localhost:5173`. Backend documentation is at `http://127.0.0.1:8000/docs`. Custom ports follow `.env`.
4. Press **Ctrl+C** in that terminal. The supervisor stops its frontend child and asks its backend child to finish gracefully. PostgreSQL and saved records remain. Logs are in `logs/` without access-log request URLs.

The launcher runs a prepared Vite preview and one backend worker. It refuses occupied ports, missing prerequisites and non-mock model modes. It never starts Ollama, installs packages, creates test data or silently substitutes PGlite. Frontend/API failures stop the companion child. A workspace OS lock prevents overlapping launcher/backup/restore operations. A stale lock file alone is harmless; the OS releases its lock when the process exits. If the supervisor is forcibly killed, the API's stdin closes and requests shutdown; the frontend may need manual stopping. Port checks then prevent a second accidental launch. Do not kill unrelated Python/Node processes by name.

This is a **single-computer college demonstration**, not a public production hosting service. Vite preview is appropriate for that bounded purpose. Real model evaluation remains **Hardware-validated model selection: pending**. Native recovery tests are small synthetic fixtures, not learning or AI-quality results.

## Backup

Stop the website first; leave PostgreSQL running. Use a trusted local database owner with access to all application tables. In a separate operator terminal, set `MCQ_OPERATOR_USER=adaptive_mcq_owner` and set `MCQ_OPERATOR_PASSWORD` from a hidden prompt. For example:

```powershell
$env:MCQ_OPERATOR_USER='adaptive_mcq_owner'
$mcqCredential=Get-Credential -UserName $env:MCQ_OPERATOR_USER -Message 'Local database operator password'
$env:MCQ_OPERATOR_PASSWORD=$mcqCredential.GetNetworkCredential().Password
.\.venv\Scripts\python.exe -m deployment.local backup
Remove-Item Env:MCQ_OPERATOR_PASSWORD
$mcqCredential=$null
```

The operator environment is separate from the application's restricted database settings. Do not start the frontend/backend from that privileged terminal. No credentials appear in command arguments. Add `--pg-bin 'C:\path\to\PostgreSQL\bin'` when needed; use compatible PostgreSQL tools.

For this laptop's generated owner credentials, the operator can load them without printing them:

```powershell
$mcqPrivate = Get-Content -LiteralPath data/native-postgres/operator.json -Raw | ConvertFrom-Json
$env:MCQ_OPERATOR_USER='adaptive_mcq_owner'
$env:MCQ_OPERATOR_PASSWORD=$mcqPrivate.owner_password
.\.venv\Scripts\python.exe -m deployment.local backup
Remove-Item Env:MCQ_OPERATOR_PASSWORD
$mcqPrivate=$null
```

For a restore rehearsal that recreates the extension, use `MCQ_OPERATOR_USER=mcq_local_admin` and the private `admin_password` in a separate operator terminal. To create a new, uniquely named empty restore target in this project's cluster, use the existing helper, for example `.\.venv\Scripts\python.exe -c "from deployment.native import credentials, create_database; create_database(credentials(), 'adaptive_mcq_restore_trial')"`. It fails if the name already exists. Keep the normal application stopped, follow the restore checks below, and clear the password environment afterward.

Backup takes SHARE locks on application/ledger tables, exports a repeatable-read snapshot for `pg_dump`, and copies only referenced PDFs after verifying their sizes/hashes. All relevant writers must be stopped; external administrator writes or filesystem changes during backup are outside the supported workflow. Missing/corrupt referenced files fail backup. Unreferenced files are counted and left in place. A final `manifest.json` appears only after completion; a directory without it is an incomplete backup, never a success.

Bundles contain `database.dump`, referenced `uploads/*.pdf` and checksums/history. They **contain private educational records and password hashes**. They exclude `.env`, runtime/operator passwords, model files, source code and logs. Retain the matching source/dependency lockfiles and prepared embedding snapshot separately. Keep a protected offline copy on a different physical device if available; another folder on the same disk does not protect against disk failure. Retention/deletion is manual; tooling never silently deletes old backups.

```powershell
.\.venv\Scripts\python.exe -m deployment.local verify-backup --bundle 'backups/<bundle-folder>'
```

This checks file inventory/checksums, not recoverability. Restore a trusted local archive to rehearse recovery. PostgreSQL warns that restoring a dump executes SQL from its source; checksums do not make an untrusted archive safe. See [pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html) and [pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html).

## Non-overwriting restore rehearsal

1. Stop the website. Verify the backup. With your PostgreSQL administrator, create a **new empty database**, such as `adaptive_mcq_restore_20261015`, owned by `adaptive_mcq_owner`. Restrict CONNECT as for the original database, granting the runtime role access. Do not precreate application tables or the vector extension; the archive includes extension creation. The extension files must be installed. The restore operator needs permission to recreate the extension; use a trusted administrator for the rehearsal if necessary, never the runtime login.
2. Set the short-lived `MCQ_OPERATOR_*` credentials as above. Run:

```powershell
.\.venv\Scripts\python.exe -m deployment.local restore --bundle 'backups/<bundle-folder>' --target-database adaptive_mcq_restore_20261015
```

The command refuses the configured/source database, a nonempty target, other target sessions or an existing staging folder. It restores in one database transaction, preserving original object owners but excluding archive ACLs. The original owner roles must already exist (recreate them with new private passwords on a replacement machine); restoring through an administrator must not turn every application security-definer function into an administrator-owned function. It reapplies the 15 runtime-grant files, revokes restored authentication sessions, compares restored PDF metadata and verifies staged file hashes. It checks runtime readiness against the new database. PDFs go to `data/recovery/<target-database>/`; the live upload folder and `.env` stay untouched. A failure leaves its separate output for operator inspection and returns a nonzero status. Grants/session changes and file copies happen after the archive transaction; their failure does not roll back an already restored database, so never treat a partial target as ready.

3. A passing rehearsal is not an automatic switch. Before switching, preserve the existing `.env`, database and complete uploads folder. With application services stopped, have the operator select the restored database in `.env` and copy the verified PDFs (not `recovery-report.json`) into a separate prepared replacement upload folder. Only replace `backend/uploads` after verifying its complete inventory; preserve the old folder. Never merge a partial restore into live data. Run `reconcile` and `doctor`, then sign in again and verify teacher/student history, reference-code admission, saved attempts, feedback and source previews. Existing JWT sessions have been revoked; passwords remain those in the archive. Keep the old database for rollback until review passes.

The controlled live cutover is an explicit operator step. No restore tool drops a database, runs `--clean`, deletes user uploads or overwrites the active configuration. Full native application backup/restore rehearsal passed with synthetic records and three PDFs. No live cutover of real user records was performed or is automatic.

## Crash and upload reconciliation

After an interrupted upload or uncertain commit, stop the application and run (with operator credentials):

```powershell
.\.venv\Scripts\python.exe -m deployment.local reconcile
```

The read-only report lists missing/corrupt referenced PDFs and unreferenced files. A crash before database commit can leave an orphan PDF; a successful but unacknowledged commit may leave a legitimate referenced file. Therefore **do not delete files merely because a request failed**. Keep unreferenced files until an operator investigates and a verified backup exists. Restore a missing/corrupt referenced PDF only from matching verified evidence. There is no automatic orphan cleanup or fabricated replacement content.

After an API-only crash, restart with the supervisor and sign in. Saved answers are server-side; retry an uncertain submission using the existing application flow. After an abrupt database stop, allow PostgreSQL's recovery, then run doctor/reconcile and application checks. Native acceptance verified unchanged application-table fingerprints, saved PDF metadata and source preview after an immediate database stop/restart. It does not establish exhaustive transaction races, physical disk durability or whole-machine/power-loss recovery.

## Troubleshooting and acceptance

| Symptom | Action |
|---|---|
| Missing database_password / jwt_secret | Configure `.env` once; check process overrides without printing secrets |
| Database unavailable | Confirm the intended instance, loopback port and SCRAM credentials |
| pgvector missing | Install the compatible extension; do not bypass migration 002 |
| Schema mismatch | Use the matching checkout; back up before applying migrations; never edit applied SQL |
| Unsafe runtime role | Use the restricted application login, not the owner/admin |
| Missing auth permissions | Apply all module grants as the trusted owner and rerun checks |
| Occupied port | Identify the owning instance; do not terminate unrelated services |
| Missing embedding snapshot | Prepare the pinned snapshot separately; startup never downloads it |
| Incomplete backup/restore | Preserve output for inspection, use a new destination for the next rehearsal |

Phase 22 native acceptance is recorded in the [completion report](phase-22-completion.md). Browser runs blocked external requests and observed none; model offline flags and local dependencies were used. The laptop's network adapter was not physically disabled. No LLM or fresh embedding inference was run. The crash-acceptance script refuses to run once the normal database contains accounts; use a separate test cluster for future crash experiments. Keep real account data out of synthetic fixtures.
