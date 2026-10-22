"""Synthetic analytics checks; no research/model quality measurements."""

from uuid import uuid4

from sqlalchemy import text

from backend.tests.test_assessments import command, post, student_account
from backend.tests.test_attempts import prepared, save, submit
from backend.tests.test_feedback import decide, report
from backend.tests.test_teacher import integration, owner, teachers  # noqa: F401

STUDENT = "/api/v1/student/analytics"
TEACHER = "/api/v1/teacher/analytics"


def read(client, headers, path=STUDENT):
    response = client.get(path, headers=headers)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()


@integration
def test_empty_roles_ownership_and_query_limits(request):
    client, app, ids, tokens = request.getfixturevalue("teachers")
    student, sid = student_account(client)
    data = read(client, student)
    assert data["summary"]["attempts"] == 0
    assert data["summary"]["accuracy"] is None
    assert data["summary"]["average_score"] is None
    assert data["history"] == data["ranking"] == data["breakdowns"] == []
    assert client.get(STUDENT).status_code == 401
    assert client.get(TEACHER, headers=student).status_code == 403
    assert client.get(STUDENT, headers=tokens[0]).status_code == 403
    assert client.get(STUDENT + "?offset=-1", headers=student).status_code == 422
    assert client.get(STUDENT + "?limit=51", headers=student).status_code == 422
    assert (
        client.get(
            f"/api/v1/teacher/assessments/{uuid4()}/analytics", headers=tokens[0]
        ).status_code
        == 404
    )


@integration
def test_embargo_excludes_all_performance_until_close(request, tmp_path, monkeypatch):
    client, app, tokens, student, sid, version, target, attempt = prepared(
        request, tmp_path, monkeypatch, release="after_close"
    )
    submit(client, student, attempt)
    data = read(client, student)
    assert data["summary"]["attempts"] == data["summary"]["withheld"] == 1
    assert data["summary"]["scored_attempts"] == data["summary"]["items"] == 0
    assert data["summary"]["accuracy"] is data["summary"]["average_score"] is None
    assert data["breakdowns"] == []
    assert data["history"][0]["score_percent"] is None
    assert data["history"][0]["elapsed_seconds"] is None
    own = read(client, tokens[0], TEACHER)
    assert own["summary"]["average_score"] == 0
    assert own["summary"]["skipped"] == 1 and own["summary"]["accuracy"] is None
    foreign = read(client, tokens[1], TEACHER)
    assert foreign["summary"]["attempts"] == 0
    assert (
        client.get(f"/api/v1/teacher/assessments/{target}/analytics", headers=tokens[1]).status_code
        == 404
    )
    assert (
        post(
            client,
            target,
            "close",
            tokens[0],
        ).status_code
        == 200
    )
    released = read(client, student)
    assert released["summary"]["withheld"] == 0
    assert released["summary"]["skipped"] == 1
    assert released["history"][0]["score_percent"] == 0
    assert released["history"][0]["student_name"] is None
    assert "correct_option" not in str(released) and "explanation" not in str(released)


