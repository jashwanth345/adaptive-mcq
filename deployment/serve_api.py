"""Private stdin-controlled API child of the local supervisor (no HTTP shutdown route)."""

import sys
import threading

import uvicorn

from backend.app.config import load_settings
from backend.app.main import create_app


def main():
    settings = load_settings()
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(settings),
            host=settings.api_host,
            port=settings.api_port,
            workers=1,
            access_log=False,
            proxy_headers=False,
            server_header=False,
            timeout_graceful_shutdown=40,
        )
    )

    def control():
        # EOF also stops the child when its supervisor unexpectedly exits.
        for line in sys.stdin:
            if line.strip() == "stop":
                break
        server.should_exit = True

    threading.Thread(target=control, daemon=True).start()
    server.run()


if __name__ == "__main__":
    main()
