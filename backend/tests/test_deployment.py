import hashlib
import json
import socket
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

import pytest
from deployment import local

from backend.app.config import Settings
from database.migrate import inventory


@pytest.fixture
def bundle(tmp_path):
    folder = tmp_path / "bundle"
    (folder / "uploads").mkdir(parents=True)
    pdf = b"%PDF- synthetic fixture"
    key = "a" * 32 + ".pdf"
    (folder / "uploads" / key).write_bytes(pdf)
    (folder / "database.dump").write_bytes(b"fixture-only-archive")
    manifest = {
        "format": 1,
        "source_database": "adaptive_mcq",
        "migration_history": {n: h for n, h, _ in inventory()},
        "database_sha256": local.digest(folder / "database.dump"),
        "documents": [{"key": key, "size": len(pdf), "sha256": hashlib.sha256(pdf).hexdigest()}],
    }
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return folder


def test_backup_inventory_is_verified_without_database_access(bundle):
    assert local.verify_bundle(bundle)["format"] == 1


@pytest.mark.parametrize(
    "damage", ["dump", "pdf", "missing", "extra", "traversal", "duplicate", "history"]
)
def test_recovery_rejects_corrupt_or_unsafe_bundle(bundle, damage):
    manifest_file = bundle / "manifest.json"
    manifest = json.loads(manifest_file.read_text())
    pdf = bundle / "uploads" / manifest["documents"][0]["key"]
    if damage == "dump":
        (bundle / "database.dump").write_bytes(b"changed")
    elif damage == "pdf":
        pdf.write_bytes(b"changed")
    elif damage == "missing":
        pdf.unlink()
    elif damage == "extra":
        (bundle / "uploads" / "extra.pdf").write_bytes(b"extra")
    elif damage == "traversal":
        manifest["documents"][0]["key"] = "../private.pdf"
    elif damage == "duplicate":
        manifest["documents"].append(manifest["documents"][0])
    elif damage == "history":
        manifest["migration_history"] = {}
    manifest_file.write_text(json.dumps(manifest))
    with pytest.raises(local.OperationError):
        local.verify_bundle(bundle)


def test_reconciliation_reports_orphans_but_never_deletes(bundle):
    manifest = local.verify_bundle(bundle)
    orphan = bundle / "uploads" / "orphan.pdf"
    orphan.write_bytes(b"possibly interrupted upload")
    rows = [(d["key"], d["sha256"], d["size"]) for d in manifest["documents"]]
    report = local.inspect_uploads(rows, bundle / "uploads")
    assert report == {"referenced": 1, "missing": [], "corrupt": [], "unreferenced": ["orphan.pdf"]}
    assert orphan.exists()


@pytest.mark.parametrize("path", ["../outside", "C:/outside", "../../secret"])
def test_paths_cannot_escape_state(tmp_path, path):
    with pytest.raises(local.OperationError):
        local.inside(tmp_path, path)


def test_operator_lock_survives_stale_file_and_blocks_overlap(tmp_path):
    with local.operation_lock(tmp_path):
        with pytest.raises(local.OperationError):
            with local.operation_lock(tmp_path):
                pass
    with local.operation_lock(tmp_path):
        assert (tmp_path / "data/operator.lock").exists()


def test_occupied_port_is_not_reused(settings):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        configured = settings.model_copy(update={"api_port": listener.getsockname()[1]})
        with pytest.raises(local.OperationError, match="occupied"):
            local.assert_ports_free(configured)


def test_restore_refuses_live_database_before_any_connection(settings, bundle, monkeypatch):
    monkeypatch.setattr(local, "connection", lambda *a, **k: pytest.fail("must not connect"))
    with pytest.raises(local.OperationError, match="live database"):
        local.restore(settings, "unused", bundle, settings.database_name)


def test_pg_environment_cannot_redirect_to_remote_or_expose_argv(settings, monkeypatch):
    monkeypatch.setenv("PGSERVICE", "unexpected")
    monkeypatch.setenv("PGHOSTADDR", "203.0.113.7")
    monkeypatch.setenv("PGOPTIONS", "-c statement_timeout=0")
    monkeypatch.setenv("MCQ_OPERATOR_USER", "local_operator")
    monkeypatch.setenv("MCQ_OPERATOR_PASSWORD", "private-fixture")
    result = local.pg_environment(settings)
    assert result["PGHOSTADDR"] == "127.0.0.1"
    assert "PGSERVICE" not in result and "PGOPTIONS" not in result
    assert result["PGPASSWORD"] == "private-fixture"


