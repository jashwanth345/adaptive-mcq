import os
from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text

from backend.app.auth.schemas import RegisterRequest
from backend.app.main import create_app
from backend.app.teacher.schemas import CourseInput
from backend.manage import provision_teacher


@pytest.mark.parametrize("title", ["", "   ", "x" * 201, "Bad\nTitle"])
def test_course_rejects_invalid_title(title):
    with pytest.raises(ValidationError):
        CourseInput(title=title)


def test_course_input_trims_and_forbids_owner():
    assert CourseInput(title="  Database Systems  ").title == "Database Systems"
    with pytest.raises(ValidationError):
        CourseInput(title="Course", owner_id=str(uuid4()))


@contextmanager
def owner(database):
    with database.session() as session, session.begin():
        session.execute(text("RESET ROLE"))
    try:
        yield
    finally:
        with database.session() as session, session.begin():
            session.execute(text("SET ROLE phase3_runtime"))


@pytest.fixture
def teachers(settings, postgres_fixture):
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
        ids = []
        with owner(app.state.database):
            for number in range(2):
                ids.append(
                    provision_teacher(
                        app.state.database,
                        app.state.auth.security,
                        RegisterRequest(
                            email=f"teacher{number}@example.com",
                            display_name=f"Teacher {number}",
                            password="Teacher fixture 42!",
                        ),
                    )
                )
        tokens = []
        for number in range(2):
            result = client.post(
                "/api/v1/auth/login",
                json={"email": f"teacher{number}@example.com", "password": "Teacher fixture 42!"},
            )
            assert result.status_code == 200, result.text
            tokens.append({"Authorization": "Bearer " + result.json()["access_token"]})
        yield client, app, ids, tokens


integration = pytest.mark.skipif(
    os.getenv("MCQ_RUN_DB_TESTS") != "1", reason="Enable disposable database tests"
)


@pytest.mark.integration
@integration
def test_teacher_owner_isolation_and_course_topic_writes(teachers):
    client, app, ids, tokens = teachers
    endpoint = "/api/v1/teacher"
    assert client.get(endpoint + "/dashboard").status_code == 401
    empty = client.get(endpoint + "/dashboard", headers=tokens[0])
    assert empty.status_code == 200, empty.text
    assert empty.headers["cache-control"] == "no-store"
    assert empty.json()["counts"] == dict(courses=0, materials=0, questions=0, assessments=0)
    assert (
        client.post(
            endpoint + "/courses",
            headers=tokens[0],
            json={"title": "DBMS", "owner_id": str(ids[1])},
        ).status_code
        == 422
    )
    result = client.post(endpoint + "/courses", headers=tokens[0], json={"title": "  DBMS  "})
    assert result.status_code == 201, result.text
    course_id = result.json()["id"]
    assert result.json()["title"] == "DBMS"
    assert (
        client.post(endpoint + "/courses", headers=tokens[0], json={"title": "dbms"}).status_code
        == 409
    )
    assert (
        client.post(endpoint + "/courses", headers=tokens[1], json={"title": "DBMS"}).status_code
        == 201
    )
    for suffix in [course_id, str(uuid4())]:
        assert client.get(endpoint + "/courses/" + suffix, headers=tokens[1]).status_code == 404
        assert (
            client.post(
                endpoint + "/courses/" + suffix + "/topics",
                headers=tokens[1],
                json={"title": "Forbidden"},
            ).status_code
            == 404
        )
    topic = client.post(
        endpoint + f"/courses/{course_id}/topics", headers=tokens[0], json={"title": "Joins"}
    )
    assert topic.status_code == 201, topic.text
    assert (
        client.post(
            endpoint + f"/courses/{course_id}/topics", headers=tokens[0], json={"title": "joins"}
        ).status_code
        == 409
    )
    detail = client.get(endpoint + "/courses/" + course_id, headers=tokens[0]).json()
    assert detail["topic_count"] == 1 and detail["topics"][0]["name"] == "Joins"
    page = client.get(endpoint + "/courses?offset=0&limit=1", headers=tokens[0]).json()
    assert page["total"] == 1 and page["items"][0]["id"] == course_id
    assert (
        client.get(endpoint + "/courses?offset=1&limit=1", headers=tokens[0]).json()["items"] == []
    )
    assert client.get(endpoint + "/courses?limit=25", headers=tokens[0]).status_code == 422
    assert client.get(endpoint + "/courses?offset=-1", headers=tokens[0]).status_code == 422
    with owner(app.state.database), app.state.database.session() as session:
        audit = (
            session.execute(
                text("SELECT event_type FROM mcq.audit_events WHERE actor_id=:id ORDER BY id"),
                {"id": ids[0]},
            )
            .scalars()
            .all()
        )
        assert (
            audit.count("teacher.course_created") == 1 and audit.count("teacher.topic_created") == 1
        )