@integration
def test_repeat_attempts_paging_and_best_submitted_ranking(request, tmp_path, monkeypatch):
    client, app, tokens, student, sid, version, target, attempt = prepared(
        request, tmp_path, monkeypatch
    )
    # Read the synthetic canonical answer through trusted setup only, then select its shuffled display slot.
    with owner(app.state.database), app.state.database.session() as session:
        key = session.execute(
            text("SELECT correct_option FROM mcq.question_versions WHERE id=:id"), dict(id=version)
        ).scalar_one()
        order = session.execute(
            text("SELECT option_order FROM mcq.attempt_items WHERE attempt_id=:id"),
            dict(id=attempt["id"]),
        ).scalar_one()
    saved = save(client, student, attempt, option=order.index(key)).json()
    assert submit(client, student, saved).status_code == 200
    second = client.post(
        f"/api/v1/student/assessments/{target}/attempts", headers=student, json=command()
    ).json()
    assert submit(client, student, second).status_code == 200
    data = read(client, student, STUDENT + "?offset=1&limit=1")
    assert len(data["history"]) == 1 and data["summary"]["attempts"] == 2
    assert data["summary"]["average_score"] == 50
    assert data["summary"]["accuracy"] == 100
    assert data["summary"]["correct"] == data["summary"]["skipped"] == 1
    assert data["summary"]["students"] == 1
    assert all(row["items"] == 2 for row in data["breakdowns"])
    path = f"/api/v1/teacher/assessments/{target}/analytics"
    assert read(client, tokens[0], path)["ranking"] == []
    ranked = read(client, tokens[0], path + "?ranking=true")
    assert len(ranked["ranking"]) == 1 and ranked["ranking"][0]["score_percent"] == 100
    assert ranked["ranking"][0]["rank"] == 1
    assert ranked["missed_items"][0]["missed_percent"] == 50
    assert ranked["missed_items"][0]["exposures"] == 2
    stranger, _ = student_account(client, "analytics.stranger@example.com")
    assert read(client, stranger)["summary"]["attempts"] == 0


@integration
def test_quarantine_preserves_original_score_excludes_breakdowns_and_ranking(
    request, tmp_path, monkeypatch
):
    client, app, tokens, student, sid, version, target, attempt = prepared(
        request, tmp_path, monkeypatch
    )
    submit(client, student, save(client, student, attempt).json())
    before = read(client, student)
    assert report(client, student, attempt["id"], version).status_code == 200
    summary = client.get(f"/api/v1/feedback/reviews/{version}", headers=tokens[0]).json()["summary"]
    assert (
        decide(client, tokens[0], version, summary["revision"], "confirm_defect").status_code == 200
    )
    after = read(client, student)
    assert after["summary"]["average_score"] == before["summary"]["average_score"]
    assert after["summary"]["excluded_items"] == 1
    assert after["summary"]["accuracy"] is None and after["breakdowns"] == []
    assert after["feedback"]["reports"] == after["feedback"]["issue_reporters"] == 1
    assert after["feedback"]["open_issues"] == 0
    teacher = read(
        client, tokens[0], f"/api/v1/teacher/assessments/{target}/analytics?ranking=true"
    )
    assert teacher["ranking"] == teacher["missed_items"] == []


@integration
def test_overdue_is_read_only_expiry_time_is_capped_and_roles_are_live(
    request, tmp_path, monkeypatch
):
    client, app, tokens, student, sid, version, target, attempt = prepared(
        request, tmp_path, monkeypatch, seconds=60
    )
    with owner(app.state.database), app.state.database.session() as session:
        session.execute(
            text(
                "UPDATE mcq.attempt_sessions SET deadline=clock_timestamp()-interval '1 second' WHERE attempt_id=:id"
            ),
            dict(id=attempt["id"]),
        )
        session.commit()
    pending = read(client, student)
    assert pending["summary"]["overdue"] == pending["summary"]["in_progress"] == 1
    assert pending["summary"]["scored_attempts"] == 0
    ended = client.get(f"/api/v1/student/attempts/{attempt['id']}", headers=student)
    assert ended.json()["state"] == "expired"
    data = read(client, student)
    assert data["summary"]["expired"] == 1 and data["summary"]["skipped"] == 1
    assert 0 <= data["summary"]["average_elapsed_seconds"] <= 60
    assert (
        read(client, tokens[0], f"/api/v1/teacher/assessments/{target}/analytics?ranking=true")[
            "ranking"
        ]
        == []
    )
    with owner(app.state.database), app.state.database.session() as session:
        session.execute(
            text("DELETE FROM mcq.user_roles WHERE user_id=:id AND role='student'"), dict(id=sid)
        )
        session.commit()
    assert client.get(STUDENT, headers=student).status_code in (401, 403)
