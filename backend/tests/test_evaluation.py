"""Synthetic harness tests only. No local inference or research measurements."""

import copy
from uuid import uuid4

import pytest
from evaluation.contracts import Config, Dataset, digest
from evaluation.fixtures import smoke_inputs
from evaluation.replay import replay
from evaluation.reporting import labels_for, metric, review_pack, summarize
from evaluation.runner import MockAdapter, prompts, run
from evaluation.storage import read_json, safe_cell, write_json
from pydantic import ValidationError
from sqlalchemy import text

from backend.app.evaluation import StudyExport
from backend.app.generator.client import OllamaGenerator
from backend.tests.test_assessments import command, student_account
from backend.tests.test_attempts import prepared, save, submit
from backend.tests.test_teacher import integration, owner, teachers  # noqa: F401

ROOT = "/api/v1/teacher/evaluation"


@pytest.fixture
def experiment(monkeypatch):
    monkeypatch.setattr("evaluation.runner.snapshot", lambda: {"synthetic_test": True})
    return run(*smoke_inputs())


def test_matched_candidates_math_rejection_and_no_fake_quality(experiment):
    assert len(experiment["records"]) == 16
    rows = experiment["records"]
    for b, c, d in zip(rows[1::4], rows[2::4], rows[3::4], strict=True):
        assert b["question"] == c["question"] == d["question"]
        assert b["candidate_id"] == c["candidate_id"] == d["candidate_id"]
        assert not b["publication_eligible"]
    summary = summarize(experiment)
    assert [r["retained_candidates"] for r in summary["groups"]] == [4, 4, 4, 3]
    assert not summary["research_results_available"]
    assert all(
        r["quality"]["raw"]["factual_correctness"]["value"] is None for r in summary["groups"]
    )
    assert all(not r["generation"]["ai_executed"] for r in rows)


def test_source_integrity_and_split_leakage_are_rejected():
    data, _ = smoke_inputs()
    raw = data.model_dump()
    raw["documents"][0]["text"] += " tampered"
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw)
    raw = data.model_dump()
    raw["documents"].append({**raw["documents"][0], "id": "overlap", "split": "test"})
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw)
    raw = data.model_dump()
    raw["cases"][0]["contexts"][0]["text"] = "not present in document"
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw)


def test_prompts_hide_reference_from_baseline_and_key_from_blind_solver():
    data, _ = smoke_inputs()
    case = data.cases[0]
    question = dict(
        stem="Fixture question?",
        options=["a", "b", "c", "d"],
        correct_option=2,
        explanation="SECRET EXPLANATION",
    )
    assert case.contexts[0].text not in prompts("A", case)
    assert case.contexts[0].text in prompts("B", case)
    assert "proposed_key" not in prompts("blind", case, question)
    assert "SECRET EXPLANATION" not in prompts("blind", case, question)
    assert "SECRET EXPLANATION" in prompts("critique", case, question)


def test_local_inference_requires_explicit_opt_in_and_models_remain_bounded(settings):
    data, config = smoke_inputs()
    with pytest.raises(ValueError, match="opt-in"):
        run(data, config.model_copy(update={"mode": "local"}))
    with pytest.raises(Exception) as caught:
        OllamaGenerator(settings).generate("never executed", 1, seed=True)
    assert getattr(caught.value, "code", None) == "GENERATOR_INVALID_OUTPUT"
    with pytest.raises(ValidationError):
        Config.model_validate({**config.model_dump(), "seeds": [42, 42]})


def test_test_split_requires_frozen_protocol_and_development_source_ledger(experiment):
    data, config = smoke_inputs()
    test = config.model_copy(update={"split": "test"})
    with pytest.raises(ValueError, match="protocol hash"):
        run(data, test)
    raw = data.model_dump()
    raw["documents"][0]["split"] = "test"
    data = Dataset.model_validate(raw)
    test = test.model_copy(
        update={
            "frozen_protocol_sha256": experiment["protocol_sha256"],
            "development_source_hashes": experiment["development_source_hashes"],
        }
    )
    with pytest.raises(ValueError, match="disjoint"):
        run(data, test)


def test_failed_slots_and_blocked_downstream_do_not_disappear():
    class Empty(MockAdapter):
        def generate(self, *args):
            return None, {"ai_executed": False}

    result = run(*smoke_inputs(), adapter=Empty())
    summary = summarize(result)
    assert all(
        r["requested_slots"] == 4 and r["generated_candidates"] == 0 for r in summary["groups"]
    )
    assert all(
        r["retention_yield"] is None and r["end_to_end_yield"] == 0 for r in summary["groups"]
    )
    assert all(r["verifier_decision"] == "NOT_RUN" for r in result["records"])