@pytest.mark.integration
@integration
def test_teacher_summary_counts_filters_and_latest_five(teachers):
    client, app, ids, tokens = teachers
    with owner(app.state.database), app.state.database.session() as session, session.begin():
        for number, uid in enumerate(ids):
            course = session.execute(
                text("INSERT INTO mcq.courses(owner_id,title) VALUES(:uid,:title) RETURNING id"),
                {"uid": uid, "title": f"Course {number}"},
            ).scalar_one()
            for table in ["materials", "questions"]:
                columns, values = (
                    ("owner_id,title,archived", ":uid,'Material',:archived")
                    if table == "materials"
                    else ("owner_id,archived", ":uid,:archived")
                )
                for archived in [True, False]:
                    session.execute(
                        text(f"INSERT INTO mcq.{table}({columns}) VALUES({values})"),
                        {"uid": uid, "archived": archived},
                    )
            for index in range(7):
                session.execute(
                    text(
                        "INSERT INTO mcq.assessments(owner_id,course_id,title,kind,mode,created_at) VALUES(:uid,:cid,:title,'classroom','fixed',now()+make_interval(secs => :n))"
                    ),
                    {
                        "uid": uid,
                        "cid": course,
                        "title": f"Assessment {number}-{index}",
                        "n": index,
                    },
                )
            session.execute(
                text(
                    "INSERT INTO mcq.assessments(owner_id,title,kind,mode) VALUES(:uid,'Private practice','practice','adaptive')"
                ),
                {"uid": uid},
            )
    result = client.get("/api/v1/teacher/dashboard", headers=tokens[0])
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["counts"] == dict(courses=1, materials=1, questions=1, assessments=7)
    assert [item["title"] for item in data["recent_assessments"]] == [
        f"Assessment 0-{n}" for n in [6, 5, 4, 3, 2]
    ]
    assert "owner_id" not in result.text and "Private practice" not in result.text


@pytest.mark.integration
@integration
def test_teacher_student_denial_revoked_role_and_body_limit(teachers):
    client, app, ids, tokens = teachers
    result = client.post(
        "/api/v1/auth/register",
        json={
            "email": "student@example.com",
            "password": "Student fixture 42!",
            "display_name": "Student",
        },
    )
    assert result.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "student@example.com", "password": "Student fixture 42!"},
    )
    student_headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.get("/api/v1/teacher/dashboard", headers=student_headers).status_code == 403
    assert (
        client.post(
            "/api/v1/teacher/courses", headers=student_headers, json={"title": "Denied"}
        ).status_code
        == 403
    )
    assert (
        client.post("/api/v1/teacher/courses", headers=tokens[0], content="x" * 17000).status_code
        == 413
    )
    with owner(app.state.database), app.state.database.session() as session, session.begin():
        session.execute(
            text("DELETE FROM mcq.user_roles WHERE user_id=:id AND role='teacher'"), {"id": ids[0]}
        )
    # Removing the last role makes the identity unusable; authentication rejects it.
    assert client.get("/api/v1/teacher/dashboard", headers=tokens[0]).status_code == 401


@pytest.mark.integration
@integration
def test_topic_cap_and_runtime_grants(teachers):
    client, app, ids, tokens = teachers
    result = client.post(
        "/api/v1/teacher/courses", headers=tokens[0], json={"title": "Many topics"}
    )
    assert result.status_code == 201
    course_id = result.json()["id"]
    with owner(app.state.database), app.state.database.session() as session, session.begin():
        session.execute(
            text(
                "INSERT INTO mcq.topics(owner_id,course_id,name) SELECT :uid,:cid,'Topic ' || n FROM generate_series(1,100) n"
            ),
            {"uid": ids[0], "cid": course_id},
        )
    assert (
        client.post(
            f"/api/v1/teacher/courses/{course_id}/topics",
            headers=tokens[0],
            json={"title": "Excess"},
        ).json()["error"]["code"]
        == "TOPIC_LIMIT"
    )
    with app.state.database.session() as session:
        assert session.execute(
            text(
                "SELECT has_column_privilege(current_user,'mcq.courses','title','INSERT') AND NOT has_table_privilege(current_user,'mcq.courses','UPDATE,DELETE') AND NOT has_table_privilege(current_user,'mcq.assessments','INSERT,UPDATE,DELETE')"
            )
        ).scalar_one()
