"""Manage this project's own native PostgreSQL cluster, never the installed service."""

import argparse
import json
import os
import re
import secrets
import socket
import subprocess
import sys
from pathlib import Path

import psycopg
from psycopg import sql

from backend.app.config import PROJECT_ROOT
from database.migrate import render
from deployment.local import GRANTS, NO_WINDOW, OperationError, inside

BASE = PROJECT_ROOT / "data/native-postgres"
PG = Path("C:/Program Files/PostgreSQL/18/bin")


def run(tool, arguments, timeout=90):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("PG")}
    with (BASE / "operator.log").open("ab") as output:
        result = subprocess.run(
            [str(PG / (tool + ".exe")), *map(str, arguments)],
            env=env,
            stdout=output,
            stderr=output,
            timeout=timeout,
            check=False,
            creationflags=NO_WINDOW,
        )
    if result.returncode:
        raise OperationError(
            f"Native {tool} failed. Inspect data/native-postgres/operator.log."
        )


def private_acl(path):
    # Keep private credentials/cluster files out of inherited broad read grants.
    identity = subprocess.run(
        ["whoami"],
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
        creationflags=NO_WINDOW,
    ).stdout.strip()
    directory = Path(path).is_dir()
    suffix = "(OI)(CI)F" if directory else "F"
    subprocess.run(
        [
            "icacls",
            str(path),
            "/inheritance:r",
            "/grant:r",
            f"{identity}:{suffix}",
            f"*S-1-5-18:{suffix}",
            f"*S-1-5-32-544:{suffix}",
        ],
        capture_output=True,
        timeout=15,
        check=True,
        creationflags=NO_WINDOW,
    )


def credentials():
    return json.loads(inside(BASE, "operator.json").read_text(encoding="utf-8"))


def connect(config, database="postgres", owner=False):
    return psycopg.connect(
        host="127.0.0.1",
        hostaddr="127.0.0.1",
        port=config["port"],
        dbname=database,
        user="adaptive_mcq_owner" if owner else "mcq_local_admin",
        password=config["owner_password" if owner else "admin_password"],
        connect_timeout=5,
        sslmode="disable",
        options="-c statement_timeout=120000 -c lock_timeout=5000",
    )


def grants(conn, runtime="adaptive_mcq_app"):
    for module in GRANTS:
        content = (
            PROJECT_ROOT / "database" / f"{module}_runtime_grants.sql"
        ).read_text(encoding="utf-8")
        content = re.sub(r"^\\set.*$", "", content, flags=re.MULTILINE)
        content = re.sub(r"^\s*(BEGIN|COMMIT);\s*$", "", content, flags=re.MULTILINE)
        conn.execute(
            content.replace(':"runtime_role"', sql.Identifier(runtime).as_string(conn))
        )


def create_database(config, name):
    with connect(config) as conn:
        conn.autocommit = True
        conn.execute(
            sql.SQL("CREATE DATABASE {} OWNER adaptive_mcq_owner").format(
                sql.Identifier(name)
            )
        )
        conn.execute(
            sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(
                sql.Identifier(name)
            )
        )
        conn.execute(
            sql.SQL(
                "GRANT CONNECT ON DATABASE {} TO adaptive_mcq_owner,adaptive_mcq_app"
            ).format(sql.Identifier(name))
        )


def start():
    inside(BASE, "cluster")
    config = credentials()
    if (BASE / "cluster/postmaster.pid").exists():
        try:
            with connect(config) as conn:
                actual = Path(conn.execute("SHOW data_directory").fetchone()[0]).resolve()
                if actual != (BASE / "cluster").resolve():
                    raise OperationError(
                        "The listening database is not this project's cluster."
                    )
            print("The project database is already running.")
            return
        except psycopg.OperationalError:
            # A shutdown/reboot can leave a stale marker. PostgreSQL itself must
            # verify process ownership and recover; never delete the PID file.
            pass
    # pg_ctl start fails rather than taking over a different instance.
    run(
        "pg_ctl",
        [
            "-D",
            BASE / "cluster",
            "-l",
            BASE / "postgres.log",
            "-w",
            "-t",
            "30",
            "start",
        ],
    )


def stop(immediate=False):
    inside(BASE, "cluster")
    credentials()
    run(
        "pg_ctl",
        [
            "-D",
            BASE / "cluster",
            "-m",
            "immediate" if immediate else "fast",
            "-w",
            "-t",
            "30",
            "stop",
        ],
    )


