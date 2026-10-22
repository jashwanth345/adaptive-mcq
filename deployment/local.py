"""Local deployment operations. Run with .venv/Scripts/python.exe -m deployment.local."""

import argparse
import getpass
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener

import psycopg
from psycopg import sql

from backend.app.config import PROJECT_ROOT, ConfigurationError, load_settings
from backend.app.database import Database
from backend.app.rag.model_files import verify_snapshot
from database.migrate import inventory

ROOT = PROJECT_ROOT
NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
GRANTS = (
    "auth",
    "teacher",
    "student",
    "material",
    "rag",
    "generator",
    "verifier",
    "validation",
    "review",
    "assessment",
    "attempt",
    "adaptive",
    "feedback",
    "analytics",
    "evaluation",
)


class OperationError(Exception):
    """Safe operator message, without connection strings or private document data."""


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def plain_name(value):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", value):
        raise OperationError("Use a plain database or role name.")
    return value


def inside(root, name):
    """Resolve only ordinary children; reject symlink/junction traversal."""
    root = Path(root).absolute()
    path = root / name
    if Path(name).is_absolute() or ".." in Path(name).parts:
        raise OperationError("Unsafe local path.")
    for part in (root, *root.parents, path, *path.parents):
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise OperationError(
                "Linked directories/files are not supported for local state."
            )
    if not path.resolve().is_relative_to(root.resolve()):
        raise OperationError("Local path escapes its directory.")
    return path


@contextmanager
def operation_lock(root=None):
    root = ROOT if root is None else root
    state = inside(root, "data")
    state.mkdir(exist_ok=True)
    path = inside(state, "operator.lock")
    with path.open("a+b") as stream:
        stream.seek(0)
        stream.write(b"0")
        stream.flush()
        stream.seek(0)
        try:
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise OperationError(
                "Another local startup or recovery operation is active."
            ) from None
        try:
            yield
        finally:
            stream.seek(0)
            if sys.platform == "win32":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def connection(settings, *, database=None, operator=False):
    # Explicit hostaddr defeats inherited libpq host/service routing.
    if os.getenv("PGSERVICE"):
        raise OperationError("Unset PGSERVICE before a local operator connection.")
    user = os.getenv("MCQ_OPERATOR_USER") if operator else settings.database_user
    password = (
        os.getenv("MCQ_OPERATOR_PASSWORD")
        if operator
        else settings.database_password.get_secret_value()
    )
    if not user or not password:
        raise OperationError(
            "Set MCQ_OPERATOR_USER and MCQ_OPERATOR_PASSWORD for this operator process."
        )
    plain_name(user)
    return psycopg.connect(
        host=settings.database_host,
        hostaddr=settings.database_host,
        port=settings.database_port,
        dbname=plain_name(database or settings.database_name),
        user=user,
        password=password,
        connect_timeout=5,
        sslmode="disable",
        options="-c statement_timeout=120000 -c lock_timeout=5000 -c timezone=UTC",
        application_name="adaptive_mcq_operator",
    )


def pg_environment(settings):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("PG")}
    user, password = os.getenv("MCQ_OPERATOR_USER"), os.getenv("MCQ_OPERATOR_PASSWORD")
    if not user or not password:
        raise OperationError(
            "Operator credentials are required in this process environment."
        )
    env.update(
        PGHOST=settings.database_host,
        PGHOSTADDR=settings.database_host,
        PGPORT=str(settings.database_port),
        PGUSER=plain_name(user),
        PGPASSWORD=password,
        PGCONNECT_TIMEOUT="5",
        PGSSLMODE="disable",
        PGCLIENTENCODING="UTF8",
    )
    return env


def pg_tool(bin_dir, tool, settings, arguments):
    executable = Path(bin_dir) / (tool + (".exe" if sys.platform == "win32" else ""))
    if not executable.is_file():
        raise OperationError(f"Missing PostgreSQL tool: {tool}.")
    result = subprocess.run(
        [str(executable), *arguments],
        env=pg_environment(settings),
        capture_output=True,
        check=False,
        timeout=180,
        creationflags=NO_WINDOW,
    )
    if result.returncode:
        # libpq/SQL errors can include private values; no raw child stderr here.
        raise OperationError(
            f"{tool} failed; operation incomplete. Check local credentials, version and privileges."
        )
    return result


