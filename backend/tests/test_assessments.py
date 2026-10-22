"""Publication tests use synthetic AI evidence only; no model inference or quality claims."""

from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import event, text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.assessments import Create, Publish, code_digest, reference_code
from backend.tests.test_teacher import integration, owner, teachers  # noqa: F401
from backend.tests.test_teacher_review import decision, passing_checks, synthetic_ai_draft
from backend.tests.test_verifier import upload_and_generate

ROOT = "/api/v1/teacher/assessments"
STUDENT = "/api/v1/student/assessments"


def command(**values):
    return {"idempotency_key": str(uuid4()), **values}


def create_body(course, version, **values):
    return command(title="Database fundamentals", course_id=course, version_ids=[version], **values)


def make_assessment(client, token, version):
    course = client.post(
        "/api/v1/teacher/courses", json={"title": "Classroom fixture"}, headers=token
    ).json()["id"]
    body = create_body(course, version)
    result = client.post(ROOT, json=body, headers=token)
    assert result.status_code == 201, result.text
    return result.json(), body


def student_account(client, email="permitted@example.com"):
    body = dict(email=email, display_name="Synthetic student", password="Student fixture 42!")
    created = client.post("/api/v1/auth/register", json=body)
    assert created.status_code == 201, created.text
    logged = client.post("/api/v1/auth/login", json={k: body[k] for k in ("email", "password")})
    assert logged.status_code == 200, logged.text
    return {"Authorization": "Bearer " + logged.json()["access_token"]}, logged.json()["user"]["id"]


def post(client, target, action, token, **body):
    return client.post(f"{ROOT}/{target}/{action}", headers=token, json=command(**body))


@pytest.mark.parametrize(
    "values",
    [
        {"title": "  "},
        {"max_attempts": True},
        {"max_attempts": 0},
        {"time_limit_seconds": 0},
        {"randomize_options": "true"},
        {"owner_id": str(uuid4())},
        {"title": "bad\x00title"},
    ],
)
def test_draft_contract(values):
    with pytest.raises(ValidationError):
        Create(**{**create_body(str(uuid4()), str(uuid4())), **values})


def test_reject_duplicate_questions_and_invalid_expiry():
    version = str(uuid4())
    body = create_body(str(uuid4()), version)
    body["version_ids"] = [version, version]
    with pytest.raises(ValidationError):
        Create(**body)
    for hours in (0, 721, True):
        with pytest.raises(ValidationError):
            Publish(**command(revision=1, expiry_hours=hours))


def test_codes_are_secret_derived_normalized_and_retry_stable():
    owner_id, key = uuid4(), uuid4()
    code = reference_code("private-test-secret", owner_id, key)
    assert code == reference_code("private-test-secret", owner_id, key)
    assert code != reference_code("different-secret", owner_id, key)
    assert code != reference_code("private-test-secret", owner_id, key, 1)
    assert len(code) == 28
    assert code_digest(code) == code_digest(" " + code.lower().replace("-", " ") + " ")
    assert code_digest(code) != code_digest("invalid")