def test_native_connection_omits_empty_service_and_rejects_inherited_service(settings, monkeypatch):
    captured = {}
    monkeypatch.setattr(local.psycopg, "connect", lambda **kwargs: captured.update(kwargs))
    local.connection(settings)
    assert "service" not in captured
    assert captured["hostaddr"] == "127.0.0.1"
    monkeypatch.setenv("PGSERVICE", "unexpected")
    with pytest.raises(local.OperationError, match="PGSERVICE"):
        local.connection(settings)


def test_configuration_is_non_overwriting_and_secrets_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(local, "ROOT", tmp_path)
    (tmp_path / ".env.example").write_text(
        "DATABASE_USER=adaptive_mcq_app\nDATABASE_NAME=adaptive_mcq\nDATABASE_PASSWORD=\nJWT_SECRET=\n"
    )
    monkeypatch.setattr("builtins.input", lambda message: "")
    password = "local ' quoted \\ password # with spaces"
    monkeypatch.setattr(local.getpass, "getpass", lambda message: password)
    local.configure()
    configured = Settings(_env_file=tmp_path / ".env")
    assert configured.database_password.get_secret_value() == password
    assert len(configured.jwt_secret.get_secret_value()) >= 32
    content = (tmp_path / ".env").read_bytes()
    with pytest.raises(local.OperationError, match="not be overwritten"):
        local.configure()
    assert (tmp_path / ".env").read_bytes() == content


def test_start_refuses_failed_readiness_without_spawning(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(local, "ROOT", tmp_path)
    monkeypatch.setattr(local, "doctor", lambda s: {"deployment_ready": False})
    monkeypatch.setattr(local.subprocess, "Popen", lambda *a, **k: pytest.fail("must not launch"))
    with pytest.raises(local.OperationError, match="prerequisites"):
        local.start(settings)


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0]


@pytest.mark.parametrize("fail_dump", [False, True])
def test_backup_snapshot_pdfs_and_incomplete_output(settings, tmp_path, monkeypatch, fail_dump):
    monkeypatch.setattr(local, "ROOT", tmp_path)
    monkeypatch.setattr(local, "assert_ports_free", lambda s: None)
    uploads = tmp_path / "backend/uploads"
    uploads.mkdir(parents=True)
    key = "b" * 32 + ".pdf"
    (uploads / key).write_bytes(b"%PDF-fixture")
    (uploads / "orphan.pdf").write_bytes(b"orphan retained")
    row = (key, local.digest(uploads / key), (uploads / key).stat().st_size)
    commands = []

    class Connection:
        def execute(self, query):
            query = str(query)
            commands.append(query)
            if "schemaname,tablename" in query:
                return FakeResult([("mcq", "documents")])
            if "SELECT tablename" in query:
                return FakeResult([("documents",)])
            if "pg_export_snapshot" in query:
                return FakeResult([("00000001-1",)])
            if "SELECT version,checksum" in query:
                return FakeResult([(n, h) for n, h, _ in inventory()])
            if "storage_key" in query:
                return FakeResult([row])
            return FakeResult([])

    @contextmanager
    def connect(*args, **kwargs):
        yield Connection()

    def dump(bin_dir, tool, settings, arguments):
        assert tool == "pg_dump"
        assert "--snapshot=00000001-1" in arguments
        assert any("LOCK TABLE" in command for command in commands)
        assert any("REPEATABLE READ" in command for command in commands)
        if fail_dump:
            raise local.OperationError("pg_dump failed")
        path = next(arg.removeprefix("--file=") for arg in arguments if arg.startswith("--file="))
        Path(path).write_bytes(b"synthetic archive")

    monkeypatch.setattr(local, "connection", connect)
    monkeypatch.setattr(local, "pg_tool", dump)
    if fail_dump:
        with pytest.raises(local.OperationError, match="pg_dump"):
            local.backup(settings, "unused")
        assert not list((tmp_path / "backups").glob("*/manifest.json"))
    else:
        folder = local.backup(settings, "unused")
        manifest = local.verify_bundle(folder)
        assert manifest["unreferenced_files_excluded"] == 1
        assert manifest["configuration_secrets_included"] is False
    assert (uploads / "orphan.pdf").exists()


