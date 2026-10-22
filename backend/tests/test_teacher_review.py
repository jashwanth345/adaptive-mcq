"""Synthetic workflow evidence only: no model inference or quality measurements."""

from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from backend.app.teacher.review import Decision, Edit
from backend.tests.test_generator import payload
from backend.tests.test_materials import pdf_bytes
from backend.tests.test_rag import FakeEncoder
from backend.tests.test_teacher import integration, owner, teachers  # noqa: F401
from backend.tests.test_verifier import answer, critique, upload_and_generate

ROOT = "/api/v1/teacher/reviews"


def edit_body(draft, **changes):
    return {
        **{
            key: draft[key]
            for key in (
                "stem",
                "options",
                "correct_option",
                "explanation",
                "difficulty",
                "cognitive_level",
            )
        },
        "idempotency_key": str(uuid4()),
        "note": "Clarify the wording for the review.",
        **changes,
    }


def decision(action="approve", **changes):
    return {
        "idempotency_key": str(uuid4()),
        "action": action,
        "note": "Teacher reviewed the source and all options.",
        **changes,
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"correct_option": True},
        {"options": ["A", "a", "B", "C"]},
        {"stem": " " * 11},
        {"note": " "},
        {"mode": "ollama"},
        {"options": ["a\0", "b", "c", "d"]},
    ],
)
def test_edit_contract_rejects_invalid_or_injected_values(changes):
    data = dict(
        stem="A valid question?",
        options=["A", "B", "C", "D"],
        correct_option=0,
        explanation="A valid explanation.",
        difficulty="easy",
        cognitive_level="understand",
    )
    with pytest.raises(ValidationError):
        Edit(**edit_body(data, **changes))


def test_decision_contract_requires_explicit_note_and_forbids_scores():
    with pytest.raises(ValidationError):
        Decision(**decision(score=100))
    with pytest.raises(ValidationError):
        Decision(**decision(note=""))


@pytest.mark.integration
@integration
def test_mock_edit_history_retries_rejection_and_isolation(request, tmp_path):
    client, app, ids, tokens = request.getfixturevalue("teachers")
    _, version = upload_and_generate(client, app, tokens, tmp_path)
    path = f"{ROOT}/{version}"
    assert client.get(ROOT).status_code == 401
    for suffix in ["", "/versions"]:
        assert client.get(path + suffix, headers=tokens[1]).status_code == 404
    detail = client.get(path, headers=tokens[0])
    assert detail.status_code == 200, detail.text
    assert detail.headers["cache-control"] == "no-store"
    original = detail.json()
    assert original["current"] and not original["can_approve"]
    assert "Test-generated" in original["blocker"]
    assert client.get(ROOT, headers=tokens[1]).json()["total"] == 0
    assert (
        client.post(path + "/decisions", json=decision(), headers=tokens[0]).json()["error"]["code"]
        == "TEACHER_APPROVAL_BLOCKED"
    )
    body = edit_body(original["draft"], stem="Which process reduces redundant data?")
    for suffix, data in [("edits", body), ("decisions", decision())]:
        assert client.post(path + "/" + suffix, json=data, headers=tokens[1]).status_code == 404
    changed = client.post(path + "/edits", json=body, headers=tokens[0])
    assert changed.status_code == 200, changed.text
    new = changed.json()
    vid = new["draft"]["id"]
    assert new["version"] == 2 and vid != version and not new["can_approve"]
    assert (
        new["draft"]["mode"] == "mock"
        and new["draft"]["evidence_quote"] == original["draft"]["evidence_quote"]
    )
    assert client.post(path + "/edits", json=body, headers=tokens[0]).json()["draft"]["id"] == vid
    assert (
        client.post(
            path + "/edits", json={**body, "stem": "Another retry question?"}, headers=tokens[0]
        ).json()["error"]["code"]
        == "TEACHER_REVIEW_KEY_CONFLICT"
    )
    assert (
        client.post(
            path + "/edits", json={**body, "idempotency_key": str(uuid4())}, headers=tokens[0]
        ).json()["error"]["code"]
        == "TEACHER_REVIEW_STALE"
    )
    old = client.get(path, headers=tokens[0]).json()
    assert not old["current"] and old["draft"] == original["draft"]
    history = client.get(path + "/versions?offset=0&limit=1", headers=tokens[0]).json()
    assert history["total"] == 2 and history["items"][0]["events"][0]["action"] == "edit"
    assert (
        client.get(path + "/versions?offset=1&limit=1", headers=tokens[0]).json()["items"][0]["id"]
        == version
    )
    assert client.get(ROOT + "?offset=0&limit=1", headers=tokens[0]).json()["items"][0]["id"] == vid
    newpath = f"{ROOT}/{vid}"
    rejected = decision("reject")
    assert (
        client.post(newpath + "/decisions", json=rejected, headers=tokens[0]).json()["state"]
        == "rejected"
    )
    assert client.post(newpath + "/decisions", json=rejected, headers=tokens[0]).status_code == 200
    assert (
        client.post(newpath + "/decisions", json=decision(), headers=tokens[0]).json()["error"][
            "code"
        ]
        == "TEACHER_REVIEW_REJECTED"
    )
    edited = client.post(newpath + "/edits", json=edit_body(new["draft"]), headers=tokens[0])
    assert (
        edited.status_code == 200
        and edited.json()["version"] == 3
        and edited.json()["state"] == "pending"
    )
    assert (
        client.post(newpath + "/edits", content="x" * 17000, headers=tokens[0]).status_code == 413
    )
    assert (
        client.post(
            newpath + "/edits", json={**body, "owner_id": str(ids[1])}, headers=tokens[0]
        ).status_code
        == 422
    )
    assert client.get(path + "/versions?limit=11", headers=tokens[0]).status_code == 422
    with app.state.database.session() as session:
        assert session.execute(text("SELECT count(*) FROM mcq.question_releases")).scalar_one() == 0
        assert (
            session.execute(text("SELECT count(*) FROM mcq.teacher_review_events")).scalar_one()
            == 3
        )
        assert not session.execute(
            text(
                "SELECT has_table_privilege(current_user,'mcq.question_releases','INSERT,UPDATE,DELETE') OR has_table_privilege(current_user,'mcq.teacher_review_events','INSERT,UPDATE,DELETE')"
            )
        ).scalar_one()


