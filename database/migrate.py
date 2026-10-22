"""Forward-only SQL migrations using Python stdlib and PostgreSQL's psql client.

No packages, application secrets, .env auto-loading or cloud connections required.
Use a dedicated migration-owner login; never give the app database-owner rights.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys

MIGRATIONS = Path(__file__).resolve().parent / "migrations"


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def inventory(directory: Path = MIGRATIONS) -> list[tuple[str, str, str]]:
    result = []
    for path in sorted(directory.glob("*.sql")):
        if not re.fullmatch(r"[0-9]{3}_[a-z0-9_]+\.sql", path.name):
            raise ValueError(f"Invalid migration name: {path.name}")
        # Normalize platform line endings so checkout CRLF conversion is harmless.
        sql = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
        result.append((path.stem, hashlib.sha256(sql.encode()).hexdigest(), sql))
    prefixes = [name.split("_", 1)[0] for name, _, _ in result]
    if not result or prefixes != [f"{n:03d}" for n in range(1, len(result) + 1)]:
        raise ValueError("Migrations must have unique contiguous versions starting at 001")
    return result


def render(target: int | None = None, directory: Path = MIGRATIONS) -> str:
    migrations = inventory(directory)
    target = len(migrations) if target is None else target
    if target < 1 or target > len(migrations):
        raise ValueError("Target must name an existing positive migration number")
    manifest = ",\n".join(f"({literal(name)}, {literal(digest)})" for name, digest, _ in migrations[:target])
    sql = ["""BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '120s';
SELECT pg_advisory_xact_lock(173421, 2);
CREATE SCHEMA IF NOT EXISTS mcq_meta;
REVOKE ALL ON SCHEMA mcq_meta FROM PUBLIC;
CREATE TABLE IF NOT EXISTS mcq_meta.schema_migrations (
    version text PRIMARY KEY,
    checksum text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
);
REVOKE ALL ON mcq_meta.schema_migrations FROM PUBLIC;
CREATE TEMP TABLE mcq_migration_manifest (version text PRIMARY KEY, checksum text NOT NULL) ON COMMIT DROP;
""", "INSERT INTO mcq_migration_manifest VALUES " + manifest + ";", """
DO $history$
BEGIN
    IF EXISTS (SELECT 1 FROM mcq_meta.schema_migrations h LEFT JOIN mcq_migration_manifest m USING (version)
               WHERE m.version IS NULL OR h.checksum <> m.checksum) THEN
        RAISE EXCEPTION 'Unknown, changed, or newer migration history; no changes applied';
    END IF;
    IF EXISTS (SELECT 1 FROM mcq_migration_manifest m WHERE NOT EXISTS
       (SELECT 1 FROM mcq_meta.schema_migrations h WHERE h.version = m.version)
       AND EXISTS (SELECT 1 FROM mcq_meta.schema_migrations h WHERE h.version > m.version)) THEN
        RAISE EXCEPTION 'Migration history has a gap; no changes applied';
    END IF;
END $history$;
"""]
    for name, digest, body in migrations[:target]:
        tag = f"$migration_{digest}$"
        wrapper = f"$apply_{digest}$"
        if tag in body or wrapper in body:
            raise ValueError("Migration contains reserved delimiter")
        sql.append(f"""DO {wrapper}
BEGIN
    IF NOT EXISTS (SELECT 1 FROM mcq_meta.schema_migrations WHERE version = {literal(name)}) THEN
        EXECUTE {tag}{body}{tag};
        INSERT INTO mcq_meta.schema_migrations (version, checksum) VALUES ({literal(name)}, {literal(digest)});
    END IF;
END {wrapper};""")
    return "\n".join(sql) + "\nCOMMIT;\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "render", "apply"])
    parser.add_argument("--target", type=int, help="001/core only = 1; default all migrations")
    parser.add_argument("--psql", default="psql", help="Installed psql executable path")
    parser.add_argument("--host", choices=["127.0.0.1", "localhost", "::1"], default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--database", help="Explicit target database; required for apply")
    parser.add_argument("--user", help="Migration-owner PostgreSQL login; required for apply")
    args = parser.parse_args()
    try:
        sql = render(args.target)
        if args.command == "render":
            sys.stdout.write(sql)
        elif args.command == "plan":
            for name, digest, _ in inventory()[:args.target]:
                print(f"{name}  sha256:{digest}")
            print("Plan only: database history has not been inspected.")
        else:
            if not args.database or not args.user or not 1 <= args.port <= 65535:
                parser.error("apply requires --database, --user and a valid --port")
            # Forbid libpq connection-string expansion that could override loopback.
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,62}", args.database + ""):
                parser.error("Use a plain database name, not a connection string")
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,62}", args.user):
                parser.error("Use a plain database user name")
            env = os.environ.copy()
            for key in ("PGSERVICE", "PGSERVICEFILE", "PGHOSTADDR", "PGOPTIONS"):
                env.pop(key, None)
            env["PGCLIENTENCODING"] = "UTF8"
            env["PGCONNECT_TIMEOUT"] = "5"
            command = [args.psql, "-X", "-w", "--set=ON_ERROR_STOP=1", "--host", args.host,
                       "--port", str(args.port), "--dbname", args.database, "--username", args.user]
            result = subprocess.run(command, input=sql, text=True, encoding="utf-8", env=env, timeout=180)
            if result.returncode:
                print("Migration failed. The transaction was rolled back; inspect the error above.", file=sys.stderr)
                return result.returncode
            print("All selected migrations committed; existing matching versions were skipped.")
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"Migration did not complete: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
