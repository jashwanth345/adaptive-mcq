"""Synthetic application evidence, never local LLM quality evaluation."""

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from backend.app.attempts import Save
from backend.tests.test_assessments import ROOT, command, make_assessment, post, student_account
from backend.tests.test_teacher import integration, owner, teachers  # noqa: F401
from backend.tests.test_teacher_review import decision, passing_checks, synthetic_ai_draft
from backend.tests.test_verifier import upload_and_generate

STUDENT = "/api/v1/student"


def prepared(request, tmp_path, monkeypatch, release="after_submit", seconds=None):
    client, app, ids, tokens = request.getfixturevalue("teachers")
    version = synthetic_ai_draft(client, app, tokens, tmp_path, monkeypatch)
    passing_checks(client, version, tokens[0])
    assert (
        client.post(
            f"/api/v1/teacher/reviews/{version}/decisions", json=decision(), headers=tokens[0]
        ).status_code
        == 200
    )
    detail, body = make_assessment(client, tokens[0], version)
    target = detail["id"]
    body.pop("course_id")
    body.update(
        command(
            revision=1,
            release_policy=release,
            time_limit_seconds=seconds,
            randomize_options=True,
            max_attempts=2,
        )
    )
    saved = client.post(f"{ROOT}/{target}/save", headers=tokens[0], json=body)
    assert saved.status_code == 200, saved.text
    student, sid = student_account(client)
    assert (
        post(client, target, "participants", tokens[0], email="permitted@example.com").status_code
        == 200
    )
    pub = post(client, target, "publish", tokens[0], revision=2)
    assert pub.status_code == 200, pub.text
    assert (
        client.post(
            STUDENT + "/assessments/join", headers=student, json={"code": pub.json()["issued_code"]}
        ).status_code
        == 200
    )
    started = client.post(
        f"{STUDENT}/assessments/{target}/attempts", headers=student, json=command()
    )
    assert started.status_code == 200, started.text
    return client, app, tokens, student, sid, version, target, started.json()


def save(client, token, attempt, option=0, **extra):
    return client.post(
        f"{STUDENT}/attempts/{attempt['id']}/save",
        headers=token,
        json=command(
            revision=attempt["revision"],
            answers=[dict(position=1, selected_option=option, flagged=True)],
            **extra,
        ),
    )


def submit(client, token, attempt, body=None):
    return client.post(
        f"{STUDENT}/attempts/{attempt['id']}/submit",
        headers=token,
        json=body or command(revision=attempt["revision"]),
    )


def test_answers_reject_duplicate_positions_client_scores_and_invalid_options():
    for answers in [
        [dict(position=1, selected_option=True)],
        [dict(position=1, selected_option=4)],
        [dict(position=1, awarded_points=1)],
        [dict(position=1), dict(position=1)],
    ]:
        with pytest.raises(ValidationError):
            Save(**command(revision=1, answers=answers))


@pytest.mark.integration
@integration
def test_snapshot_save_resume_score_privacy_and_retry(request, tmp_path, monkeypatch):
    client, app, tokens, student, sid, version, target, attempt = prepared(
        request, tmp_path, monkeypatch
    )
    item = attempt["items"][0]
    assert not attempt["results_released"] and "result" not in attempt
    assert all(
        k not in item
        for k in ["correct_option", "explanation", "is_correct", "source_quotes", "option_order"]
    )
    assert client.get(f"{STUDENT}/attempts/{attempt['id']}", headers=tokens[0]).status_code == 403
    stranger, _ = student_account(client, "stranger@example.com")
    assert client.get(f"{STUDENT}/attempts/{attempt['id']}", headers=stranger).status_code == 404
    assert (
        client.post(
            f"{STUDENT}/assessments/{target}/attempts", headers=student, json=command()
        ).json()["id"]
        == attempt["id"]
    )
    with app.state.database.session() as session:
        # Test-only expected key from immutable source, never supplied by the browser.
        correct = session.execute(
            text("SELECT correct_option FROM mcq.question_versions WHERE id=:v"), {"v": version}
        ).scalar_one()
        options = (
            session.execute(
                text("SELECT content FROM mcq.options WHERE version_id=:v ORDER BY ordinal"),
                {"v": version},
            )
            .scalars()
            .all()
        )
    display = item["options"].index(options[correct])
    saved = save(client, student, attempt, display)
    assert saved.status_code == 200, saved.text
    value = saved.json()
    assert value["items"][0]["flagged"] and value["revision"] == 2
    assert save(client, student, attempt, display).json()["error"]["code"] == "ATTEMPT_STALE"
    reopened = client.get(f"{STUDENT}/attempts/{attempt['id']}", headers=student).json()
    assert reopened["items"] == value["items"]
    # A replacement/revocation affects new access, not an already admitted snapshot.
    assert post(client, target, "revoke", tokens[0]).status_code == 200
    body = command(revision=2)
    result = submit(client, student, value, body)
    assert result.status_code == 200, result.text
    result = result.json()
    assert result["state"] == "submitted" and result["result"]["awarded_points"] == 1
    assert result["items"][0]["correct_option"] == display and result["items"][0]["is_correct"]
    assert result["items"][0]["source_quotes"]
    assert submit(client, student, value, body).json()["result"] == result["result"]
    assert submit(client, student, value).json()["result"] == result["result"]
    assert save(client, student, value).json()["error"]["code"] == "ATTEMPT_FINISHED"
    assert (
        client.post(
            f"{STUDENT}/assessments/{target}/attempts", headers=student, json=command()
        ).status_code
        == 409
    )
    learned = client.get(STUDENT + "/learning", headers=student)
    assert learned.status_code == 200, learned.text
    assert learned.json()["eligible_observations"] == 1
    assert learned.json()["topics"][0]["performance_index"] is None
    with owner(app.state.database), app.state.database.session() as session:
        assert (
            session.execute(
                text("SELECT count(*) FROM mcq.mastery_evidence WHERE student_id=:s"), {"s": sid}
            ).scalar_one()
            == 1
        )


