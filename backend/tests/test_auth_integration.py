import os
from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.app.auth.schemas import RegisterRequest
from backend.app.auth.security import utc_now
from backend.app.config import ConfigurationError
from backend.app.main import create_app
from backend.manage import manage_user, provision_teacher

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("MCQ_RUN_DB_TESTS") != "1", reason="Enable disposable database integration tests"
    ),
]
PASSWORD = "Fixture password 42!"
EMAIL = "student@example.com"


@pytest.fixture
def auth_context(settings, postgres_fixture):
    port = postgres_fixture()
    config = settings.model_copy(
        update={
            "database_port": port,
            "database_name": "postgres",
            "database_user": "postgres",
            "database_pool_size": 1,
        }
    )
    app = create_app(config)
    with TestClient(app, base_url="http://localhost") as client:
        assert client.get("/api/v1/health/ready").status_code == 200
        yield client, app, config


@contextmanager
def operator(database):
    # Adapter-only role switching: its session_user is the fixture owner.
    # This is NOT a native PostgreSQL login/authentication test.
    with database.session() as session, session.begin():
        session.execute(text("RESET ROLE"))
    try:
        yield
    finally:
        with database.session() as session, session.begin():
            session.execute(text("SET ROLE phase3_runtime"))


def signup(client, email=EMAIL):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "Student fixture"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def login(client, email=EMAIL, password=PASSWORD):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()["access_token"]


def headers(token):
    return {"Authorization": "Bearer " + token}


def assert_sql_rejection(database, sql, state):
    # Catch the expected exception inside PostgreSQL: the embedded socket adapter
    # cannot reliably recover an extended-query error followed by wire ROLLBACK.
    # A missing rejection still fails the test; native wire recovery is unverified.
    with database.session() as session, session.begin():
        session.execute(
            text(f"""DO $check$ BEGIN
            {sql};
            RAISE EXCEPTION 'Expected SQL rejection did not occur';
        EXCEPTION WHEN SQLSTATE '{state}' THEN NULL;
        END $check$;""")
        )


def test_student_registration_login_identity_and_role_gates(auth_context):
    client, app, _ = auth_context
    response = client.post(
        "/api/v1/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "display_name": "Student", "role": "teacher"},
    )
    assert response.status_code == 422
    user = signup(client)
    assert user["roles"] == ["student"] and "password_hash" not in user
    token = login(client)
    assert client.get("/api/v1/auth/me", headers=headers(token)).json() == user
    assert client.get("/api/v1/roles/student", headers=headers(token)).status_code == 200
    assert client.get("/api/v1/roles/teacher", headers=headers(token)).status_code == 403
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Basic x"}).status_code == 401
    with operator(app.state.database), app.state.database.session() as session:
        stored = session.execute(
            text("SELECT password_hash FROM mcq.users WHERE email=:email"), {"email": EMAIL}
        ).scalar_one()
        assert stored.startswith("$argon2id$") and PASSWORD not in stored
        assert session.execute(text("SELECT count(*) FROM mcq.student_profiles")).scalar_one() == 1


def test_duplicate_registration_rolls_back_profile_and_role(auth_context):
    client, app, _ = auth_context
    signup(client)
    duplicate = client.post(
        "/api/v1/auth/register",
        json={"email": "STUDENT@example.com", "password": PASSWORD, "display_name": "Other"},
    )
    assert duplicate.status_code == 409, duplicate.text
    with operator(app.state.database), app.state.database.session() as session:
        for table in ("users", "user_roles", "student_profiles"):
            assert session.execute(text(f"SELECT count(*) FROM mcq.{table}")).scalar_one() == 1


def test_logout_revokes_one_session_and_survives_app_restart(auth_context):
    client, app, config = auth_context
    signup(client)
    first, second = login(client), login(client)
    assert client.post("/api/v1/auth/logout", headers=headers(first)).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers(first)).status_code == 401
    assert client.get("/api/v1/auth/me", headers=headers(second)).status_code == 200
    # Recreate application/service state while retaining the same DB, not an in-memory denylist.
    restarted = create_app(config, database_factory=lambda _: app.state.database)
    with TestClient(restarted, base_url="http://localhost") as other:
        assert other.get("/api/v1/auth/me", headers=headers(first)).status_code == 401
        assert other.get("/api/v1/auth/me", headers=headers(second)).status_code == 200
        assert other.post("/api/v1/auth/logout-all", headers=headers(second)).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers(second)).status_code == 401


def test_password_change_checks_old_password_and_revokes_every_session(auth_context):
    client, _, _ = auth_context
    signup(client)
    first, second = login(client), login(client)
    route = "/api/v1/auth/change-password"
    wrong = client.post(
        route,
        headers=headers(first),
        json={"current_password": "wrong", "new_password": "New fixture password 43!"},
    )
    assert wrong.status_code == 401
    changed = client.post(
        route,
        headers=headers(first),
        json={"current_password": PASSWORD, "new_password": "New fixture password 43!"},
    )
    assert changed.status_code == 204
    for token in (first, second):
        assert client.get("/api/v1/auth/me", headers=headers(token)).status_code == 401
    assert (
        client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}).status_code
        == 401
    )
    login(client, password="New fixture password 43!")