@pytest.mark.integration
@integration
def test_drafts_owner_isolation_revision_mock_gate_and_privileges(request, tmp_path):
    client, app, _, tokens = request.getfixturevalue("teachers")
    _, version = upload_and_generate(client, app, tokens, tmp_path)
    detail, body = make_assessment(client, tokens[0], version)
    target = detail["id"]
    assert not detail["can_publish"] and detail["issued_code"] is None
    assert client.post(ROOT, json=body, headers=tokens[0]).json()["id"] == target
    assert client.get(ROOT, headers=tokens[0]).json()["total"] == 1
    assert client.get(ROOT, headers=tokens[1]).json()["total"] == 0
    assert client.get(f"{ROOT}/{target}", headers=tokens[1]).status_code == 404
    assert client.get(ROOT).status_code == 401
    for action, data in [
        ("publish", dict(revision=1)),
        ("participants", dict(email="x@example.com")),
        ("revoke", {}),
    ]:
        assert post(client, target, action, tokens[1], **data).status_code == 404
    denied = post(client, target, "publish", tokens[0], revision=1)
    assert denied.status_code == 409 and denied.json()["error"]["code"] == "ASSESSMENT_BLOCKED"
    assert (
        post(client, target, "participants", tokens[0], email="missing@example.com").status_code
        == 409
    )
    saved = {k: v for k, v in body.items() if k != "course_id"}
    saved.update(command(revision=1, title="Revised title"))
    response = client.post(f"{ROOT}/{target}/save", json=saved, headers=tokens[0])
    assert response.status_code == 200, response.text
    assert response.json()["revision"] == 2
    assert (
        client.post(f"{ROOT}/{target}/save", json=saved, headers=tokens[0]).json()["revision"] == 2
    )
    assert (
        client.post(
            f"{ROOT}/{target}/save", json={**saved, "title": "Conflict"}, headers=tokens[0]
        ).json()["error"]["code"]
        == "ASSESSMENT_KEY_CONFLICT"
    )
    assert (
        client.post(
            f"{ROOT}/{target}/save",
            json={**saved, "idempotency_key": str(uuid4())},
            headers=tokens[0],
        ).json()["error"]["code"]
        == "ASSESSMENT_STALE"
    )
    student, _ = student_account(client)
    assert client.get(ROOT, headers=student).status_code == 403
    assert (
        client.post(STUDENT + "/join", json={"code": "invalid"}, headers=tokens[0]).status_code
        == 403
    )
    assert client.post(ROOT, content="x" * 17000, headers=tokens[0]).status_code == 413
    with app.state.database.session() as session:
        assert session.execute(text("SELECT count(*) FROM mcq.reference_codes")).scalar_one() == 0
        assert session.execute(text("SELECT state FROM mcq.assessments")).scalar_one() == "draft"
        for table in (
            "assessments",
            "assessment_questions",
            "reference_codes",
            "assessment_participants",
            "assessment_operations",
            "assessment_admissions",
        ):
            assert not session.execute(
                text("SELECT has_table_privilege(current_user,:table,'INSERT,UPDATE,DELETE')"),
                {"table": "mcq." + table},
            ).scalar_one()


@pytest.mark.integration
@integration
def test_synthetic_publication_code_lifecycle_authorization_and_private_preview(
    request, tmp_path, monkeypatch
):
    client, app, _, tokens = request.getfixturevalue("teachers")
    version = synthetic_ai_draft(client, app, tokens, tmp_path, monkeypatch)
    passing_checks(client, version, tokens[0])
    assert (
        client.post(
            f"/api/v1/teacher/reviews/{version}/decisions", json=decision(), headers=tokens[0]
        ).status_code
        == 200
    )
    detail, _ = make_assessment(client, tokens[0], version)
    target = detail["id"]
    assert detail["can_publish"]
    permitted, student_id = student_account(client)
    stranger, _ = student_account(client, "stranger@example.com")
    assert (
        post(client, target, "participants", tokens[0], email="PERMITTED@example.com").status_code
        == 200
    )
    body = command(revision=1, expiry_hours=24)
    path = f"{ROOT}/{target}/publish"
    published = client.post(path, headers=tokens[0], json=body)
    assert published.status_code == 200, published.text
    code = published.json()["issued_code"]
    assert code and published.json()["state"] == "published"
    assert client.post(path, headers=tokens[0], json=body).json()["issued_code"] == code
    assert client.get(f"{ROOT}/{target}", headers=tokens[0]).json()["issued_code"] is None
    assert client.post(STUDENT + "/join", json={"code": code}, headers=stranger).status_code == 404
    joined = client.post(STUDENT + "/join", json={"code": code.lower()}, headers=permitted)
    assert joined.status_code == 200, joined.text
    assert joined.headers["cache-control"] == "no-store"
    assert joined.json()["available"] and joined.json()["question_count"] == 1
    assert set(joined.json()) == {
        "id",
        "title",
        "question_count",
        "available",
        "time_limit_seconds",
        "max_attempts",
        "randomize_questions",
        "randomize_options",
        "release_policy",
    }
    assert client.post(STUDENT + "/join", json={"code": code}, headers=permitted).status_code == 200
    assert client.get(STUDENT, headers=permitted).json()["total"] == 1
    with app.state.database.session() as session:
        assert (
            session.execute(text("SELECT count(*) FROM mcq.assessment_admissions")).scalar_one()
            == 1
        )
        assert session.execute(text("SELECT count(*) FROM mcq.attempts")).scalar_one() == 0
        assert (
            session.execute(
                text(
                    "SELECT count(*) FROM mcq.course_memberships WHERE student_id=:student AND active"
                ),
                {"student": student_id},
            ).scalar_one()
            == 1
        )
        assert session.execute(
            text("SELECT code_digest FROM mcq.reference_codes")
        ).scalar_one() == code_digest(code)
        assert code not in str(
            session.execute(text("SELECT request,result FROM mcq.assessment_operations")).all()
        )
    replacement = post(client, target, "rotate", tokens[0], expiry_hours=1)
    assert replacement.status_code == 200, replacement.text
    new_code = replacement.json()["issued_code"]
    assert new_code and new_code != code
    assert client.post(path, headers=tokens[0], json=body).json()["issued_code"] is None
    assert client.get(STUDENT, headers=permitted).json()["items"][0]["available"] is False
    assert client.post(STUDENT + "/join", json={"code": code}, headers=permitted).status_code == 404
    assert (
        client.post(STUDENT + "/join", json={"code": new_code}, headers=permitted).status_code
        == 200
    )
    assert (
        post(
            client, target, "participants", tokens[0], email="permitted@example.com", active=False
        ).status_code
        == 200
    )
    assert (
        client.post(STUDENT + "/join", json={"code": new_code}, headers=permitted).status_code
        == 404
    )
    assert (
        post(
            client, target, "participants", tokens[0], email="permitted@example.com", active=True
        ).status_code
        == 200
    )
    assert post(client, target, "revoke", tokens[0]).status_code == 200
    assert (
        client.post(STUDENT + "/join", json={"code": new_code}, headers=permitted).status_code
        == 404
    )
    closed = post(client, target, "close", tokens[0])
    assert closed.status_code == 200 and closed.json()["state"] == "closed"
    assert post(client, target, "rotate", tokens[0]).status_code == 409
    assert client.get(STUDENT, headers=permitted).json()["total"] == 1