def initialize():
    if BASE.exists() or (PROJECT_ROOT / ".env").exists():
        raise OperationError(
            "Native state or .env already exists; initialization refuses to overwrite it."
        )
    if not (PG.parent / "share/extension/vector.control").is_file():
        raise OperationError(
            "Install the compatible pgvector extension before initialization."
        )
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 55432))
    BASE.mkdir(parents=True)
    private_acl(BASE)
    config = {
        "port": 55432,
        "admin_password": secrets.token_urlsafe(40),
        "owner_password": secrets.token_urlsafe(40),
        "runtime_password": secrets.token_urlsafe(40),
    }
    (BASE / "operator.json").write_text(json.dumps(config), encoding="utf-8")
    pwfile = BASE / "init-password"
    pwfile.write_text(config["admin_password"], encoding="utf-8")
    try:
        run(
            "initdb",
            [
                "-D",
                BASE / "cluster",
                "-U",
                "mcq_local_admin",
                "--pwfile",
                pwfile,
                "--auth-host=scram-sha-256",
                "--auth-local=scram-sha-256",
                "--encoding=UTF8",
                "--locale=C",
                "--no-instructions",
            ],
        )
    finally:
        pwfile.unlink(missing_ok=True)
    with (BASE / "cluster/postgresql.conf").open("a", encoding="utf-8") as stream:
        stream.write(
            "\nlisten_addresses='127.0.0.1'\nport=55432\nshared_buffers='64MB'\nmax_connections=20\nwork_mem='2MB'\n"
        )
    start()
    with connect(config) as conn:
        for role, key in (
            ("adaptive_mcq_owner", "owner_password"),
            ("adaptive_mcq_app", "runtime_password"),
        ):
            conn.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
                ).format(sql.Identifier(role), sql.Literal(config[key]))
            )
    create_database(config, "adaptive_mcq")
    with connect(config, "adaptive_mcq") as conn:
        conn.execute("CREATE EXTENSION vector")
        conn.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
    with connect(config, "adaptive_mcq", owner=True) as conn:
        conn.execute(render())
        grants(conn)
    content = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    content = content.replace("DATABASE_PORT=5432", "DATABASE_PORT=55432")
    content = content.replace(
        "DATABASE_PASSWORD=\n", f"DATABASE_PASSWORD={config['runtime_password']}\n"
    )
    content = content.replace(
        "JWT_SECRET=\n", f"JWT_SECRET={secrets.token_urlsafe(48)}\n"
    )
    with (PROJECT_ROOT / ".env").open("x", encoding="utf-8") as stream:
        stream.write(content)
    private_acl(PROJECT_ROOT / ".env")
    print(
        "Initialized dedicated native database on 127.0.0.1:55432. Private credentials saved; no default website account created."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["init", "start", "stop", "status", "create-teacher"]
    )
    args = parser.parse_args()
    try:
        if args.command == "init":
            initialize()
        elif args.command == "start":
            start()
        elif args.command == "stop":
            stop()
        elif args.command == "create-teacher":
            config = credentials()
            email = input("Teacher email: ").strip()
            name = input("Teacher display name: ").strip()
            env = {
                **os.environ,
                "DATABASE_HOST": "127.0.0.1",
                "DATABASE_PORT": str(config["port"]),
                "DATABASE_NAME": "adaptive_mcq",
                "DATABASE_USER": "adaptive_mcq_owner",
                "DATABASE_PASSWORD": config["owner_password"],
            }
            # The existing operator CLI validates identity and prompts for the new
            # password twice. Owner credentials never enter the normal API config.
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "backend.manage",
                    "create-teacher",
                    "--email",
                    email,
                    "--name",
                    name,
                ],
                cwd=PROJECT_ROOT,
                env=env,
                check=False,
            )
            return result.returncode
        else:
            config = credentials()
            with connect(config) as conn:
                row = conn.execute(
                    "SELECT version(),current_setting('listen_addresses')"
                ).fetchone()
                print(
                    json.dumps(
                        {
                            "running": True,
                            "port": config["port"],
                            "version": row[0],
                            "listen": row[1],
                        }
                    )
                )
        return 0
    except (
        OSError,
        ValueError,
        psycopg.Error,
        subprocess.SubprocessError,
        OperationError,
    ):
        print(
            "Native operation did not complete. Inspect the local operator log; existing data was not deleted."
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
