"""Bounded isolated native PostgreSQL probe. Never opens the installed service data."""

import json
import os
import secrets
import socket
import subprocess
import sys
from pathlib import Path

import psycopg

from backend.app.config import PROJECT_ROOT
from database.migrate import render


def main():
    base = PROJECT_ROOT / "data" / ("native-probe-" + secrets.token_hex(6))
    base.mkdir(parents=True)
    pg = Path("C:/Program Files/PostgreSQL/18/bin")
    cluster = base / "cluster"
    password = secrets.token_urlsafe(32)
    pwfile = base / "init-password"
    pwfile.write_text(password, encoding="utf-8")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("PG")}
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    report = {
        "scope": "isolated native PostgreSQL; no existing service changes",
        "checks": {},
    }

    def run(tool, args, timeout=45):
        # Postmaster can inherit handles; pipe EOF is not a process-liveness signal.
        with (base / (tool + "-output.log")).open("ab") as output:
            result = subprocess.run(
                [str(pg / (tool + ".exe")), *map(str, args)],
                env=env,
                stdout=output,
                stderr=output,
                timeout=timeout,
                check=False,
                creationflags=flags,
            )
        if result.returncode:
            raise RuntimeError(tool + " failed; local diagnostic log retained")
        print(tool + " completed", flush=True)

    def connect(user="phase22_operator", secret=password, database="postgres"):
        return psycopg.connect(
            host="127.0.0.1",
            hostaddr="127.0.0.1",
            port=port,
            dbname=database,
            user=user,
            password=secret,
            connect_timeout=3,
            sslmode="disable",
            options="-c statement_timeout=10000 -c lock_timeout=2000",
        )

    started = False
    try:
        run(
            "initdb",
            [
                "-D",
                cluster,
                "-U",
                "phase22_operator",
                "--pwfile",
                pwfile,
                "--auth-host=scram-sha-256",
                "--auth-local=scram-sha-256",
                "--encoding=UTF8",
                "--locale=C",
                "--no-instructions",
            ],
            timeout=90,
        )
        pwfile.unlink()
        with (cluster / "postgresql.conf").open("a", encoding="utf-8") as stream:
            stream.write(
                f"\nlisten_addresses='127.0.0.1'\nport={port}\nshared_buffers='32MB'\nmax_connections=12\nwork_mem='1MB'\n"
            )
        run(
            "pg_ctl",
            ["-D", cluster, "-l", base / "postgres.log", "-w", "-t", "20", "start"],
        )
        started = True
        report["checks"]["native_start"] = "passed"
        with connect() as conn:
            report["server_version"] = conn.info.server_version
            vector = conn.execute(
                "SELECT default_version FROM pg_available_extensions WHERE name='vector'"
            ).fetchone()
            report["checks"]["pgvector_available"] = "present" if vector else "missing"
            conn.execute(
                "CREATE ROLE phase22_reader LOGIN PASSWORD 'probe-only-runtime-password' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT"
            )
            conn.execute(
                "CREATE TABLE public.recovery_probe(id integer PRIMARY KEY, value text)"
            )
            conn.execute(
                "INSERT INTO public.recovery_probe VALUES(1,'committed fixture')"
            )
            conn.execute("GRANT SELECT ON public.recovery_probe TO phase22_reader")
        try:
            connect("phase22_reader", "incorrect-password")
            raise AssertionError("Wrong password accepted")
        except psycopg.OperationalError:
            report["checks"]["scram_wrong_password_denied"] = "passed"
        with connect("phase22_reader", "probe-only-runtime-password") as conn:
            assert (
                conn.execute("SELECT value FROM public.recovery_probe").fetchone()[0]
                == "committed fixture"
            )
            try:
                conn.execute("DELETE FROM public.recovery_probe")
                raise AssertionError("Restricted role wrote data")
            except psycopg.errors.InsufficientPrivilege:
                report["checks"]["native_role_permissions"] = "passed"
        with connect() as first, connect() as second:
            assert first.info.backend_pid != second.info.backend_pid
            first.execute(
                "UPDATE public.recovery_probe SET value='uncommitted' WHERE id=1"
            )
            assert (
                second.execute(
                    "SELECT value FROM public.recovery_probe WHERE id=1"
                ).fetchone()[0]
                == "committed fixture"
            )
            first.rollback()
            report["checks"]["independent_connection_isolation"] = "passed"
        run("pg_ctl", ["-D", cluster, "-m", "immediate", "-w", "-t", "20", "stop"])
        started = False
        run(
            "pg_ctl",
            ["-D", cluster, "-l", base / "postgres.log", "-w", "-t", "20", "start"],
        )
        started = True
        with connect() as conn:
            assert (
                conn.execute("SELECT value FROM public.recovery_probe").fetchone()[0]
                == "committed fixture"
            )
            report["checks"]["native_immediate_stop_recovery"] = "passed"
        env.update(
            PGHOST="127.0.0.1",
            PGHOSTADDR="127.0.0.1",
            PGPORT=str(port),
            PGUSER="phase22_operator",
            PGPASSWORD=password,
            PGCONNECT_TIMEOUT="3",
        )
        run("pg_dump", ["-w", "-Fc", "-d", "postgres", "-f", base / "fixture.dump"])
        with connect() as conn:
            conn.autocommit = True
            conn.execute("CREATE DATABASE phase22_restore")
        run(
            "pg_restore",
            [
                "-w",
                "--single-transaction",
                "--exit-on-error",
                "-d",
                "phase22_restore",
                base / "fixture.dump",
            ],
        )
        with connect(database="phase22_restore") as conn:
            assert (
                conn.execute("SELECT value FROM public.recovery_probe").fetchone()[0]
                == "committed fixture"
            )
            report["checks"]["native_dump_restore_fixture"] = "passed"
        if not vector:
            with connect() as conn:
                try:
                    conn.execute(render())
                    raise AssertionError("Migrations accepted missing vector")
                except psycopg.Error:
                    conn.rollback()
                    assert (
                        conn.execute("SELECT to_regnamespace('mcq')").fetchone()[0]
                        is None
                    )
                    report["checks"]["missing_vector_migrations_roll_back"] = "passed"
        report["full_application_deployment"] = (
            "blocked: pgvector unavailable"
            if not vector
            else "not tested by this primitive probe"
        )
    except (OSError, RuntimeError, subprocess.SubprocessError, psycopg.Error) as exc:
        report["failure"] = type(exc).__name__
    finally:
        pwfile.unlink(missing_ok=True)
        if started or (cluster / "postmaster.pid").exists():
            run("pg_ctl", ["-D", cluster, "-m", "fast", "-w", "-t", "20", "stop"])
        report["cluster_stopped"] = not (cluster / "postmaster.pid").exists()
        (base / "report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, indent=2))
        print("Evidence directory:", base)
    return 0 if "failure" not in report else 2


if __name__ == "__main__":
    raise SystemExit(main())
