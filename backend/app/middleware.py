import asyncio
import logging
import re
import time
from uuid import uuid4

from starlette.datastructures import Headers
from starlette.requests import Request

from .errors import error_response

logger = logging.getLogger("mcq.requests")
JSON_BODY_LIMIT = 16384


class RequestMiddleware:
    """Local browser boundary, bounded API bodies and private response headers."""

    def __init__(self, app, allowed_origin: str, body_timeout: float = 15):
        self.app = app
        self.allowed_origin = allowed_origin
        self.body_timeout = body_timeout

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id = str(uuid4())  # Never trust caller-supplied IDs for logs.
        scope.setdefault("state", {})["request_id"] = request_id
        start = time.monotonic()
        status = 500
        started = False
        path = scope.get("path", "")
        api_request = path.startswith("/api/")

        async def send_response(message):
            nonlocal status, started
            if message["type"] == "http.response.start":
                status, started = message["status"], True
                headers = [
                    (k, v)
                    for k, v in message.get("headers", [])
                    if k.lower()
                    not in {
                        b"x-request-id",
                        b"x-content-type-options",
                        b"x-frame-options",
                        b"referrer-policy",
                        b"permissions-policy",
                    }
                ]
                headers.extend(
                    [
                        (b"x-request-id", request_id.encode()),
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                    ]
                )
                if Headers(scope=scope).get("origin") == self.allowed_origin and not any(
                    k.lower() == b"access-control-allow-origin" for k, _ in headers
                ):
                    headers.extend(
                        [
                            (b"access-control-allow-origin", self.allowed_origin.encode()),
                            (b"vary", b"Origin"),
                        ]
                    )
                if api_request:
                    headers = [(k, v) for k, v in headers if k.lower() != b"cache-control"]
                    headers.append((b"cache-control", b"no-store"))
                if not any(k.lower() == b"content-security-policy" for k, _ in headers):
                    headers.append(
                        (
                            b"content-security-policy",
                            b"default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
                        )
                    )
                message = {**message, "headers": headers}
            await send(message)

        try:
            request_headers = Headers(scope=scope)
            hosts = request_headers.getlist("host")
            host = hosts[0].lower() if len(hosts) == 1 else ""
            if not re.fullmatch(r"(?:localhost|127\.0\.0\.1|\[::1\])(?::[0-9]{1,5})?", host):
                response = error_response(
                    Request(scope), 400, "INVALID_HOST", "A local host is required."
                )
                return await response(scope, receive, send_response)
            origins = request_headers.getlist("origin")
            same_origin = f"{scope.get('scheme', 'http')}://{host}"
            if origins and (
                len(origins) != 1 or origins[0] not in {self.allowed_origin, same_origin}
            ):
                response = error_response(
                    Request(scope),
                    403,
                    "ORIGIN_NOT_ALLOWED",
                    "This browser origin is not permitted.",
                )
                return await response(scope, receive, send_response)
            # PDF uploads have authenticated streaming, a 5 MiB cap and their own
            # 15-second receive deadline. All other API bodies share one default.
            pdf_upload = scope.get("method") == "POST" and path.rstrip("/") == "/api/v1/materials"
            if api_request and not pdf_upload:
                lengths = request_headers.getlist("content-length")
                if lengths and (len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,10}", lengths[0])):
                    response = error_response(
                        Request(scope), 400, "INVALID_CONTENT_LENGTH", "Invalid request length."
                    )
                    return await response(scope, receive, send_response)
                if lengths and int(lengths[0]) > JSON_BODY_LIMIT:
                    response = error_response(
                        Request(scope), 413, "REQUEST_TOO_LARGE", "Request body is too large."
                    )
                    return await response(scope, receive, send_response)
                if request_headers.get("content-encoding", "identity").lower() != "identity":
                    response = error_response(
                        Request(scope),
                        415,
                        "UNSUPPORTED_ENCODING",
                        "Encoded request bodies are not supported.",
                    )
                    return await response(scope, receive, send_response)
                body = bytearray()
                try:
                    async with asyncio.timeout(self.body_timeout):
                        while True:
                            message = await receive()
                            if message["type"] == "http.disconnect":
                                return
                            chunk = message.get("body", b"")
                            if len(body) + len(chunk) > JSON_BODY_LIMIT:
                                response = error_response(
                                    Request(scope),
                                    413,
                                    "REQUEST_TOO_LARGE",
                                    "Request body is too large.",
                                )
                                return await response(scope, receive, send_response)
                            body.extend(chunk)
                            if not message.get("more_body", False):
                                break
                except TimeoutError:
                    response = error_response(
                        Request(scope),
                        408,
                        "REQUEST_TIMEOUT",
                        "Request body took too long to arrive.",
                    )
                    return await response(scope, receive, send_response)
                if lengths and int(lengths[0]) != len(body):
                    response = error_response(
                        Request(scope), 400, "INVALID_CONTENT_LENGTH", "Invalid request length."
                    )
                    return await response(scope, receive, send_response)
                delivered = False
                original_receive = receive

                async def replay_body():
                    nonlocal delivered
                    if not delivered:
                        delivered = True
                        return {"type": "http.request", "body": bytes(body), "more_body": False}
                    return await original_receive()

                receive = replay_body
            await self.app(scope, receive, send_response)
        except Exception:
            # No raw exceptions, bodies, query strings, SQL or credentials in logs.
            logger.error("request_failed request_id=%s", request_id)
            if started:
                raise
            response = error_response(
                Request(scope), 500, "INTERNAL_ERROR", "An unexpected error occurred."
            )
            await response(scope, receive, send_response)
        finally:
            logger.info(
                "request_complete request_id=%s status=%s elapsed_ms=%d",
                request_id,
                status,
                (time.monotonic() - start) * 1000,
            )