@pytest.mark.integration
@integration
def test_unknown_codes_are_rate_limited_persistently(request):
    client, app, _, _ = request.getfixturevalue("teachers")
    token, _ = student_account(client)
    for _ in range(10):
        assert (
            client.post(STUDENT + "/join", json={"code": "wrong"}, headers=token).status_code == 404
        )
    response = client.post(STUDENT + "/join", json={"code": "wrong"}, headers=token)
    assert response.status_code == 429 and response.headers["retry-after"] == "60"
    with owner(app.state.database), app.state.database.session() as session, session.begin():
        session.execute(
            text(
                "UPDATE mcq.code_join_limits SET window_started=clock_timestamp()-interval '61 seconds'"
            )
        )
    assert client.post(STUDENT + "/join", json={"code": "wrong"}, headers=token).status_code == 404


@pytest.mark.integration
@integration
def test_synthetic_publication_failure_rolls_back_and_expiry_blocks_access(
    request, tmp_path, monkeypatch
):
    client, app, _, tokens = request.getfixturevalue("teachers")
    version = synthetic_ai_draft(client, app, tokens, tmp_path, monkeypatch)
    passing_checks(client, version, tokens[0])
    assert (
        client.post(
            f"/api/v1/teacher/reviews/{version}/decisions", json=decision(), headers=tokens[0]
        ).status_code
        == 200
    )
    detail, _ = make_assessment(client, tokens[0], version)
    target = detail["id"]

    def fail_after_write(conn, cursor, statement, parameters, context, executemany):
        if "SELECT mcq.assessment_action" in statement:
            raise SQLAlchemyError("Synthetic transaction interruption")

    event.listen(app.state.database.engine, "after_cursor_execute", fail_after_write)
    try:
        assert post(client, target, "publish", tokens[0], revision=1).status_code == 503
    finally:
        event.remove(app.state.database.engine, "after_cursor_execute", fail_after_write)
    with app.state.database.session() as session:
        assert session.execute(text("SELECT state FROM mcq.assessments")).scalar_one() == "draft"
        assert session.execute(text("SELECT count(*) FROM mcq.reference_codes")).scalar_one() == 0
        assert (
            session.execute(
                text("SELECT count(*) FROM mcq.assessment_operations WHERE operation='publish'")
            ).scalar_one()
            == 0
        )
    published = post(client, target, "publish", tokens[0], revision=1)
    assert published.status_code == 200, published.text
    code = published.json()["issued_code"]
    student, _ = student_account(client)
    assert (
        post(client, target, "participants", tokens[0], email="permitted@example.com").status_code
        == 200
    )
    with owner(app.state.database), app.state.database.session() as session, session.begin():
        session.execute(
            text("UPDATE mcq.reference_codes SET expires_at=created_at+interval '1 microsecond'")
        )
    assert client.post(STUDENT + "/join", json={"code": code}, headers=student).status_code == 404
    # Approval revoked after publication also blocks replacement and student admission.
    assert (
        client.post(
            f"/api/v1/teacher/reviews/{version}/decisions",
            json=decision("reject"),
            headers=tokens[0],
        ).status_code
        == 200
    )
    assert post(client, target, "rotate", tokens[0]).json()["error"]["code"] == "ASSESSMENT_BLOCKED"