def assert_ports_free(settings):
    front = urlsplit(settings.frontend_origin)
    for host, port in (
        (settings.api_host, settings.api_port),
        (front.hostname, front.port),
    ):
        family = socket.AF_INET6 if ":" in host else socket.AF_INET
        with socket.socket(family) as probe:
            if sys.platform == "win32":
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                probe.bind((host, port))
            except OSError:
                raise OperationError(
                    "A frontend/API port is occupied. Stop the existing application first."
                ) from None


def document_rows(conn):
    return conn.execute(
        "SELECT storage_key, sha256, byte_size FROM mcq.documents ORDER BY storage_key"
    ).fetchall()


def inspect_uploads(rows, directory):
    directory = inside(directory, ".")
    expected, missing, corrupt = set(), [], []
    for key, checksum, size in rows:
        if not re.fullmatch(r"[0-9a-f]{32}\.pdf", key):
            raise OperationError(
                "Unexpected stored PDF filename; operator inspection required."
            )
        expected.add(key)
        path = inside(directory, key)
        if not path.is_file():
            missing.append(key)
        elif path.stat().st_size != size or digest(path) != checksum:
            corrupt.append(key)
    orphans = []
    if directory.exists():
        for path in directory.iterdir():
            inside(directory, path.name)
            if path.name not in expected:
                orphans.append(path.name)
    return {
        "referenced": len(expected),
        "missing": missing,
        "corrupt": corrupt,
        "unreferenced": sorted(orphans),
    }


def doctor(settings):
    database = Database(settings)
    try:
        report = database.readiness()
    finally:
        database.close()
    report["frontend_build"] = (
        "present" if (ROOT / "frontend/dist/index.html").is_file() else "missing"
    )
    report["node"] = "present" if shutil.which("node") else "missing"
    report["vite"] = (
        "present"
        if (ROOT / "frontend/node_modules/vite/bin/vite.js").is_file()
        else "missing"
    )
    report["ai_mode"] = (
        "mock"
        if settings.generator_mode == settings.verifier_mode == "mock"
        else "local_ollama" if settings.generator_mode == settings.verifier_mode == "ollama"
        else "unsupported_mixed_modes"
    )
    report["free_storage_gib"] = round(shutil.disk_usage(ROOT).free / 1024**3, 2)
    report["model_validation"] = "pending; no inference performed"
    try:
        verify_snapshot()
        report["embedding_snapshot"] = "verified_files_only"
    except (OSError, ValueError, KeyError, TypeError):
        report["embedding_snapshot"] = "missing_or_invalid"
    try:
        assert_ports_free(settings)
        report["ports"] = "available"
    except OperationError:
        report["ports"] = "occupied"
    report["deployment_ready"] = (
        report["status"] == "ready"
        and report["frontend_build"] == "present"
        and report["node"] == report["vite"] == "present"
        and report["ai_mode"] in {"mock", "local_ollama"}
        and report["ports"] == "available"
        and report["embedding_snapshot"] == "verified_files_only"
    )
    return report


def configure():
    target = ROOT / ".env"
    if target.exists():
        raise OperationError(".env already exists; it will not be overwritten.")
    user = plain_name(
        input("Restricted database login [adaptive_mcq_app]: ").strip()
        or "adaptive_mcq_app"
    )
    database = plain_name(
        input("Database name [adaptive_mcq]: ").strip() or "adaptive_mcq"
    )
    password = getpass.getpass("Existing database login password: ")
    if not password or any(c in password for c in "\r\n\x00"):
        raise OperationError("Use a nonempty single-line password.")
    # Single-quoted dotenv values only require backslash and quote escaping.
    escaped = password.replace("\\", "\\\\").replace("'", "\\'")
    content = (ROOT / ".env.example").read_text(encoding="utf-8")
    content = content.replace("DATABASE_USER=adaptive_mcq_app", f"DATABASE_USER={user}")
    content = content.replace("DATABASE_NAME=adaptive_mcq", f"DATABASE_NAME={database}")
    content = content.replace(
        "DATABASE_PASSWORD=\n", f"DATABASE_PASSWORD='{escaped}'\n"
    )
    content = content.replace(
        "JWT_SECRET=\n", f"JWT_SECRET={secrets.token_urlsafe(48)}\n"
    )
    with target.open("x", encoding="utf-8") as stream:
        stream.write(content)
    print(
        "Created private .env. No database, role or model was created. Protect this file with your Windows account permissions."
    )


