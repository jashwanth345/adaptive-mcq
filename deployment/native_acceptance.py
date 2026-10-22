"""Synthetic native application/recovery acceptance. No learner or model-quality claims."""

import json
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import psycopg
import pymupdf
from fastapi.testclient import TestClient
from psycopg import sql

from backend.app.config import PROJECT_ROOT, Settings
from backend.app.database import Database
from backend.app.main import create_app
from database.migrate import render
from deployment import local, native


def fingerprint(config, name):
    with native.connect(config, name, owner=True) as conn:
        tables = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname='mcq' AND tablename<>'auth_sessions' ORDER BY tablename"
        ).fetchall()
        return {
            table: conn.execute(
                sql.SQL(
                    "SELECT count(*),md5(coalesce(string_agg(row_to_json(t)::text,E'\\n' ORDER BY row_to_json(t)::text),'')) FROM mcq.{} t"
                ).format(sql.Identifier(table))
            ).fetchone()
            for (table,) in tables
        }


def main():
    config = native.credentials()
    with native.connect(config, "adaptive_mcq", owner=True) as conn:
        if conn.execute("SELECT count(*) FROM mcq.users").fetchone()[0]:
            raise RuntimeError(
                "Crash rehearsal requires an unused project database; use a separate test cluster once real accounts exist."
            )
    run_id = secrets.token_hex(5)
    name = "mcq_acceptance_" + run_id
    restored_name = "mcq_restore_" + run_id
    base = PROJECT_ROOT / "data/native-acceptance" / run_id
    uploads = base / "backend/uploads"
    uploads.mkdir(parents=True)
    (base / "database").mkdir()
    for module in local.GRANTS:
        shutil.copyfile(
            PROJECT_ROOT / "database" / f"{module}_runtime_grants.sql",
            base / "database" / f"{module}_runtime_grants.sql",
        )
    report = {
        "scope": "native synthetic application acceptance",
        "database": name,
        "real_ai_inference": False,
        "checks": [],
    }

    def passed(message):
        report["checks"].append(message)
        print("PASS: " + message, flush=True)
        (base / "report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )

    def child(arguments, logfile, env):
        with (base / logfile).open("w", encoding="utf-8") as stream:
            result = subprocess.run(
                arguments,
                cwd=PROJECT_ROOT,
                env=env,
                stdout=stream,
                stderr=stream,
                timeout=240,
                check=False,
                creationflags=local.NO_WINDOW,
            )
        if result.returncode:
            raise RuntimeError("Acceptance child failed: " + logfile)

    native.create_database(config, name)
    with native.connect(config, name) as conn:
        conn.execute("CREATE EXTENSION vector")
    with native.connect(config, name, owner=True) as conn:
        conn.execute(render())
        native.grants(conn)
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_port=config["port"],
        database_name=name,
        database_user="adaptive_mcq_app",
        database_password=config["runtime_password"],
        jwt_secret="native-fixture-only-" + secrets.token_hex(24),
    )
    db = Database(settings)
    try:
        assert db.readiness()["status"] == "ready"
    finally:
        db.close()
    with local.connection(settings) as conn:
        assert (
            conn.execute("SELECT '[1,0,0]'::vector <=> '[0,1,0]'::vector").fetchone()[0]
            == 1.0
        )
    passed(
        "All 12 migrations, pgvector and restricted runtime readiness on native PostgreSQL"
    )
    env = {
        **os.environ,
        "TEST_PYTHON": sys.executable,
        "MCQ_NATIVE_TEST_DATABASE": name,
        "MCQ_TEST_UPLOADS": str(uploads),
        "DATABASE_PORT": str(config["port"]),
        "DATABASE_PASSWORD": config["runtime_password"],
        "NODE_OPTIONS": "--max-old-space-size=256",
        "RAYON_NUM_THREADS": "2",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "E2E_OUTPUT": str(base / "browser"),
        "E2E_LIGHTWEIGHT": "1",
    }
    child([shutil.which("node"), "database/tests/native-seed.mjs"], "seed.log", env)
    passed(
        "Synthetic classroom fixture with real local PDF files prepared in a separate test database"
    )
    child(
        [shutil.which("node"), "frontend/tests/integration-e2e.mjs"],
        "classroom.log",
        env,
    )
    passed(
        "14 native browser classroom checks including saved answers, API restart, retry, analytics and quarantine"
    )
    app = create_app(settings)
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        app.state.materials.root = uploads
        credentials = {
            "email": "attempt.student@example.com",
            "password": "Fixture teacher 42!",
        }
        response = client.post("/api/v1/auth/login", json=credentials)
        assert response.status_code == 200, response.status_code
        token = response.json()["access_token"]
        headers = {"Authorization": "Bearer " + token}
        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.insert_text(
                (72, 72),
                "Transactions preserve atomic changes. Native PDF persistence fixture.",
            )
            body = pdf.tobytes()
        response = client.post(
            "/api/v1/materials?title=Native%20recovery%20PDF",
            content=body,
            headers={**headers, "Content-Type": "application/pdf"},
        )
        assert response.status_code == 201, response.status_code
        material = response.json()["id"]
        payload = {
            "material_ids": [material],
            "topic": "Transactions",
            "idempotency_key": str(uuid4()),
        }
        generated = client.post(
            "/api/v1/generator/drafts", json=payload, headers=headers
        )
        assert generated.status_code == 200, generated.text
        assert "mock" in generated.text
    passed(
        "Native authenticated PDF upload/extraction and labelled mock draft generation"
    )
    # Two independent application connections contend on the same native row.
    with (
        native.connect(config, name, owner=True) as first,
        native.connect(config, name, owner=True) as second,
    ):
        assert first.info.backend_pid != second.info.backend_pid
        first.execute("SELECT id FROM mcq.users ORDER BY id LIMIT 1 FOR UPDATE")
        second.execute("SET LOCAL lock_timeout='150ms'")
        try:
            second.execute("SELECT id FROM mcq.users ORDER BY id LIMIT 1 FOR UPDATE")
            raise AssertionError("Expected row contention")
        except psycopg.errors.LockNotAvailable:
            second.rollback()
        first.rollback()
    passed("Independent native transactions enforce row locks with bounded contention")
    before = fingerprint(config, name)
    native.stop(immediate=True)
    native.start()
    assert fingerprint(config, name) == before
    with TestClient(create_app(settings), base_url="http://127.0.0.1:8000") as client:
        response = client.get("/api/v1/materials/" + material, headers=headers)
        assert response.status_code == 200
    passed(
        "Immediate native database stop/restart preserves application rows and uploaded PDF metadata"
    )
    original_root = local.ROOT
    local.ROOT = base
    old_user, old_password = (
        os.environ.get("MCQ_OPERATOR_USER"),
        os.environ.get("MCQ_OPERATOR_PASSWORD"),
    )
    os.environ.update(
        MCQ_OPERATOR_USER="mcq_local_admin",
        MCQ_OPERATOR_PASSWORD=config["admin_password"],
    )
    try:
        bundle = local.backup(settings, native.PG)
        manifest = local.verify_bundle(bundle)
        assert len(manifest["documents"]) >= 3
        native.create_database(config, restored_name)
        result = local.restore(settings, native.PG, bundle, restored_name)
        assert result["readiness"]["status"] == "ready"
        assert fingerprint(config, restored_name) == fingerprint(config, name)
        with native.connect(config, restored_name) as conn:
            assert (
                conn.execute(
                    "SELECT count(*) FROM mcq.auth_sessions WHERE revoked_at IS NULL"
                ).fetchone()[0]
                == 0
            )
            assert (
                conn.execute(
                    "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_roles r ON r.oid=p.proowner WHERE n.nspname='mcq' AND r.rolsuper"
                ).fetchone()[0]
                == 0
            )
        restored_settings = settings.model_copy(update={"database_name": restored_name})
        restored_app = create_app(restored_settings)
        with TestClient(restored_app, base_url="http://127.0.0.1:8000") as client:
            restored_app.state.materials.root = Path(result["uploads_staging"])
            assert client.get("/api/v1/materials", headers=headers).status_code == 401
            response = client.post("/api/v1/auth/login", json=credentials)
            assert response.status_code == 200
            fresh = {"Authorization": "Bearer " + response.json()["access_token"]}
            assert (
                client.get("/api/v1/materials/" + material, headers=fresh).status_code
                == 200
            )
        passed(
            "Full database/PDF backup and separate native restore preserve all non-session table fingerprints and file hashes"
        )
        passed(
            "Restored sessions revoked; fresh sign-in/source preview works and function ownership remains non-administrative"
        )
    finally:
        local.ROOT = original_root
        for key, value in (
            ("MCQ_OPERATOR_USER", old_user),
            ("MCQ_OPERATOR_PASSWORD", old_password),
        ):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    report["status"] = "passed"
    report["browser_checks"] = 14
    report["restored_database"] = restored_name
    (base / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Evidence:", base)


if __name__ == "__main__":
    main()