def synthetic_ai_draft(client, app, tokens, tmp_path, monkeypatch):
    from backend.app.generator.mock import generate_mock

    app.state.materials.root = tmp_path / "uploads"
    app.state.rag.encoder = FakeEncoder()
    app.state.generator.settings = app.state.generator.settings.model_copy(
        update={"generator_mode": "ollama"}
    )
    monkeypatch.setattr(app.state.generator.client, "inspect", lambda: {})
    monkeypatch.setattr(
        app.state.generator.client,
        "generate",
        lambda *_: (
            generate_mock({"citation": "S1", "excerpt": "Normalization reduces redundant data."}),
            {"model": "fixture", "digest": "a" * 64},
        ),
    )
    upload = client.post(
        "/api/v1/materials?title=Synthetic%20AI%20fixture",
        content=pdf_bytes(("Normalization reduces redundant data.",)),
        headers={**tokens[0], "Content-Type": "application/pdf"},
    )
    assert upload.status_code == 201, upload.text
    mid = upload.json()["id"]
    assert client.post(f"/api/v1/rag/materials/{mid}/index", headers=tokens[0]).status_code == 200
    generated = client.post(
        "/api/v1/generator/drafts", json=payload(material_ids=[mid]), headers=tokens[0]
    )
    assert generated.status_code == 200, generated.text
    app.state.verifier.settings = app.state.verifier.settings.model_copy(
        update={"verifier_mode": "ollama"}
    )
    monkeypatch.setattr(
        app.state.verifier.client,
        "review",
        lambda _: (
            answer(),
            critique(),
            {"blind": {"digest": "a" * 64}, "critique": {"digest": "a" * 64}},
        ),
    )
    return generated.json()["id"]


def passing_checks(client, version, token):
    review = client.post(
        f"/api/v1/verifier/drafts/{version}/reports",
        json={"idempotency_key": str(uuid4())},
        headers=token,
    )
    assert review.status_code == 200 and review.json()["recommendation"] == "PASS", review.text
    validation = client.post(
        f"/api/v1/validation/drafts/{version}/reports",
        json={"idempotency_key": str(uuid4())},
        headers=token,
    )
    assert validation.status_code == 200 and validation.json()["technical_pass"], validation.text
    return validation.json()["id"]