def start(settings):
    with operation_lock():
        report = doctor(settings)
        if not report["deployment_ready"]:
            print(json.dumps(report, indent=2))
            raise OperationError(
                "Startup prerequisites are not ready. Run doctor and follow docs/local-deployment.md."
            )
        env = os.environ.copy()
        env.update(
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
            HF_HUB_DISABLE_TELEMETRY="1",
            NODE_OPTIONS="--max-old-space-size=256",
            RAYON_NUM_THREADS="2",
        )
        # Credentials stay out of child argv and frontend environment.
        front_env = {
            k: v
            for k, v in env.items()
            if k.upper()
            not in {
                "DATABASE_PASSWORD",
                "JWT_SECRET",
                "MCQ_OPERATOR_PASSWORD",
                "PGPASSWORD",
            }
        }
        host = (
            f"[{settings.api_host}]" if ":" in settings.api_host else settings.api_host
        )
        front_env["LOCAL_API_ORIGIN"] = f"http://{host}:{settings.api_port}"
        front = urlsplit(settings.frontend_origin)
        log_dir = inside(ROOT, "logs")
        log_dir.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ-"
        ) + secrets.token_hex(3)
        api = ui = None
        opener = build_opener(ProxyHandler({}))
        with (
            (log_dir / f"api-{stamp}.log").open("x", encoding="utf-8") as api_log,
            (log_dir / f"frontend-{stamp}.log").open("x", encoding="utf-8") as ui_log,
        ):
            try:
                api = subprocess.Popen(
                    [sys.executable, "-m", "deployment.serve_api"],
                    cwd=ROOT,
                    env=env,
                    stdin=subprocess.PIPE,
                    stdout=api_log,
                    stderr=api_log,
                    text=True,
                    creationflags=NO_WINDOW,
                )
                deadline = time.monotonic() + 30
                while True:
                    try:
                        with opener.open(
                            front_env["LOCAL_API_ORIGIN"] + "/api/v1/health/ready",
                            timeout=3,
                        ) as response:
                            if json.load(response)["status"] == "ready":
                                break
                    except OSError:
                        pass
                    if api.poll() is not None or time.monotonic() >= deadline:
                        raise OperationError(
                            "Backend did not become ready; inspect the local API log."
                        )
                    time.sleep(0.2)
                ui = subprocess.Popen(
                    [
                        shutil.which("node"),
                        "node_modules/vite/bin/vite.js",
                        "preview",
                        "--host",
                        front.hostname,
                        "--port",
                        str(front.port),
                        "--strictPort",
                    ],
                    cwd=ROOT / "frontend",
                    env=front_env,
                    stdout=ui_log,
                    stderr=ui_log,
                    creationflags=NO_WINDOW,
                )
                deadline = time.monotonic() + 20
                while True:
                    try:
                        with opener.open(
                            settings.frontend_origin, timeout=2
                        ) as response:
                            if response.status == 200:
                                break
                    except OSError:
                        pass
                    if ui.poll() is not None or time.monotonic() >= deadline:
                        raise OperationError(
                            "Frontend did not start; inspect its local log."
                        )
                    time.sleep(0.2)
                print(
                    f"Ready: {settings.frontend_origin} | {report['ai_mode']} mode | Press Ctrl+C to stop.",
                    flush=True,
                )
                while api.poll() is None and ui.poll() is None:
                    time.sleep(0.5)
                raise OperationError(
                    "A child service stopped; both application services have been stopped."
                )
            except KeyboardInterrupt:
                print(
                    "Stopping application services; PostgreSQL and saved data are retained."
                )
            finally:
                try:
                    if ui is not None and ui.poll() is None:
                        ui.terminate()
                        try:
                            ui.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            ui.kill()
                            ui.wait(timeout=10)
                finally:
                    if api is not None and api.poll() is None:
                        try:
                            api.communicate("stop\n", timeout=45)
                        except (subprocess.TimeoutExpired, OSError):
                            api.kill()
                            api.wait(timeout=10)
                            print(
                                "Backend needed a forced stop. Run reconcile before restarting."
                            )


