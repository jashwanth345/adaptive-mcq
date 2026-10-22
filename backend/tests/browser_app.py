"""Browser fixture launcher: disposable upload storage, real app and API."""

import faulthandler
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

import uvicorn

from backend.app.config import PROJECT_ROOT, load_settings
from backend.app.main import create_app

if __name__ == "__main__":
    # Test-only diagnostics for slow startup on memory-constrained Windows.
    faulthandler.dump_traceback_later(20)
    settings = load_settings()
    if settings.app_env != "test":
        raise SystemExit("This launcher requires test configuration")
    app = create_app(settings)
    original = app.router.lifespan_context

    @asynccontextmanager
    async def temporary_uploads(application):
        if os.getenv("MCQ_TEST_UPLOADS"):
            root = Path(os.environ["MCQ_TEST_UPLOADS"]).resolve()
            if not root.is_relative_to(PROJECT_ROOT / "data/native-acceptance"):
                raise RuntimeError("Native test uploads must stay in the acceptance workspace")
            root.mkdir(parents=True, exist_ok=True)
            async with original(application):
                application.state.materials.root = root
                faulthandler.cancel_dump_traceback_later()
                yield
            return
        scratch = (PROJECT_ROOT / "frontend" / "test-results").resolve()
        assert scratch.is_relative_to(PROJECT_ROOT)
        scratch.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix="mcq-browser-", dir=scratch) as directory:
            root = Path(directory).resolve()
            assert root.is_relative_to(scratch)
            async with original(application):
                application.state.materials.root = root
                faulthandler.cancel_dump_traceback_later()
                yield

    app.router.lifespan_context = temporary_uploads
    config = uvicorn.Config(
        app,
        host=settings.api_host,
        port=settings.api_port,
        workers=1,
        access_log=False,
        proxy_headers=False,
        server_header=False,
    )
    server = uvicorn.Server(config)

    def stop_from_test_runner():
        # Test-only stdin control allows lifespan/database cleanup on Windows.
        # The normal application launcher exposes no shutdown endpoint.
        for line in sys.stdin:
            if line.strip() == "stop":
                server.should_exit = True
                return

    # Only the restart journey needs an open stdin reader. Keep it out of
    # PDF-worker journeys, whose child processes otherwise inherit that pipe.
    if "--stdin-shutdown" in sys.argv:
        Thread(target=stop_from_test_runner, daemon=True).start()
    server.run()
