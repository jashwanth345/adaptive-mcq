"""Synthetic workflows only; no learner study or model-quality claims."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.app.feedback import Decision, Report, prioritize
from backend.tests.test_assessments import command, student_account
from backend.tests.test_attempts import prepared, save, submit
from backend.tests.test_teacher import integration, owner, teachers  # noqa: F401
from backend.tests.test_teacher_review import decision

ROOT = "/api/v1/feedback/reviews"


def report(client, token, attempt, version, **kwargs):
    body = command(version_id=version, category="wrong_answer", comment="Synthetic issue report")
    body.update(kwargs)
    return client.post(f"/api/v1/student/attempts/{attempt}/feedback", headers=token, json=body)


def decide(client, token, version, revision, action="review", **kwargs):
    body = command(revision=revision, action=action, note="Synthetic review decision")
    body.update(kwargs)
    return client.post(f"{ROOT}/{version}/decisions", headers=token, json=body)


@pytest.mark.parametrize(
    "extra",
    [
        {"category": "rating"},
        {"rating": "helpful"},
        {"category": "fake"},
        {"student_id": str(uuid4())},
        {"comment": "x" * 2001},
        {"comment": "bad\x00text"},
    ],
)
def test_feedback_contract_rejects_invalid_report(extra):
    data = command(version_id=str(uuid4()), category="wrong_answer")
    data.update(extra)
    with pytest.raises(ValidationError):
        Report(**data)


def test_decision_contract_and_priority(settings):
    with pytest.raises(ValidationError):
        Decision(**command(revision=True, action="confirm_defect", note="yes"))
    row = dict(open_reporters=3, exposures=10, grade_review="not_required")
    assert prioritize(row, settings)["priority"] == "elevated"
    assert prioritize({**row, "open_reporters": 2}, settings)["priority"] == "standard"
    assert prioritize({**row, "grade_review": "pending"}, settings)["priority"] == "score_review"
    assert Report(**command(version_id=str(uuid4()), category="rating", rating="helpful"))


@integration
def test_report_permissions_deduplication_and_history(request, tmp_path, monkeypatch):
    client, app, tokens, student, sid, version, target, attempt = prepared(
        request, tmp_path, monkeypatch
    )
    assert report(client, student, attempt["id"], version).status_code == 404
    finished = submit(client, student, attempt).json()
    assert finished["state"] == "submitted"
    body = command(version_id=version, category="ambiguous", comment="A synthetic ambiguity")
    path = f"/api/v1/student/attempts/{attempt['id']}/feedback"
    first = client.post(path, headers=student, json=body)
    assert first.status_code == 200, first.text
    assert not first.json()["duplicate"]
    assert client.post(path, headers=student, json=body).json() == first.json()
    assert (
        client.post(path, headers=student, json={**body, "comment": "Changed"}).status_code == 409
    )
    repeated = client.post(
        path, headers=student, json={**body, "idempotency_key": str(uuid4())}
    ).json()
    assert repeated["duplicate"] and repeated["report_id"] == first.json()["report_id"]
    assert report(client, student, attempt["id"], str(uuid4())).status_code == 404
    stranger, _ = student_account(client, "stranger@example.com")
    assert report(client, stranger, attempt["id"], version).status_code == 404
    assert report(client, tokens[0], attempt["id"], version).status_code == 403
    assert client.get("/api/v1/student/feedback", headers=stranger).json()["total"] == 0
    history = client.get("/api/v1/student/feedback", headers=student).json()
    assert history["total"] == 1 and history["items"][0]["comment"] == "A synthetic ambiguity"
    assert "student_id" not in history["items"][0]
    assert client.get(ROOT, headers=tokens[1]).json()["total"] == 0
    assert client.get(f"{ROOT}/{version}", headers=tokens[1]).status_code == 404
    assert client.get(f"{ROOT}/{version}", headers=student).status_code == 404
    detail = client.get(f"{ROOT}/{version}", headers=tokens[0]).json()
    assert detail["summary"]["reporters"] == detail["summary"]["exposures"] == 1
    assert "student_id" not in detail["reports"][0] and "email" not in detail["reports"][0]


@integration
def test_confirm_quarantines_blocks_reapproval_and_preserves_score(request, tmp_path, monkeypatch):
    client, app, tokens, student, sid, version, target, attempt = prepared(
        request, tmp_path, monkeypatch
    )
    saved = save(client, student, attempt).json()
    result = submit(client, student, saved).json()
    assert report(client, student, attempt["id"], version).status_code == 200
    first = client.get(f"{ROOT}/{version}", headers=tokens[0]).json()["summary"]
    assert decide(client, tokens[1], version, first["revision"]).status_code == 404
    assert decide(client, tokens[0], version, first["revision"]).status_code == 200
    assert (
        decide(client, tokens[0], version, first["revision"], "confirm_defect").status_code == 409
    )
    current = client.get(f"{ROOT}/{version}", headers=tokens[0]).json()["summary"]
    retry = command(
        revision=current["revision"],
        action="confirm_defect",
        note="Confirmed synthetic wrong answer",
    )
    path = f"{ROOT}/{version}/decisions"
    confirmed = client.post(path, headers=tokens[0], json=retry)
    assert confirmed.status_code == 200, confirmed.text
    assert client.post(path, headers=tokens[0], json=retry).json() == confirmed.json()
    item = client.get(f"/api/v1/student/attempts/{attempt['id']}", headers=student).json()
    assert item["result"] == result["result"] and item["items"][0]["under_review"]
    assert "correct_option" not in item["items"][0]
    assert (
        client.get("/api/v1/student/learning", headers=student).json()["eligible_observations"] == 0
    )
    assert (
        client.post(
            f"/api/v1/student/assessments/{target}/attempts", headers=student, json=command()
        ).status_code
        == 409
    )
    approval = client.post(
        f"/api/v1/teacher/reviews/{version}/decisions", headers=tokens[0], json=decision()
    )
    assert approval.status_code == 409
    assert not client.get(f"/api/v1/teacher/reviews/{version}", headers=tokens[0]).json()[
        "can_approve"
    ]
    detail = client.get(f"{ROOT}/{version}", headers=tokens[0]).json()
    assert detail["summary"]["grade_review"] == "pending"
    assert (
        "corrected new version"
        in client.get(f"/api/v1/teacher/reviews/{version}", headers=tokens[0]).json()["blocker"]
    )
    assert detail["summary"]["completed_attempts"] == 1
    assert (
        decide(client, tokens[0], version, detail["summary"]["revision"], "dismiss").status_code
        == 409
    )
    assert (
        decide(
            client, tokens[0], version, detail["summary"]["revision"], "acknowledge_grades"
        ).status_code
        == 200
    )
    assert (
        client.get(f"{ROOT}/{version}", headers=tokens[0]).json()["summary"]["grade_review"]
        == "acknowledged"
    )


@integration
def test_ratings_dismissal_and_new_category_reopen(request, tmp_path, monkeypatch):
    client, app, tokens, student, sid, version, target, attempt = prepared(
        request, tmp_path, monkeypatch, release="after_close"
    )
    submit(client, student, attempt)
    assert (
        report(
            client, student, attempt["id"], version, category="rating", rating="helpful"
        ).status_code
        == 200
    )
    summary = client.get(ROOT, headers=tokens[0]).json()["items"][0]
    assert summary["helpful"] == 1 and summary["reporters"] == 0
    assert decide(client, tokens[0], version, summary["revision"], "dismiss").status_code == 200
    assert report(client, student, attempt["id"], version, category="other").status_code == 200
    summary = client.get(ROOT, headers=tokens[0]).json()["items"][0]
    assert summary["state"] == "open" and summary["reporters"] == 1
    assert summary["release_state"] == "approved"
    history = client.get("/api/v1/student/feedback", headers=student).json()
    assert history["total"] == 2 and "note" not in str(history)
    assert (
        client.get(f"/api/v1/student/attempts/{attempt['id']}", headers=student).json()[
            "results_released"
        ]
        is False
    )