def test_blind_pack_deduplicates_reused_candidates_and_omits_allocation(experiment):
    pack, mapping, template = review_pack(experiment)
    assert len(pack["items"]) == 8
    assert len(mapping["blind_to_candidate"]) == 8
    assert (
        not {"condition", "pair_id", "candidate_id", "verifier_decision"} & pack["items"][0].keys()
    )
    assert all(r["valid"] is None for r in template["ratings"])
    assert all(row["reference_text"] for row in pack["items"])
    with pytest.raises(ValueError, match="unchanged"):
        labels_for(experiment, mapping, {**template, "run_sha256": "wrong"})


def test_independent_disagreement_missingness_adjudication_and_kappa(experiment):
    _, mapping, template = review_pack(experiment)
    one = template["ratings"][0]
    annotations = {
        "run_sha256": digest(experiment),
        "ratings": [
            {**one, "reviewer": "r1", "valid": True, "factual_correctness": True},
            {**one, "reviewer": "r2", "valid": False, "factual_correctness": True},
        ],
    }
    labels, meta = labels_for(experiment, mapping, annotations)
    assert list(labels.values())[0]["valid"] is None
    assert list(labels.values())[0]["factual_correctness"] is True
    assert meta["agreement"][0]["agreement"] == 0
    annotations["ratings"].append(
        {**one, "reviewer": "adjudicator", "stage": "adjudication", "valid": False}
    )
    assert list(labels_for(experiment, mapping, annotations)[0].values())[0]["valid"] is False
    assert not summarize(experiment, mapping, annotations)["research_results_available"]
    annotations["ratings"].append(annotations["ratings"][0])
    with pytest.raises(ValueError, match="duplicate"):
        labels_for(experiment, mapping, annotations)


def test_quality_false_acceptance_and_raw_retained_denominators(experiment):
    # Deliberately relabel ONLY this in-memory synthetic unit fixture to exercise metric arithmetic.
    result = copy.deepcopy(experiment)
    result["mode"] = "local"
    result["dataset"]["synthetic"] = False
    _, mapping, template = review_pack(result)
    annotations = {"run_sha256": digest(result), "ratings": []}
    for row in template["ratings"]:
        annotations["ratings"].extend(
            {**row, "reviewer": reviewer, "valid": False, "factual_correctness": False}
            for reviewer in ("r1", "r2")
        )
    summary = summarize(result, mapping, annotations)
    c = next(g for g in summary["groups"] if g["condition"] == "C")
    assert c["verifier_false_acceptance"]["value"] == 1
    assert c["verifier_false_acceptance"]["rated_items"] == 4
    assert c["verifier_false_rejection"]["value"] is None
    d = next(g for g in summary["groups"] if g["condition"] == "D")
    assert d["quality"]["raw"]["valid"]["rated_items"] == 4
    assert d["quality"]["retained"]["valid"]["rated_items"] == 3
    assert d["quality"]["raw"]["answerability"]["unrated_or_unresolved"] == 4


def test_cluster_uncertainty_empty_single_cluster_and_repeatability():
    assert metric([])["value"] is None
    assert metric([("one", 1), ("one", 0)])["ci95"] is None
    values = [("one", 1), ("two", 0), ("two", 0)]
    assert metric(values) == metric(values)
    assert metric(values)["source_documents"] == 2
    assert metric(values)["ci95"] == [0, 1]


def test_local_files_never_overwrite_or_accept_nonfinite_json(tmp_path):
    target = tmp_path / "artifact.json"
    write_json(target, {"fixture": True})
    with pytest.raises(FileExistsError):
        write_json(target, {})
    assert read_json(target) == {"fixture": True}
    target.write_text('{"value":NaN}')
    with pytest.raises(ValueError):
        read_json(target)
    assert safe_cell(" =HYPERLINK()") == "' =HYPERLINK()"


def test_replay_is_prior_answer_only_and_never_claims_learning_gain():
    data = {
        "format": "adaptive-export-v1",
        "consent_confirmed": True,
        "events": [
            {
                "sequence": i,
                "learner": "p1",
                "topic": "t1",
                "version": f"v{i}",
                "difficulty": "easy",
                "is_correct": True,
            }
            for i in range(1, 9)
        ],
    }
    result = replay(data)
    assert result["decisions"][0]["adaptive_difficulty"] == "easy"
    assert result["decisions"][-1]["adaptive_difficulty"] == "medium"
    assert result["learning_gain"] is None
    data["events"].append({**data["events"][0], "sequence": 9})
    with pytest.raises(ValueError, match="Duplicate"):
        replay(data)