def backup(settings, bin_dir):
    with operation_lock():
        assert_ports_free(settings)
        base = inside(ROOT, "backups")
        base.mkdir(exist_ok=True)
        target = inside(
            base,
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")
            + secrets.token_hex(4),
        )
        target.mkdir()
        uploads = target / "uploads"
        uploads.mkdir()
        # Incomplete directories have no manifest and are never accepted for restore.
        with connection(settings, operator=True) as conn:
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            tables = conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname IN ('mcq','mcq_meta') ORDER BY schemaname,tablename"
            ).fetchall()
            if not tables:
                raise OperationError(
                    "Application schema is missing; no backup was produced."
                )
            # Block mutations across the snapshot and PDF copy, not just pg_dump's read window.
            names = conn.execute(
                "SELECT schemaname,tablename FROM pg_tables WHERE schemaname IN ('mcq','mcq_meta') ORDER BY schemaname,tablename"
            ).fetchall()
            conn.execute(
                sql.SQL("LOCK TABLE {} IN SHARE MODE").format(
                    sql.SQL(",").join(sql.Identifier(*name) for name in names)
                )
            )
            snapshot = conn.execute("SELECT pg_export_snapshot()").fetchone()[0]
            history = dict(
                conn.execute(
                    "SELECT version,checksum FROM mcq_meta.schema_migrations"
                ).fetchall()
            )
            if history != {n: h for n, h, _ in inventory()}:
                raise OperationError(
                    "Schema history does not match this checkout; backup with the matching application release."
                )
            rows = document_rows(conn)
            source = inside(ROOT, settings.upload_directory)
            state = inspect_uploads(rows, source)
            if state["missing"] or state["corrupt"]:
                raise OperationError(
                    "Referenced PDFs are missing or corrupt. Reconcile before backup."
                )
            pg_tool(
                bin_dir,
                "pg_dump",
                settings,
                [
                    "--no-password",
                    "--format=custom",
                    "--snapshot=" + snapshot,
                    "--file=" + str(target / "database.dump"),
                    "--dbname=" + settings.database_name,
                ],
            )
            for key, checksum, size in rows:
                shutil.copyfile(inside(source, key), uploads / key)
                if digest(uploads / key) != checksum:
                    raise OperationError(
                        "PDF changed during backup; bundle is incomplete."
                    )
        manifest = {
            "format": 1,
            "source_database": settings.database_name,
            "migration_history": history,
            "database_sha256": digest(target / "database.dump"),
            "documents": [{"key": k, "sha256": h, "size": s} for k, h, s in rows],
            "unreferenced_files_excluded": len(state["unreferenced"]),
            "configuration_secrets_included": False,
        }
        (target / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        print(f"Backup created: {target}. Rehearse restore before relying on it.")
        return target


def verify_bundle(bundle):
    bundle = inside(Path(bundle), ".")
    manifest = json.loads(inside(bundle, "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") != 1 or manifest.get("migration_history") != {
        n: h for n, h, _ in inventory()
    }:
        raise OperationError(
            "Backup format or migration history does not match this application."
        )
    if digest(inside(bundle, "database.dump")) != manifest["database_sha256"]:
        raise OperationError("Database backup checksum mismatch.")
    rows = [(d["key"], d["sha256"], d["size"]) for d in manifest["documents"]]
    if len({r[0] for r in rows}) != len(rows):
        raise OperationError("Duplicate PDF names in backup manifest.")
    result = inspect_uploads(rows, inside(bundle, "uploads"))
    if result["missing"] or result["corrupt"] or result["unreferenced"]:
        raise OperationError("PDF backup inventory/checksum mismatch.")
    return manifest


def restore(settings, bin_dir, bundle, target_database):
    plain_name(target_database)
    if target_database == settings.database_name:
        raise OperationError("Restore cannot target the configured live database.")
    with operation_lock():
        assert_ports_free(settings)
        manifest = verify_bundle(bundle)
        if target_database == manifest["source_database"]:
            raise OperationError("Restore cannot target the source database.")
        with connection(settings, database=target_database, operator=True) as conn:
            count = conn.execute(
                "SELECT count(*) FROM pg_namespace WHERE nspname NOT IN ('public','information_schema') AND nspname NOT LIKE 'pg_%'"
            ).fetchone()[0]
            objects = conn.execute(
                "SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace"
            ).fetchone()[0]
            routines = conn.execute(
                "SELECT count(*) FROM pg_proc WHERE pronamespace='public'::regnamespace"
            ).fetchone()[0]
            if count or objects or routines:
                raise OperationError(
                    "Restore target must be a separately created empty database."
                )
            others = conn.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()"
            ).fetchone()[0]
            if others:
                raise OperationError(
                    "Restore target has other sessions; close them first."
                )
        stage = inside(ROOT, "data/recovery")
        stage.mkdir(parents=True, exist_ok=True)
        destination = inside(stage, target_database)
        destination.mkdir()  # Never overwrite a previous rehearsal.
        # Trusted local archives only: checksums detect corruption, not malicious SQL.
        pg_tool(
            bin_dir,
            "pg_restore",
            settings,
            [
                "--no-password",
                "--exit-on-error",
                "--single-transaction",
                "--no-privileges",
                "--dbname=" + target_database,
                str(Path(bundle).resolve() / "database.dump"),
            ],
        )
        with connection(settings, database=target_database, operator=True) as conn:
            for module in GRANTS:
                body = (ROOT / "database" / f"{module}_runtime_grants.sql").read_text(
                    encoding="utf-8"
                )
                body = re.sub(r"^\\set.*$", "", body, flags=re.MULTILINE)
                body = re.sub(r"^\s*(BEGIN|COMMIT);\s*$", "", body, flags=re.MULTILINE)
                quoted = sql.Identifier(settings.database_user).as_string(conn)
                conn.execute(body.replace(':"runtime_role"', quoted))
            # Old browser sessions are never revived by restoring an archive.
            conn.execute(
                "UPDATE mcq.auth_sessions SET revoked_at=now() WHERE revoked_at IS NULL"
            )
            rows = document_rows(conn)
            if rows != [
                (d["key"], d["sha256"], d["size"]) for d in manifest["documents"]
            ]:
                raise OperationError(
                    "Restored document inventory does not match backup."
                )
        for item in manifest["documents"]:
            shutil.copyfile(
                inside(Path(bundle) / "uploads", item["key"]), destination / item["key"]
            )
        state = inspect_uploads(rows, destination)
        if state["missing"] or state["corrupt"]:
            raise OperationError(
                "Restored PDF verification failed; target is not ready."
            )
        restored = settings.model_copy(update={"database_name": target_database})
        db = Database(restored)
        try:
            ready = db.readiness()
        finally:
            db.close()
        result = {
            "database": target_database,
            "uploads_staging": str(destination),
            "readiness": ready,
            "live_database_changed": False,
            "sessions_revoked": True,
        }
        (destination / "recovery-report.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        print(json.dumps(result, indent=2))
        if ready["status"] != "ready":
            raise OperationError(
                "Restore completed but runtime readiness failed; do not switch the application."
            )
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "configure",
            "doctor",
            "start",
            "reconcile",
            "backup",
            "verify-backup",
            "restore",
        ],
    )
    parser.add_argument("--pg-bin", default="C:/Program Files/PostgreSQL/18/bin")
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--target-database")
    args = parser.parse_args()
    try:
        if args.command == "configure":
            configure()
            return 0
        if args.command == "verify-backup":
            if not args.bundle:
                raise OperationError("Specify --bundle.")
            verify_bundle(args.bundle)
            print(
                "Backup inventory and checksums pass. This is not a restore rehearsal."
            )
            return 0
        settings = load_settings()
        if args.command == "doctor":
            report = doctor(settings)
            print(json.dumps(report, indent=2))
            return 0 if report["deployment_ready"] else 2
        if args.command == "start":
            start(settings)
        elif args.command == "reconcile":
            with operation_lock():
                assert_ports_free(settings)
                with connection(settings, operator=True) as conn:
                    report = inspect_uploads(
                        document_rows(conn), inside(ROOT, settings.upload_directory)
                    )
                print(json.dumps(report, indent=2))
                print("Read-only report. No uploads were deleted or changed.")
                return 2 if report["missing"] or report["corrupt"] else 0
        elif args.command == "backup":
            backup(settings, args.pg_bin)
        elif args.command == "restore":
            if not args.bundle or not args.target_database:
                raise OperationError("Specify --bundle and --target-database.")
            restore(settings, args.pg_bin, args.bundle, args.target_database)
        return 0
    except (OperationError, ConfigurationError) as exc:
        print(str(exc), file=sys.stderr)
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        psycopg.Error,
        subprocess.SubprocessError,
    ):
        print(
            "Local operation failed; no success is claimed. Check prerequisites and the operator guide. Partial recovery output is retained for inspection.",
            file=sys.stderr,
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