def test_restore_refuses_nonempty_target_before_running_restore(
    settings, tmp_path, bundle, monkeypatch
):
    monkeypatch.setattr(local, "ROOT", tmp_path)
    monkeypatch.setattr(local, "assert_ports_free", lambda s: None)

    class Connection:
        def execute(self, query):
            return FakeResult([(1,)])

    @contextmanager
    def connect(*args, **kwargs):
        yield Connection()

    monkeypatch.setattr(local, "connection", connect)
    monkeypatch.setattr(local, "pg_tool", lambda *args: pytest.fail("must not restore"))
    with pytest.raises(local.OperationError, match="empty database"):
        local.restore(settings, "unused", bundle, "separate_restore")


def test_restore_preserves_owners_and_never_cleans_live_database(
    settings, tmp_path, bundle, monkeypatch
):
    monkeypatch.setattr(local, "ROOT", tmp_path)
    monkeypatch.setattr(local, "assert_ports_free", lambda s: None)

    class Connection:
        def execute(self, query):
            return FakeResult([(0,)])

    @contextmanager
    def connect(*args, **kwargs):
        assert kwargs["database"] == "separate_restore"
        yield Connection()

    def intercept(bin_dir, tool, settings, arguments):
        assert tool == "pg_restore"
        assert "--single-transaction" in arguments
        assert "--exit-on-error" in arguments
        assert "--no-privileges" in arguments
        assert "--dbname=separate_restore" in arguments
        assert not {"--clean", "--create", "--no-owner"}.intersection(arguments)
        raise local.OperationError("Intentional simulated restore failure")

    monkeypatch.setattr(local, "connection", connect)
    monkeypatch.setattr(local, "pg_tool", intercept)
    with pytest.raises(local.OperationError, match="simulated"):
        local.restore(settings, "unused", bundle, "separate_restore")
    assert not (tmp_path / "backend/uploads").exists()
    assert not (tmp_path / ".env").exists()
    assert not (tmp_path / "data/recovery/separate_restore/recovery-report.json").exists()


@pytest.mark.integration
@pytest.mark.skipif(
    __import__("os").getenv("MCQ_RUN_DB_TESTS") != "1", reason="Explicit local database tests only"
)
def test_supervised_stack_serves_local_build_and_stops_both_children(postgres_fixture, monkeypatch):
    port = postgres_fixture()
    ports = []
    for _ in range(2):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            ports.append(probe.getsockname()[1])
    settings = Settings(
        _env_file=None,
        database_port=port,
        database_user="phase3_runtime",
        database_password="fixture-password",
        jwt_secret="fixture-only-secret-not-for-real-use-12345",
        api_port=ports[0],
        frontend_origin=f"http://127.0.0.1:{ports[1]}",
    )
    for key in ("database_port", "database_user", "api_port", "frontend_origin"):
        monkeypatch.setenv(key.upper(), str(getattr(settings, key)))
    monkeypatch.setenv("DATABASE_PASSWORD", settings.database_password.get_secret_value())
    monkeypatch.setenv("JWT_SECRET", settings.jwt_secret.get_secret_value())
    opener = build_opener(ProxyHandler({}))
    original_sleep = time.sleep
    observed = []

    def stop_after_ready(delay):
        if delay == 0.5:
            with opener.open(
                settings.frontend_origin + "/api/v1/health/ready", timeout=5
            ) as response:
                assert json.load(response)["status"] == "ready"
            with opener.open(settings.frontend_origin, timeout=5) as response:
                assert "script-src 'self'" in response.headers["Content-Security-Policy"]
                assert b"<html" in response.read()
            observed.append(True)
            raise KeyboardInterrupt
        original_sleep(delay)

    monkeypatch.setattr(local.time, "sleep", stop_after_ready)
    local.start(settings)
    assert observed == [True]
    local.assert_ports_free(settings)