@pytest.mark.integration
@integration
def test_result_embargo_skips_and_quarantine_filter(request, tmp_path, monkeypatch):
    client, app, tokens, student, _, version, target, attempt = prepared(
        request, tmp_path, monkeypatch, release="after_close"
    )
    saved = save(client, student, attempt, 0).json()
    done = submit(client, student, saved)
    assert done.status_code == 200, done.text
    assert not done.json()["results_released"] and "result" not in done.json()
    assert "correct_option" not in done.json()["items"][0]
    assert client.get(STUDENT + "/learning", headers=student).json()["eligible_observations"] == 0
    assert post(client, target, "close", tokens[0]).status_code == 200
    result = client.get(f"{STUDENT}/attempts/{attempt['id']}", headers=student).json()
    assert result["results_released"] and "correct_option" in result["items"][0]
    assert client.get(STUDENT + "/learning", headers=student).json()["eligible_observations"] == 1
    assert (
        client.post(
            f"/api/v1/teacher/reviews/{version}/decisions",
            headers=tokens[0],
            json=decision("reject"),
        ).status_code
        == 200
    )
    assert client.get(STUDENT + "/learning", headers=student).json()["eligible_observations"] == 0
    quarantined = client.get(f"{STUDENT}/attempts/{attempt['id']}", headers=student).json()
    assert (
        quarantined["items"][0]["under_review"] and "correct_option" not in quarantined["items"][0]
    )


@pytest.mark.integration
@integration
def test_deadline_finalizes_saved_answers_without_accepting_late_changes(
    request, tmp_path, monkeypatch
):
    client, app, _, student, _, _, _, attempt = prepared(request, tmp_path, monkeypatch, seconds=60)
    with owner(app.state.database), app.state.database.session() as session, session.begin():
        session.execute(
            text(
                "UPDATE mcq.attempt_sessions SET deadline=clock_timestamp()-interval '1 second' WHERE attempt_id=:id"
            ),
            {"id": attempt["id"]},
        )
    response = save(client, student, attempt, 0)
    assert response.status_code == 200, response.text
    done = response.json()
    assert done["state"] == "expired" and done["result"]["awarded_points"] == 0
    assert "selected_option" not in done["items"][0]
    assert client.get(STUDENT + "/learning", headers=student).json()["eligible_observations"] == 0
    assert (
        client.get(f"{STUDENT}/attempts/{attempt['id']}", headers=student).json()["state"]
        == "expired"
    )


@pytest.mark.integration
@integration
def test_mock_private_practice_cannot_start(request, tmp_path):
    client, app, _, tokens = request.getfixturevalue("teachers")
    student, _ = student_account(client)
    _, version = upload_and_generate(client, app, [student], tmp_path)
    response = client.post(
        STUDENT + "/practice/start", headers=student, json=command(version_id=version)
    )
    assert response.status_code == 409 and response.json()["error"]["code"] == "PRACTICE_BLOCKED"
    assert client.get(STUDENT + "/learning", headers=student).json()["recommendation"] is None


@pytest.mark.integration
@integration
def test_private_practice_automatic_evidence_unseen_selection_and_no_repeat_mastery(
    request, tmp_path, monkeypatch
):
    client, app, _, _ = request.getfixturevalue("teachers")
    student, sid = student_account(client)
    version = synthetic_ai_draft(client, app, [student], tmp_path, monkeypatch)
    passing_checks(client, version, student)
    learning = client.get(STUDENT + "/learning", headers=student)
    assert learning.status_code == 200, learning.text
    assert learning.json()["recommendation"]["version_id"] == version
    payload = command(version_id=version)
    started = client.post(STUDENT + "/practice/start", headers=student, json=payload)
    assert started.status_code == 200, started.text
    attempt = started.json()
    assert (
        client.post(STUDENT + "/practice/start", headers=student, json=payload).json()["id"]
        == attempt["id"]
    )
    saved = save(client, student, attempt, 0).json()
    done = submit(client, student, saved)
    assert done.status_code == 200, done.text
    assert done.json()["results_released"]
    assert client.get(STUDENT + "/learning", headers=student).json()["recommendation"] is None
    next_attempt = client.post(
        STUDENT + "/practice/start", headers=student, json=command(version_id=version)
    )
    assert next_attempt.status_code == 200, next_attempt.text
    saved = save(client, student, next_attempt.json(), 0).json()
    assert submit(client, student, saved).status_code == 200
    assert client.get(STUDENT + "/learning", headers=student).json()["eligible_observations"] == 1
    with owner(app.state.database), app.state.database.session() as session:
        assert (
            session.execute(
                text("SELECT count(*) FROM mcq.mastery_evidence WHERE student_id=:s"), {"s": sid}
            ).scalar_one()
            == 1
        )
        assert (
            session.execute(
                text(
                    "SELECT automatic_validation_id FROM mcq.question_releases WHERE version_id=:v"
                ),
                {"v": version},
            ).scalar_one()
            is not None
        )
