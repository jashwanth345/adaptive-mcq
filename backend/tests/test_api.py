from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from backend.app.main import create_app


class FakeDatabase:
    def __init__(self):
        self.closed = False
        self.calls = 0
        self.result = {
            "status": "not_ready",
            "scope": "backend_foundation",
            "checks": {"database": "unavailable"},
        }

    def readiness(self):
        self.calls += 1
        return self.result

    def close(self):
        self.closed = True


@pytest.fixture
def api(settings):
    database = FakeDatabase()
    app = create_app(settings, database_factory=lambda _: database)
    with TestClient(app, base_url="http://localhost") as client:
        yield client, database
    assert database.closed


def test_liveness_does_not_depend_on_database(api):
    client, database = api
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"
    assert database.calls == 0
    assert response.headers["cache-control"] == "no-store"


def test_missing_database_is_503(api):
    response = api[0].get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_ready_contract_is_explicitly_foundation_only(api):
    client, database = api
    database.result = {
        "status": "ready",
        "scope": "backend_foundation",
        "checks": {"database": "ok", "schema": "ok", "pgvector": "ok", "runtime_role": "ok"},
    }
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["scope"] == "backend_foundation"


def test_request_id_is_generated_not_reflected(api):
    response = api[0].get("/not-a-route", headers={"X-Request-ID": "untrusted-input"})
    assert response.status_code == 404
    request_id = response.headers["x-request-id"]
    UUID(request_id)
    assert response.json()["error"]["request_id"] == request_id
    assert "untrusted-input" not in response.text


@pytest.mark.parametrize(
    "host", ["remote.example", "localhost.evil", "[::1]evil", "localhost:abc", "127.0.0.1@evil"]
)
def test_invalid_host_uses_error_contract(api, host):
    response = api[0].get("/api/v1/health/live", headers={"Host": host})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_HOST"


def test_cors_accepts_configured_origin_only(api):
    client = api[0]
    good = client.options(
        "/api/v1/health/live",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert good.status_code == 200
    assert good.headers["access-control-allow-origin"] == "http://localhost:5173"
    UUID(good.headers["x-request-id"])
    bad = client.get("/api/v1/health/live", headers={"Origin": "https://remote.example"})
    assert "access-control-allow-origin" not in bad.headers


def test_only_current_routes_in_openapi(api):
    schema = api[0].get("/openapi.json").json()
    assert set(schema["paths"]) == {
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/api/v1/auth/register",
        "/api/v1/auth/register-teacher",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/auth/logout",
        "/api/v1/auth/logout-all",
        "/api/v1/auth/change-password",
        "/api/v1/roles/teacher",
        "/api/v1/roles/student",
        "/api/v1/teacher/dashboard",
        "/api/v1/teacher/assessments",
        "/api/v1/teacher/assessments/{assessment_id}",
        "/api/v1/teacher/assessments/{assessment_id}/save",
        "/api/v1/teacher/assessments/{assessment_id}/publish",
        "/api/v1/teacher/assessments/{assessment_id}/rotate",
        "/api/v1/teacher/assessments/{assessment_id}/revoke",
        "/api/v1/teacher/assessments/{assessment_id}/close",
        "/api/v1/teacher/assessments/{assessment_id}/participants",
        "/api/v1/student/assessments",
        "/api/v1/student/assessments/join",
        "/api/v1/teacher/reviews",
        "/api/v1/teacher/reviews/{version_id}",
        "/api/v1/teacher/reviews/{version_id}/versions",
        "/api/v1/teacher/reviews/{version_id}/edits",
        "/api/v1/teacher/reviews/{version_id}/decisions",
        "/api/v1/teacher/courses",
        "/api/v1/teacher/courses/{course_id}",
        "/api/v1/teacher/courses/{course_id}/topics",
        "/api/v1/student/dashboard",
        "/api/v1/student/attempts",
        "/api/v1/student/preferences",
        "/api/v1/student/assessments/{assessment_id}/attempts",
        "/api/v1/student/attempts/{attempt_id}",
        "/api/v1/student/attempts/{attempt_id}/save",
        "/api/v1/student/attempts/{attempt_id}/submit",
        "/api/v1/student/practice/start",
        "/api/v1/student/learning",
        "/api/v1/student/analytics",
        "/api/v1/teacher/evaluation/runs",
        "/api/v1/teacher/evaluation/runs/{run_id}",
        "/api/v1/teacher/evaluation/runs/{run_id}/review-pack",
        "/api/v1/teacher/evaluation/adaptive-export",
        "/api/v1/teacher/analytics",
        "/api/v1/teacher/assessments/{assessment_id}/analytics",
        "/api/v1/student/attempts/{attempt_id}/feedback",
        "/api/v1/student/feedback",
        "/api/v1/feedback/reviews",
        "/api/v1/feedback/reviews/{version_id}",
        "/api/v1/feedback/reviews/{version_id}/decisions",
        "/api/v1/materials",
        "/api/v1/materials/{material_id}",
        "/api/v1/rag/materials/{material_id}",
        "/api/v1/rag/materials/{material_id}/index",
        "/api/v1/rag/search",
        "/api/v1/generator/status",
        "/api/v1/generator/drafts",
        "/api/v1/generator/drafts/{version_id}",
        "/api/v1/verifier/status",
        "/api/v1/verifier/drafts/{version_id}/reports",
        "/api/v1/validation/math-check",
        "/api/v1/validation/drafts/{version_id}/reports",
    }
    assert "503" in schema["paths"]["/api/v1/health/ready"]["get"]["responses"]


def test_documentation_has_no_external_assets(api):
    response = api[0].get("/docs")
    assert response.status_code == 200
    assert "https://" not in response.text
    assert "http://" not in response.text
    assert "connect-src 'self'" in response.headers["content-security-policy"]


def test_errors_and_logs_do_not_leak_private_data(settings, caplog):
    database = FakeDatabase()
    app = create_app(settings, database_factory=lambda _: database)

    class Payload(BaseModel):
        amount: int

    @app.post("/test-validation")
    def validation(payload: Payload):
        return payload

    @app.get("/test-crash")
    def crash():
        raise RuntimeError("secret-password-and-sql")

    @app.get("/test-http")
    def http_failure():
        raise HTTPException(409, detail="private-detail")

    with TestClient(app, base_url="http://localhost") as client:
        invalid = client.post("/test-validation", json={"amount": "private-input"})
        assert invalid.status_code == 422
        assert "private-input" not in invalid.text
        assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
        crashed = client.get(
            "/test-crash?token=private-query", headers={"Origin": "http://localhost:5173"}
        )
        assert crashed.status_code == 500
        assert "secret-password-and-sql" not in crashed.text
        assert crashed.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert "private-detail" not in client.get("/test-http").text
    records = " ".join(r.getMessage() for r in caplog.records if r.name.startswith("mcq."))
    for private in ["secret-password-and-sql", "private-input", "private-query"]:
        assert private not in records


def test_method_error_retains_allow_header(api):
    response = api[0].post("/api/v1/health/live")
    assert response.status_code == 405
    assert "GET" in response.headers["allow"]
