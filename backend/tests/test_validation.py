from fractions import Fraction
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.validation.duplicates import compare, normalize
from backend.app.validation.math_check import Unsupported, arithmetic, check_math
from backend.tests.test_generator import payload
from backend.tests.test_student import integration, students  # noqa: F401
from backend.tests.test_verifier import upload_and_generate


@pytest.mark.parametrize(
    "expression,expected",
    [
        ("0.1+0.2", Fraction(3, 10)),
        ("(3+5)/2", 4),
        ("2**-3", Fraction(1, 8)),
        ("-(-4)", 4),
        ("1/3+1/6", Fraction(1, 2)),
    ],
)
def test_exact_arithmetic(expression, expected):
    assert arithmetic(expression) == expected


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os')",
        "open('file')",
        "1e9",
        "nan",
        "2//1",
        "2%1",
        "[1][0]",
        "2**999",
        "2**(2**8)",
        "9" * 25,
        "1+" * 70 + "1",
        "x+1",
        "sqrt(4)",
        "1<2",
        "(1,2)",
    ],
)
def test_unsupported_and_resource_expressions(expression):
    with pytest.raises(Unsupported):
        arithmetic(expression)


@pytest.mark.parametrize(
    "stem,options,key,status",
    [
        ("Calculate: 0.1 + 0.2", ["0.3", "0.4", "0.5", "0.6"], 0, "pass"),
        ("Evaluate: 1/2", ["0.5", "1/2", "1", "2"], 0, "fail"),
        ("Calculate: 2+2", ["4", "3", "5", "6"], 1, "fail"),
        ("Calculate: 2+2", ["1", "2", "3", "5"], 0, "fail"),
        ("Calculate: 1/0", ["0", "1", "2", "3"], 0, "fail"),
        ("Calculate: 0**0", ["0", "1", "2", "3"], 0, "fail"),
        ("Calculate: 1/3", ["0.33", "1", "2", "3"], 0, "fail"),
        ("Calculate: 1+1", ["2 m", "1", "3", "4"], 0, "unsupported"),
        ("Find the average of five values", ["1", "2", "3", "4"], 0, "unsupported"),
    ],
)
def test_math_answerability(stem, options, key, status):
    assert check_math(stem, options, key)["status"] == status


def test_conceptual_math_triage_is_conservative():
    assert check_math("What is normalization?", [], 0, "conceptual")["status"] == "not_applicable"
    assert check_math("How many are 2 plus 2?", [], 0, "conceptual")["status"] == "unsupported"
    assert check_math("Which program output?", [], 0, "code")["status"] == "unsupported"


def test_duplicate_normalization_near_matches_and_incomplete_scan():
    stem = "Which relational database operation combines rows from multiple tables?"
    rows = [
        {"id": uuid4(), "stem": stem.upper()},
        {"id": uuid4(), "stem": stem.replace("relational ", "")},
        {"id": uuid4(), "stem": "Unrelated content"},
    ]
    result = compare(stem, rows)
    assert result["match_count"] == 2 and result["matches"][0]["kind"] == "exact"
    assert result["matches"][1]["kind"] == "near"
    assert normalize("Ａ  B!") == "a b"
    assert normalize("2+2") != normalize("2-2")
    result = compare(stem, [{"id": uuid4(), "stem": "unrelated"}] * 2001)
    assert result["status"] == "incomplete" and not result["complete"]


@pytest.mark.integration
@integration
def test_private_validation_math_preview_idempotency_duplicates_and_rollback(
    request, tmp_path, monkeypatch
):
    client, app, ids, tokens = request.getfixturevalue("students")
    material, version = upload_and_generate(client, app, tokens, tmp_path)

    def no_ai(*args, **kwargs):
        pytest.fail("Validation must not load or call an AI model")

    monkeypatch.setattr(app.state.verifier.client, "review", no_ai)
    url = f"/api/v1/validation/drafts/{version}/reports"
    key = {"idempotency_key": str(uuid4())}
    assert client.post(url, json=key).status_code == 401
    assert client.post(url, json=key, headers=tokens[1]).status_code == 404
    assert client.get(url, headers=tokens[1]).status_code == 404
    response = client.post(url, json=key, headers=tokens[0])
    assert response.status_code == 200, response.text
    first = response.json()
    assert not first["technical_pass"] and not first["publication_eligible"]
    assert first["duplicates"]["status"] == "pass" and first["math"]["status"] == "not_applicable"
    assert "Test-generated" in first["blockers"][0]
    assert client.post(url, json=key, headers=tokens[0]).json()["id"] == first["id"]
    assert response.headers["cache-control"] == "no-store"
    assert (
        client.post(url, json={**key, "technical_pass": True}, headers=tokens[0]).status_code == 422
    )
    assert client.post(url, content=b"x" * 17000, headers=tokens[0]).status_code == 413
    # Same owner gets a real second immutable draft. Revalidation sees the new corpus.
    second = client.post(
        "/api/v1/generator/drafts", json=payload(material_ids=[material]), headers=tokens[0]
    ).json()
    assert second["id"] != version
    second_url = f"/api/v1/validation/drafts/{second['id']}/reports"
    assert client.post(second_url, json=key, headers=tokens[0]).status_code == 409
    report = client.post(url, json={"idempotency_key": str(uuid4())}, headers=tokens[0]).json()
    assert report["duplicates"]["match_count"] == 1
    assert report["duplicates"]["matches"][0]["version_id"] == second["id"]
    assert client.get(url, headers=tokens[0]).json()["total"] == 2
    assert len(client.get(url + "?offset=1&limit=1", headers=tokens[0]).json()["items"]) == 1
    preview = {"stem": "Calculate: (3+5)/2", "options": ["4", "3", "5", "6"], "correct_option": 0}
    checked = client.post("/api/v1/validation/math-check", json=preview, headers=tokens[0])
    assert checked.status_code == 200 and checked.json()["result"]["status"] == "pass"
    assert not checked.json()["saved"] and not checked.json()["publication_eligible"]
    assert (
        client.post(
            "/api/v1/validation/math-check",
            json={**preview, "correct_option": True},
            headers=tokens[0],
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/validation/math-check",
            json={**preview, "options": ["9" * 129] * 4},
            headers=tokens[0],
        ).status_code
        == 422
    )
    assert client.post("/api/v1/validation/math-check", json=preview).status_code == 401

    def fail_audit(conn, cursor, statement, params, context, many):
        if "INSERT INTO mcq.audit_events" in statement:
            raise SQLAlchemyError("synthetic audit failure")

    event.listen(app.state.database.engine, "before_cursor_execute", fail_audit)
    retry = {"idempotency_key": str(uuid4())}
    try:
        assert client.post(url, json=retry, headers=tokens[0]).status_code == 503
    finally:
        event.remove(app.state.database.engine, "before_cursor_execute", fail_audit)
    assert client.get(url, headers=tokens[0]).json()["total"] == 2
    assert client.post(url, json=retry, headers=tokens[0]).status_code == 200
    with app.state.database.session() as session:
        assert session.execute(text("SELECT count(*) FROM mcq.question_releases")).scalar_one() == 0
        assert not session.execute(
            text(
                "SELECT has_table_privilege(current_user,'mcq.validation_reports','UPDATE,DELETE')"
            )
        ).scalar_one()
