import json
import os
import re
import shutil
import subprocess
import sys
from queue import Empty, Queue
from threading import Thread

import pytest

from backend.app.config import PROJECT_ROOT, Settings


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    monkeypatch.delenv("PGSERVICE", raising=False)
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
        monkeypatch.delenv(name.lower(), raising=False)


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        app_env="test",
        database_password="fixture-password",
        jwt_secret="fixture-only-secret-not-for-real-use-12345",
    )


@pytest.fixture
def postgres_fixture():
    processes = []

    def start(mode="ready"):
        node = os.getenv("TEST_NODE") or shutil.which("node")
        if not node:
            pytest.fail("Node.js is required for the explicitly enabled integration suite")
        script = PROJECT_ROOT / "database/tests/backend-server.mjs"
        env = {**os.environ, "TEST_PYTHON": sys.executable}
        process = subprocess.Popen(
            [node, str(script), mode],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        processes.append(process)
        queue = Queue()

        def read_startup():
            queue.put(process.stdout.readline())

        Thread(target=read_startup, daemon=True).start()
        try:
            line = queue.get(timeout=45)
        except Empty:
            process.kill()
            pytest.fail("Disposable PostgreSQL adapter did not start within 45 seconds")
        if not line:
            pytest.fail("Adapter startup failed: " + process.stderr.read()[-2000:])
        payload = json.loads(line)
        match = re.search(r":(\d+)(?:/[^/]*)?$", payload["connection"])
        assert match, payload
        port = int(match.group(1))
        assert port > 0, payload
        return port

    yield start
    for process in processes:
        if process.poll() is None:
            try:
                process.communicate("stop\n", timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5)