@pytest.mark.integration
@integration
def test_synthetic_approval_exact_evidence_edit_quarantine_and_fresh_checks(
    request, tmp_path, monkeypatch
):
    client, app, ids, tokens = request.getfixturevalue("teachers")
    version = synthetic_ai_draft(client, app, tokens, tmp_path, monkeypatch)
    path = f"{ROOT}/{version}"
    validation = passing_checks(client, version, tokens[0])
    assert client.get(path, headers=tokens[0]).json()["can_approve"]
    body = decision()
    approved = client.post(path + "/decisions", json=body, headers=tokens[0])
    assert approved.status_code == 200, approved.text
    assert approved.json()["state"] == "approved"
    assert client.post(path + "/decisions", json=body, headers=tokens[0]).status_code == 200
    with app.state.database.session() as session:
        row = (
            session.execute(
                text(
                    "SELECT r.*,e.validation_report_id FROM mcq.question_releases r JOIN mcq.teacher_review_events e ON e.id=r.teacher_review_id"
                )
            )
            .mappings()
            .one()
        )
        assert row["verification_id"] is None and str(row["validation_report_id"]) == validation
        assert str(row["reviewed_by"]) == str(ids[0])
        assert (
            session.execute(text("SELECT count(*) FROM mcq.question_verifications")).scalar_one()
            == 0
        )
        assert session.execute(text("SELECT count(*) FROM mcq.assessments")).scalar_one() == 0
    edited = client.post(
        path + "/edits",
        json=edit_body(approved.json()["draft"], stem="Which method reduces redundant data?"),
        headers=tokens[0],
    )
    assert edited.status_code == 200, edited.text
    new = edited.json()
    new_id = new["draft"]["id"]
    newpath = f"{ROOT}/{new_id}"
    assert new["state"] == "pending" and not new["can_approve"]
    assert client.get(path, headers=tokens[0]).json()["state"] == "quarantined"
    for layer in ["validation", "verifier"]:
        assert (
            client.get(f"/api/v1/{layer}/drafts/{new_id}/reports", headers=tokens[0]).json()[
                "total"
            ]
            == 0
        )
    assert (
        client.post(newpath + "/decisions", json=decision(), headers=tokens[0]).status_code == 409
    )
    passing_checks(client, new_id, tokens[0])
    assert (
        client.post(newpath + "/decisions", json=decision(), headers=tokens[0]).json()["state"]
        == "approved"
    )
    assert (
        client.post(newpath + "/decisions", json=decision("reject"), headers=tokens[0]).json()[
            "state"
        ]
        == "rejected"
    )
    assert (
        client.post(newpath + "/decisions", json=decision(), headers=tokens[0]).status_code == 409
    )
    with app.state.database.session() as session:
        assert (
            session.execute(
                text("SELECT count(*) FROM mcq.question_releases WHERE state='approved'")
            ).scalar_one()
            == 0
        )


@pytest.mark.integration
@integration
def test_edit_atomicity_and_temporary_shadow_tables_cannot_approve_mock(request, tmp_path):
    client, app, ids, tokens = request.getfixturevalue("teachers")
    _, version = upload_and_generate(client, app, tokens, tmp_path)
    draft = client.get(f"{ROOT}/{version}", headers=tokens[0]).json()["draft"]

    # A failure after all function writes but before commit rolls everything back.
    def fail_after_write(conn, cursor, statement, parameters, context, executemany):
        if "SELECT mcq.teacher_review_action" in statement:
            raise SQLAlchemyError("Synthetic failure before commit")

    event.listen(app.state.database.engine, "after_cursor_execute", fail_after_write)
    body = edit_body(draft)
    try:
        assert (
            client.post(f"{ROOT}/{version}/edits", json=body, headers=tokens[0]).status_code == 503
        )
    finally:
        event.remove(app.state.database.engine, "after_cursor_execute", fail_after_write)
    with owner(app.state.database), app.state.database.session() as session, session.begin():
        assert session.execute(text("SELECT count(*) FROM mcq.question_versions")).scalar_one() == 1
        assert (
            session.execute(text("SELECT count(*) FROM mcq.teacher_review_events")).scalar_one()
            == 0
        )
    assert client.post(f"{ROOT}/{version}/edits", json=body, headers=tokens[0]).status_code == 200
    with app.state.database.session() as session, session.begin():
        session.execute(
            text(
                "CREATE TEMP TABLE validation_reports (technical_pass boolean); CREATE TEMP TABLE question_versions (id uuid)"
            )
        )
        assert not session.execute(
            text("SELECT mcq.teacher_approval_ready(:uid,:vid)"), {"uid": ids[0], "vid": version}
        ).scalar_one()
        session.execute(
            text("DROP TABLE pg_temp.validation_reports; DROP TABLE pg_temp.question_versions")
        )
    with app.state.database.session() as session, pytest.raises(DBAPIError):
        session.execute(text("UPDATE mcq.teacher_review_events SET action='approve'"))


@pytest.mark.integration
@integration
def test_student_and_revoked_teacher_cannot_review(request, tmp_path):
    client, app, ids, tokens = request.getfixturevalue("teachers")
    _, version = upload_and_generate(client, app, tokens, tmp_path)
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "student.review@example.com",
            "password": "Student review fixture!",
            "display_name": "Student",
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "student.review@example.com", "password": "Student review fixture!"},
    )
    token = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.get(ROOT, headers=token).status_code == 403
    assert client.get(f"{ROOT}/{version}", headers=token).status_code == 403
    assert (
        client.post(f"{ROOT}/{version}/decisions", json=decision(), headers=token).status_code
        == 403
    )
    with owner(app.state.database), app.state.database.session() as session, session.begin():
        session.execute(text("DELETE FROM mcq.user_roles WHERE user_id=:id"), {"id": ids[0]})
    assert (
        client.post(f"{ROOT}/{version}/decisions", json=decision(), headers=tokens[0]).status_code
        == 401
    )
