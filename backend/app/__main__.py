import logging
import sys

import uvicorn

from .config import ConfigurationError, load_settings
from .main import create_app


def main() -> int:
    try:
        settings = load_settings()
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    # No access log: raw request URLs/query strings may contain private data.
    uvicorn.run(
        create_app(settings),
        host=settings.api_host,
        port=settings.api_port,
        workers=1,
        access_log=False,
        proxy_headers=False,
        server_header=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
