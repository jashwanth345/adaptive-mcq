import json
import os
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener

from backend.app.config import PROJECT_ROOT, Settings


def child_environment():
    env = os.environ.copy()
    for key in Settings.model_fields:
        env.pop(key.upper(), None)
        env.pop(key.lower(), None)
    env.pop("PGSERVICE", None)
    return env


def test_launcher_fails_safely_with_blank_secrets():
    env = child_environment()
    env.update(DATABASE_PASSWORD="", JWT_SECRET="")
    result = subprocess.run(
        [sys.executable, "-m", "backend.app"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    assert result.returncode == 2
    assert "database_password" in result.stderr
    assert "jwt_secret" in result.stderr
    assert "Traceback" not in result.stderr


def test_real_http_server_starts_reports_dependency_failure_and_stops(tmp_path):
    # Keep a local port bound but not listening to guarantee no database service exists there.
    unavailable = socket.socket()
    unavailable.bind(("127.0.0.1", 0))
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        api_port = probe.getsockname()[1]
    env = child_environment()
    env.update(
        DATABASE_PASSWORD="fixture-not-a-real-db-password",
        JWT_SECRET="fixture-only-long-secret-1234567890123456789",
        DATABASE_PORT=str(unavailable.getsockname()[1]),
        API_PORT=str(api_port),
    )
    log_file = tmp_path / "server.log"
    opener = build_opener(ProxyHandler({}))
    with log_file.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "backend.app"],
            cwd=PROJECT_ROOT,
            env=env,
            stdout=log,
            stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        try:
            base = f"http://127.0.0.1:{api_port}"
            deadline = time.monotonic() + 12
            while True:
                try:
                    with opener.open(base + "/api/v1/health/live", timeout=1) as response:
                        assert json.load(response)["status"] == "alive"
                    break
                except URLError:
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise AssertionError("The local launcher did not become live") from None
                    time.sleep(0.1)
            with opener.open(base + "/docs", timeout=2) as response:
                assert response.status == 200
            try:
                opener.open(base + "/api/v1/health/ready", timeout=8)
                raise AssertionError("Readiness must fail without PostgreSQL")
            except HTTPError as response:
                assert response.code == 503
                assert json.load(response)["checks"]["database"] == "unavailable"
        finally:
            process.terminate()
            process.wait(timeout=8)
            unavailable.close()
    content = log_file.read_text(encoding="utf-8")
    assert env["DATABASE_PASSWORD"] not in content
    assert env["JWT_SECRET"] not in content