@pytest.mark.parametrize("sequence", [True, 0, -1, "1"])
def test_replay_rejects_ambiguous_ordering(sequence):
    data = {
        "format": "adaptive-export-v1",
        "consent_confirmed": True,
        "events": [
            {
                "sequence": sequence,
                "learner": "l",
                "topic": "t",
                "version": "v",
                "difficulty": "easy",
                "is_correct": True,
            }
        ],
    }
    with pytest.raises(ValueError, match="sequence"):
        replay(data)
    data["events"][0]["sequence"] = 1
    data["events"].append({**data["events"][0], "version": "v2"})
    with pytest.raises(ValueError, match="sequence"):
        replay(data)


@pytest.mark.parametrize("consent", [False, 1, "true", None])
def test_export_requires_explicit_boolean_consent(consent):
    with pytest.raises(ValidationError):
        StudyExport(assessment_ids=[uuid4()], consent_confirmed=consent)


@integration
def test_teacher_smoke_isolation_retry_export_and_no_question_writes(request):
    client, app, ids, tokens = request.getfixturevalue("teachers")
    student, _ = student_account(client)
    assert client.get(ROOT + "/runs", headers=student).status_code == 403
    assert (
        client.post(
            ROOT + "/runs", headers=tokens[0], json={**command(), "mode": "local"}
        ).status_code
        == 422
    )
    with owner(app.state.database), app.state.database.session() as session:
        before = session.execute(text("SELECT count(*) FROM mcq.questions")).scalar_one()
    body = command()
    response = client.post(ROOT + "/runs", headers=tokens[0], json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["run"]["mode"] == "mock" and not result["summary"]["research_results_available"]
    assert client.post(ROOT + "/runs", headers=tokens[0], json=body).json() == result
    assert client.get(ROOT + "/runs", headers=tokens[1]).json()["items"] == []
    assert client.get(ROOT + f"/runs/{result['id']}", headers=tokens[1]).status_code == 404
    pack = client.get(ROOT + f"/runs/{result['id']}/review-pack", headers=tokens[0])
    assert pack.status_code == 200 and len(pack.json()["reviewer_items"]["items"]) == 8
    with owner(app.state.database), app.state.database.session() as session:
        assert session.execute(text("SELECT count(*) FROM mcq.questions")).scalar_one() == before


@integration
def test_adaptive_export_scope_privacy_release_and_repeatability(request, tmp_path, monkeypatch):
    client, app, tokens, student, sid, version, target, attempt = prepared(
        request, tmp_path, monkeypatch
    )
    submit(client, student, save(client, student, attempt).json())
    body = dict(assessment_ids=[target], consent_confirmed=True)
    response = client.post(ROOT + "/adaptive-export", headers=tokens[0], json=body)
    assert response.status_code == 200, response.text
    exported = response.json()
    assert len(exported["events"]) == 1 and replay(exported)["eligible_events"] == 1
    for private in (sid, version, attempt["id"], target, "@example.com", "submitted_at"):
        assert private not in response.text
    second = client.post(ROOT + "/adaptive-export", headers=tokens[0], json=body).json()
    assert second["events"][0]["learner"] != exported["events"][0]["learner"]
    assert client.post(ROOT + "/adaptive-export", headers=tokens[1], json=body).status_code == 404
    assert (
        client.post(
            ROOT + "/adaptive-export",
            headers=tokens[0],
            json={**body, "assessment_ids": [target, str(uuid4())]},
        ).status_code
        == 404
    )
    assert client.post(ROOT + "/adaptive-export", headers=student, json=body).status_code == 403
    with owner(app.state.database), app.state.database.session() as session:
        session.execute(
            text(
                "UPDATE mcq.question_releases SET state='quarantined',reason='Synthetic test' WHERE version_id=:v"
            ),
            {"v": version},
        )
        session.commit()
    assert (
        client.post(ROOT + "/adaptive-export", headers=tokens[0], json=body).json()["events"] == []
    )


@integration
def test_adaptive_export_excludes_withheld_results(request, tmp_path, monkeypatch):
    client, app, tokens, student, sid, version, target, attempt = prepared(
        request, tmp_path, monkeypatch, release="after_close"
    )
    submit(client, student, save(client, student, attempt).json())
    response = client.post(
        ROOT + "/adaptive-export",
        headers=tokens[0],
        json=dict(assessment_ids=[target], consent_confirmed=True),
    )
    assert response.status_code == 200 and response.json()["events"] == []
