import os
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text

from backend.app.main import create_app
from backend.app.student.schemas import Preferences


@pytest.mark.parametrize(
    "payload",
    [
        {"preferred_difficulty": "expert"},
        {"preferred_difficulty": " easy "},
        {"preferred_difficulty": "easy", "student_id": "other"},
        {},
    ],
)
def test_preference_input_rejects_invalid_or_extra_fields(payload):
    with pytest.raises(ValidationError):
        Preferences(**payload)


@contextmanager
def operator(database):
    with database.session() as session, session.begin():
        session.execute(text("RESET ROLE"))
    try:
        yield
    finally:
        with database.session() as session, session.begin():
            session.execute(text("SET ROLE phase3_runtime"))


@pytest.fixture
def students(settings, postgres_fixture):
    config = settings.model_copy(
        update={
            "database_port": postgres_fixture(),
            "database_name": "postgres",
            "database_user": "postgres",
            "database_pool_size": 1,
        }
    )
    app = create_app(config)
    with TestClient(app, base_url="http://localhost") as client:
        ids, tokens = [], []
        for number in range(2):
            payload = {
                "email": f"student{number}@example.com",
                "display_name": f"Student {number}",
                "password": "Student fixture 42!",
            }
            response = client.post("/api/v1/auth/register", json=payload)
            assert response.status_code == 201, response.text
            ids.append(response.json()["id"])
            response = client.post(
                "/api/v1/auth/login", json={key: payload[key] for key in ["email", "password"]}
            )
            assert response.status_code == 200, response.text
            tokens.append({"Authorization": "Bearer " + response.json()["access_token"]})
        yield client, app, ids, tokens


integration = pytest.mark.skipif(
    os.getenv("MCQ_RUN_DB_TESTS") != "1", reason="Enable disposable database tests"
)


@pytest.mark.integration
@integration
def test_student_preferences_persist_scope_validate_and_audit(students):
    client, app, ids, tokens = students
    url = "/api/v1/student"
    empty = client.get(url + "/dashboard", headers=tokens[0])
    assert empty.status_code == 200, empty.text
    assert empty.headers["cache-control"] == "no-store"
    assert empty.json() == {
        "preferences": {"preferred_difficulty": "easy"},
        "counts": dict(courses=0, materials=0, submitted_attempts=0, feedback=0),
        "courses": [],
    }
    saved = client.post(
        url + "/preferences", headers=tokens[0], json={"preferred_difficulty": "hard"}
    )
    assert saved.status_code == 200 and saved.json()["preferred_difficulty"] == "hard"
    assert (
        client.get(url + "/dashboard", headers=tokens[0]).json()["preferences"][
            "preferred_difficulty"
        ]
        == "hard"
    )
    assert (
        client.get(url + "/dashboard", headers=tokens[1]).json()["preferences"][
            "preferred_difficulty"
        ]
        == "easy"
    )
    assert (
        client.post(
            url + "/preferences",
            headers=tokens[0],
            json={"preferred_difficulty": "hard", "student_id": ids[1]},
        ).status_code
        == 422
    )
    assert (
        client.post(
            url + "/preferences", headers=tokens[0], json={"preferred_difficulty": "expert"}
        ).status_code
        == 422
    )
    assert (
        client.post(url + "/preferences", headers=tokens[0], content="x" * 17000).status_code == 413
    )
    with operator(app.state.database), app.state.database.session() as session:
        assert (
            session.execute(
                text(
                    "SELECT count(*) FROM mcq.audit_events WHERE actor_id=:id AND event_type='student.preferences_saved'"
                ),
                {"id": ids[0]},
            ).scalar_one()
            == 1
        )