def test_operator_teacher_creation_dual_roles_and_revocation(auth_context):
    client, app, _ = auth_context
    db = app.state.database
    payload = RegisterRequest(
        email="teacher@example.com", display_name="Teacher fixture", password=PASSWORD
    )
    with pytest.raises(ConfigurationError):
        provision_teacher(db, app.state.auth.security, payload)
    with operator(db):
        provision_teacher(db, app.state.auth.security, payload)
    teacher = login(client, email=payload.email)
    assert client.get("/api/v1/roles/teacher", headers=headers(teacher)).status_code == 200
    assert client.get("/api/v1/roles/student", headers=headers(teacher)).status_code == 403
    signup(client)
    old = login(client)
    with operator(db):
        manage_user(db, EMAIL, "grant-teacher")
    assert client.get("/api/v1/auth/me", headers=headers(old)).status_code == 401
    dual = login(client)
    assert client.get("/api/v1/auth/me", headers=headers(dual)).json()["roles"] == [
        "student",
        "teacher",
    ]
    for role in ("student", "teacher"):
        assert client.get("/api/v1/roles/" + role, headers=headers(dual)).status_code == 200
    with operator(db):
        manage_user(db, EMAIL, "revoke-teacher")
    new = login(client)
    assert client.get("/api/v1/roles/teacher", headers=headers(new)).status_code == 403


def test_disabled_user_and_live_role_lookup(auth_context):
    client, app, _ = auth_context
    signup(client)
    token = login(client)
    db = app.state.database
    # Direct trusted-role removal without token mutation demonstrates fresh DB role lookup.
    with operator(db), db.session() as session, session.begin():
        session.execute(text("DELETE FROM mcq.user_roles"))
    assert client.get("/api/v1/auth/me", headers=headers(token)).status_code == 401
    with operator(db), db.session() as session, session.begin():
        session.execute(text("INSERT INTO mcq.user_roles SELECT id,'student' FROM mcq.users"))
    with operator(db):
        manage_user(db, EMAIL, "disable-user")
    assert (
        client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}).status_code
        == 401
    )
    assert client.get("/api/v1/auth/me", headers=headers(token)).status_code == 401


def test_wrong_and_unknown_login_match_and_rate_limit_persists(auth_context):
    client, app, config = auth_context
    signup(client)
    unknown = client.post(
        "/api/v1/auth/login", json={"email": "unknown@example.com", "password": "wrong"}
    )
    wrong = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": "wrong"})
    assert unknown.status_code == wrong.status_code == 401
    for field in ("code", "message"):
        assert unknown.json()["error"][field] == wrong.json()["error"][field]
    for _ in range(config.auth_login_account_limit - 1):
        assert (
            client.post(
                "/api/v1/auth/login", json={"email": EMAIL, "password": "wrong"}
            ).status_code
            == 401
        )
    limited = client.post(
        "/api/v1/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        headers={"X-Forwarded-For": "8.8.8.8"},
    )
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) > 0
    restarted = create_app(config, database_factory=lambda _: app.state.database)
    with TestClient(restarted, base_url="http://localhost") as other:
        assert (
            other.post(
                "/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
            ).status_code
            == 429
        )


def test_runtime_cannot_grant_roles_or_reactivate_accounts(auth_context):
    client, app, _ = auth_context
    user = signup(client)
    db = app.state.database
    for sql in (
        "INSERT INTO mcq.user_roles(user_id,role) VALUES(:id,'teacher')",
        "UPDATE mcq.users SET active=false WHERE id=:id",
        "DELETE FROM mcq.user_roles WHERE user_id=:id",
    ):
        assert_sql_rejection(db, sql.replace(":id", f"'{UUID(user['id'])}'::uuid"), "42501")


def test_session_database_expiry_and_revocation_invariants(auth_context):
    client, app, _ = auth_context
    signup(client)
    token = login(client)
    sid = app.state.auth.security.decode(token)["jti"]
    db = app.state.database
    assert client.post("/api/v1/auth/logout", headers=headers(token)).status_code == 204
    assert_sql_rejection(
        db, f"UPDATE mcq.auth_sessions SET revoked_at=NULL WHERE id='{sid}'::uuid", "23514"
    )
    assert_sql_rejection(
        db,
        f"UPDATE mcq.auth_sessions SET expires_at=clock_timestamp()+interval '1 day' WHERE id='{sid}'::uuid",
        "42501",
    )
    uid = app.state.auth.security.decode(token)["sub"]
    expired_id = uuid4()
    with operator(db), db.session() as session, session.begin():
        session.execute(
            text(
                "INSERT INTO mcq.auth_sessions(id,user_id,created_at,expires_at) VALUES(:sid,:uid,clock_timestamp()-interval '2 hours',clock_timestamp()-interval '1 hour')"
            ),
            {"sid": expired_id, "uid": uid},
        )
    stale, _ = app.state.auth.security.issue(uid, expired_id, utc_now())
    assert client.get("/api/v1/auth/me", headers=headers(stale)).status_code == 401


def test_auth_body_size_and_missing_bearer(auth_context):
    client, _, _ = auth_context
    assert (
        client.post(
            "/api/v1/auth/login", content=b"a" * 20000, headers={"Content-Type": "application/json"}
        ).status_code
        == 413
    )
    for path in ("/auth/me", "/roles/student", "/roles/teacher"):
        response = client.get("/api/v1" + path)
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
