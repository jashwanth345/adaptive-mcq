"""Adversarial local HTTP boundary checks; no real accounts or model inference."""

import asyncio
import json
import re

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.app.main import create_app
from backend.app.middleware import JSON_BODY_LIMIT, RequestMiddleware
from backend.tests.test_api import FakeDatabase


@pytest.fixture
def api(settings):
    database = FakeDatabase()
    app = create_app(settings, database_factory=lambda _: database)
    with TestClient(app, base_url="http://localhost") as client:
        yield client, database


def boundary(headers=(), chunks=(b"{}",), *, path="/api/v1/feedback/reviews", stall=False):
    sent, observed = [], {"calls": 0, "reads": 0}

    async def handler(scope, receive, send):
        observed["calls"] += 1
        observed["body"] = await Request(scope, receive).body()
        await JSONResponse({"private": "fixture"}, headers={"Cache-Control": "public"})(
            scope, receive, send
        )

    async def run():
        messages = [
            {"type": "http.request", "body": chunk, "more_body": i < len(chunks) - 1 or stall}
            for i, chunk in enumerate(chunks)
        ]

        async def receive():
            observed["reads"] += 1
            if messages:
                return messages.pop(0)
            if stall:
                await asyncio.Future()
            return {"type": "http.disconnect"}

        async def send(message):
            sent.append(message)

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": path,
            "query_string": b"",
            "headers": [(b"host", b"localhost:8000"), *headers],
            "client": ("127.0.0.1", 12345),
            "server": ("127.0.0.1", 8000),
        }
        await RequestMiddleware(handler, "http://localhost:5173", body_timeout=0.02)(
            scope, receive, send
        )

    asyncio.run(run())
    start = next(message for message in sent if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"") for message in sent if message["type"] == "http.response.body"
    )
    return start["status"], dict(start["headers"]), json.loads(body), observed


@pytest.mark.parametrize(
    "origin",
    [
        b"null",
        b"https://attacker.invalid",
        b"http://localhost:9999",
        b"http://localhost:5173.attacker.invalid",
    ],
)
def test_foreign_browser_origin_is_rejected_before_reading_body(origin):
    status, headers, payload, observed = boundary(
        [(b"origin", origin), (b"x-forwarded-host", b"localhost:5173")]
    )
    assert status == 403 and payload["error"]["code"] == "ORIGIN_NOT_ALLOWED"
    assert observed == {"calls": 0, "reads": 0}
    assert b"access-control-allow-origin" not in headers
    assert headers[b"cache-control"] == b"no-store"


@pytest.mark.parametrize("origin", [None, b"http://localhost:5173", b"http://localhost:8000"])
def test_configured_browser_same_origin_and_cli_remain_usable(origin):
    status, headers, _, observed = boundary([] if origin is None else [(b"origin", origin)])
    assert status == 200 and observed["calls"] == 1 and observed["body"] == b"{}"
    assert headers[b"x-frame-options"] == b"DENY"
    assert headers[b"referrer-policy"] == b"no-referrer"
    assert headers[b"cache-control"] == b"no-store"


@pytest.mark.parametrize(
    "headers,code",
    [
        ([(b"origin", b"http://localhost:5173"), (b"origin", b"null")], "ORIGIN_NOT_ALLOWED"),
        ([(b"host", b"attacker.invalid")], "INVALID_HOST"),
        ([(b"content-length", b"2"), (b"content-length", b"2")], "INVALID_CONTENT_LENGTH"),
        ([(b"content-length", b"-1")], "INVALID_CONTENT_LENGTH"),
        ([(b"content-length", b"NaN")], "INVALID_CONTENT_LENGTH"),
        ([(b"content-length", b"20000")], "REQUEST_TOO_LARGE"),
        ([(b"content-encoding", b"gzip")], "UNSUPPORTED_ENCODING"),
    ],
)
def test_ambiguous_or_oversized_headers_do_not_reach_application(headers, code):
    status, _, payload, observed = boundary(headers)
    assert status in {400, 403, 413, 415} and payload["error"]["code"] == code
    assert observed == {"calls": 0, "reads": 0}


@pytest.mark.parametrize(
    "path",
    ["/api/v1/auth/login", "/api/v1/feedback/reviews/fixture/decisions", "/api/v1/future-module"],
)
def test_streamed_body_limit_includes_feedback_and_future_routes(path):
    status, _, payload, observed = boundary(chunks=(b"x" * JSON_BODY_LIMIT, b"x"), path=path)
    assert status == 413 and payload["error"]["code"] == "REQUEST_TOO_LARGE"
    assert observed["calls"] == 0


def test_exact_limit_replays_bytes_once_and_small_declared_length_cannot_bypass_limit():
    body = b"x" * JSON_BODY_LIMIT
    status, _, _, observed = boundary(chunks=(body[:123], body[123:]))
    assert status == 200 and observed["body"] == body
    status, _, _, observed = boundary([(b"content-length", b"2")], chunks=(body, b"x"))
    assert status == 413 and observed["calls"] == 0


def test_incomplete_body_times_out_without_calling_application():
    status, headers, payload, observed = boundary(stall=True)
    assert status == 408 and payload["error"]["code"] == "REQUEST_TIMEOUT"
    assert observed["calls"] == 0 and headers[b"cache-control"] == b"no-store"


def test_content_length_mismatch_rejected_without_private_body_echo():
    status, _, payload, observed = boundary([(b"content-length", b"1")], chunks=(b"private-token",))
    assert status == 400 and payload["error"]["code"] == "INVALID_CONTENT_LENGTH"
    assert observed["calls"] == 0 and "private-token" not in json.dumps(payload)


@pytest.mark.parametrize("authorization", [None, "Bearer invalid-token"])
def test_every_protected_operation_rejects_missing_or_invalid_bearer_before_database(
    api, authorization
):
    client, database = api
    public = {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/register-teacher",
        "/api/v1/health/live",
        "/api/v1/health/ready",
    }
    count = 0
    for template, operations in client.app.openapi()["paths"].items():
        if not template.startswith("/api/v1/") or template in public:
            continue
        path = re.sub(r"\{[^}]+\}", "00000000-0000-4000-8000-000000000001", template)
        for operation in operations:
            if operation not in {"get", "post"}:
                continue
            method = operation.upper()
            response = client.request(
                method,
                path,
                json={} if method == "POST" else None,
                headers={"Authorization": authorization} if authorization else {},
            )
            assert response.status_code == 401, (method, path, response.text)
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["www-authenticate"] == "Bearer"
            count += 1
    assert count >= 60
    assert database.calls == 0


def test_origin_rejection_precedes_registration_and_cors_preflight(api):
    client, database = api
    response = client.post("/api/v1/auth/register", headers={"Origin": "null"}, json={})
    assert response.status_code == 403 and database.calls == 0
    response = client.options(
        "/api/v1/auth/login",
        headers={"Origin": "https://attacker.invalid", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 403 and "access-control-allow-origin" not in response.headers


def test_successful_feedback_and_unknown_api_responses_cannot_opt_in_to_caching(api):
    client, _ = api

    @client.app.get("/api/v1/feedback/security-probe")
    def probe():
        return JSONResponse(
            {"note": "private fixture"}, headers={"Cache-Control": "public, max-age=300"}
        )

    response = client.get("/api/v1/feedback/security-probe")
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert client.get("/api/v1/no-such-module").headers["cache-control"] == "no-store"