@pytest.mark.integration
@integration
def test_enrollments_materials_and_history_are_student_scoped(students):
    client, app, ids, tokens = students
    with operator(app.state.database), app.state.database.session() as session, session.begin():
        for student_no, uid in enumerate(ids):
            for n in range(8):
                # Owner intentionally differs from enrolled student: scope must use membership.student_id.
                course = session.execute(
                    text(
                        "INSERT INTO mcq.courses(owner_id,title) VALUES(:owner,:title) RETURNING id"
                    ),
                    {"owner": ids[1 - student_no], "title": f"Student {student_no} course {n}"},
                ).scalar_one()
                session.execute(
                    text(
                        "INSERT INTO mcq.course_memberships(course_id,student_id,active,joined_at) VALUES(:cid,:uid,:active,now()+make_interval(secs => :n))"
                    ),
                    {"cid": course, "uid": uid, "active": n < 7, "n": n},
                )
            for archived in [True, False]:
                session.execute(
                    text(
                        "INSERT INTO mcq.materials(owner_id,title,archived) VALUES(:uid,'Material',:archived)"
                    ),
                    {"uid": uid, "archived": archived},
                )
            assessment = session.execute(
                text(
                    "INSERT INTO mcq.assessments(owner_id,title,kind,mode,max_attempts) VALUES(:uid,:title,'practice','adaptive',10) RETURNING id"
                ),
                {"uid": uid, "title": f"Private practice {student_no}"},
            ).scalar_one()
            session.execute(
                text(
                    "UPDATE mcq.assessments SET state='published',published_at=now() WHERE id=:id"
                ),
                {"id": assessment},
            )
            for n in range(1, 8):
                attempt = session.execute(
                    text(
                        "INSERT INTO mcq.attempts(assessment_id,owner_id,student_id,attempt_number,idempotency_key,started_at) VALUES(:aid,:uid,:uid,:n,gen_random_uuid(),now()-make_interval(secs => :n)) RETURNING id"
                    ),
                    {"aid": assessment, "uid": uid, "n": n},
                ).scalar_one()
                if n == 1:
                    session.execute(
                        text(
                            "UPDATE mcq.attempts SET state='expired',submitted_at=now() WHERE id=:id"
                        ),
                        {"id": attempt},
                    )
    response = client.get("/api/v1/student/dashboard", headers=tokens[0])
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["counts"] == dict(courses=7, materials=1, submitted_attempts=0, feedback=0)
    assert [c["title"] for c in data["courses"]] == [
        f"Student 0 course {n}" for n in [6, 5, 4, 3, 2, 1]
    ]
    page = client.get("/api/v1/student/attempts?offset=0&limit=6", headers=tokens[0])
    assert page.status_code == 200, page.text
    assert page.json()["total"] == 7 and len(page.json()["items"]) == 6
    assert page.json()["items"][0]["state"] == "expired"
    assert all(row["title"] == "Private practice 0" for row in page.json()["items"])
    assert set(page.json()["items"][0]) == {
        "id",
        "title",
        "kind",
        "state",
        "attempt_number",
        "started_at",
        "submitted_at",
    }
    assert (
        client.get("/api/v1/student/attempts?offset=6&limit=6", headers=tokens[0]).json()["items"][
            0
        ]["attempt_number"]
        == 7
    )
    assert client.get("/api/v1/student/attempts?limit=25", headers=tokens[0]).status_code == 422
    assert client.get("/api/v1/student/attempts?offset=-1", headers=tokens[0]).status_code == 422


@pytest.mark.integration
@integration
def test_student_role_gate_missing_profile_and_grants(students):
    client, app, ids, tokens = students
    assert client.get("/api/v1/student/dashboard").status_code == 401
    with operator(app.state.database), app.state.database.session() as session, session.begin():
        session.execute(
            text("INSERT INTO mcq.user_roles(user_id,role) VALUES(:id,'teacher')"), {"id": ids[1]}
        )
        session.execute(
            text("DELETE FROM mcq.user_roles WHERE user_id=:id AND role='student'"), {"id": ids[1]}
        )
    assert client.get("/api/v1/student/dashboard", headers=tokens[1]).status_code == 403
    assert client.get("/api/v1/student/attempts", headers=tokens[1]).status_code == 403
    assert (
        client.post(
            "/api/v1/student/preferences", headers=tokens[1], json={"preferred_difficulty": "hard"}
        ).status_code
        == 403
    )
    with operator(app.state.database), app.state.database.session() as session, session.begin():
        session.execute(text("DELETE FROM mcq.student_profiles WHERE user_id=:id"), {"id": ids[0]})
    for method, route, args in [
        ("get", "/dashboard", {}),
        ("post", "/preferences", {"json": {"preferred_difficulty": "medium"}}),
    ]:
        result = getattr(client, method)("/api/v1/student" + route, headers=tokens[0], **args)
        assert (
            result.status_code == 503
            and result.json()["error"]["code"] == "STUDENT_PROFILE_UNAVAILABLE"
        )
    with app.state.database.session() as session:
        assert session.execute(
            text(
                "SELECT has_column_privilege(current_user,'mcq.student_profiles','preferred_difficulty','UPDATE') AND NOT has_column_privilege(current_user,'mcq.student_profiles','user_id','UPDATE') AND NOT has_table_privilege(current_user,'mcq.attempts','INSERT,UPDATE,DELETE') AND NOT has_table_privilege(current_user,'mcq.answers','SELECT')"
            )
        ).scalar_one()
