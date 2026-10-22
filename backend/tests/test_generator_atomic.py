import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import SQLAlchemyError

from backend.tests.test_generator import payload
from backend.tests.test_materials import pdf_bytes
from backend.tests.test_student import integration, operator, students  # noqa: F401


@pytest.mark.integration
@integration
def test_failed_source_insert_rolls_back_entire_draft_and_allows_retry(request, tmp_path):
    client, app, ids, tokens = request.getfixturevalue("students")
    app.state.materials.root = tmp_path / "uploads"
    uploaded = client.post(
        "/api/v1/materials?title=Atomic%20source",
        content=pdf_bytes(("Normalization reduces redundant data.",)),
        headers={**tokens[0], "Content-Type": "application/pdf"},
    )
    assert uploaded.status_code == 201
    body = payload(material_ids=[uploaded.json()["id"]])

    def fail_source_insert(connection, cursor, statement, parameters, context, many):
        # Inject after earlier real SQL writes, before commit. Server-side FK
        # errors desynchronize the test-only PGlite socket protocol; native FK
        # recovery needs a native PostgreSQL trial. This checks real rollback.
        if "INSERT INTO mcq.question_sources" in statement:
            raise SQLAlchemyError("Synthetic source-write failure")

    engine = app.state.database.engine
    event.listen(engine, "before_cursor_execute", fail_source_insert)
    try:
        failed = client.post("/api/v1/generator/drafts", json=body, headers=tokens[0])
    finally:
        event.remove(engine, "before_cursor_execute", fail_source_insert)
    assert failed.status_code == 503, failed.text
    with operator(app.state.database), app.state.database.session() as session:
        for table in (
            "jobs",
            "generation_runs",
            "questions",
            "question_versions",
            "options",
            "question_sources",
            "topics",
        ):
            assert session.execute(text(f"SELECT count(*) FROM mcq.{table}")).scalar_one() == 0
        assert (
            session.execute(
                text(
                    "SELECT count(*) FROM mcq.audit_events WHERE event_type='generation.draft_created'"
                )
            ).scalar_one()
            == 0
        )
    recovered = client.post("/api/v1/generator/drafts", json=body, headers=tokens[0])
    assert recovered.status_code == 200, recovered.text
    assert client.get("/api/v1/generator/drafts", headers=tokens[0]).json()["total"] == 1
