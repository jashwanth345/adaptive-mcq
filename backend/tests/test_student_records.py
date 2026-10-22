"""Positive count/privacy fixture built through all existing SQL validity gates."""

from uuid import uuid4

import pytest
from sqlalchemy import text

from backend.tests.test_student import integration, operator, students  # noqa: F401


@pytest.mark.integration
@integration
def test_submitted_and_feedback_counts_do_not_expose_results(request):
    client, app, ids, tokens = request.getfixturevalue("students")
    keys = {
        name: uuid4()
        for name in [
            "topic",
            "material",
            "doc",
            "chunk",
            "question",
            "version",
            "verification",
            "assessment",
            "attempt",
            "generate_job",
            "generation_run",
            "review_job",
            "review",
        ]
    }
    values = {**keys, "uid": ids[1]}
    # All names, verification scores and content below are synthetic SQL fixtures.
    statements = [
        "INSERT INTO mcq.jobs(id,owner_id,kind,state,idempotency_key) VALUES(:generate_job,:uid,'generate','completed',gen_random_uuid()),(:review_job,:uid,'verify','completed',gen_random_uuid())",
        "INSERT INTO mcq.generation_runs(id,job_id,owner_id,generator_model,model_digest,prompt_version,settings) VALUES(:generation_run,:generate_job,:uid,'synthetic-test','synthetic-test','test','{\"mode\":\"ollama\"}')",
        "INSERT INTO mcq.topics(id,owner_id,name) VALUES(:topic,:uid,'Fixture topic')",
        "INSERT INTO mcq.materials(id,owner_id,title) VALUES(:material,:uid,'Fixture source')",
        "INSERT INTO mcq.documents(id,material_id,owner_id,version,storage_key,sha256,byte_size,page_count) VALUES(:doc,:material,:uid,1,'student_fixture.pdf',repeat('a',64),100,1)",
        "INSERT INTO mcq.chunks(id,document_id,owner_id,ordinal,page_start,page_end,content,content_sha256,token_count,splitter_version) VALUES(:chunk,:doc,:uid,0,1,1,'Private source',repeat('b',64),3,'fixture')",
        "INSERT INTO mcq.questions(id,owner_id) VALUES(:question,:uid)",
        "INSERT INTO mcq.question_versions(id,question_id,owner_id,version,topic_id,generation_run_id,stem,explanation,correct_option,difficulty,cognitive_level,question_type) VALUES(:version,:question,:uid,1,:topic,:generation_run,'Private stem','Private explanation',0,'easy','understand','conceptual')",
        "INSERT INTO mcq.options(version_id,ordinal,content) SELECT :version,n,'Private option '||n FROM generate_series(0,3) n",
        "INSERT INTO mcq.question_sources(version_id,chunk_id,owner_id,evidence_quote) VALUES(:version,:chunk,:uid,'Private source')",
        """INSERT INTO mcq.question_verifications(id,version_id,verifier_model,model_digest,prompt_version,policy_version,status,
        confidence_score,correctness_score,clarity_score,difficulty_score,distractor_score,grounding_score,duplicate_score,
        blind_option,schema_pass,source_pass,duplicate_pass,math_result,review_required)
        VALUES(:verification,:version,'fixture','fixture','fixture','fixture','PASS',80,80,80,80,80,80,0,0,true,true,true,'not_applicable',false)""",
        "INSERT INTO mcq.verifier_reports(id,owner_id,version_id,job_id,mode,recommendation,result) VALUES(:review,:uid,:version,:review_job,'ollama','PASS',jsonb_build_object('ai_executed',true,'blind_option',0))",
        "INSERT INTO mcq.validation_reports(owner_id,version_id,idempotency_key,policy_version,verifier_report_id,corpus_hash,schema_pass,source_pass,duplicate_status,math_status,technical_pass,result) VALUES(:uid,:version,gen_random_uuid(),'deterministic-validation-v1',:review,mcq.validation_corpus(:uid,:question),true,true,'pass','not_applicable',true,'{}')",
        "INSERT INTO mcq.question_releases(version_id,verification_id,state) VALUES(:version,:verification,'approved')",
        "INSERT INTO mcq.assessments(id,owner_id,title,kind,mode,release_policy) VALUES(:assessment,:uid,'Stored assessment','practice','adaptive','after_close')",
        "UPDATE mcq.assessments SET state='published',published_at=now() WHERE id=:assessment",
        "INSERT INTO mcq.attempts(id,assessment_id,owner_id,student_id,attempt_number,idempotency_key) VALUES(:attempt,:assessment,:uid,:uid,1,gen_random_uuid())",
        "INSERT INTO mcq.attempt_items(attempt_id,assessment_id,owner_id,position,version_id,points) VALUES(:attempt,:assessment,:uid,1,:version,1)",
        "INSERT INTO mcq.answers(attempt_id,version_id,selected_option,is_correct,awarded_points) VALUES(:attempt,:version,0,true,1)",
        "UPDATE mcq.attempts SET state='submitted',submitted_at=now() WHERE id=:attempt",
        "INSERT INTO mcq.feedback(attempt_id,version_id,student_id,category,comment) VALUES(:attempt,:version,:uid,'poor_wording','Private feedback comment')",
    ]
    with operator(app.state.database), app.state.database.session() as session, session.begin():
        for sql in statements:
            session.execute(text(sql), values)
    own = client.get("/api/v1/student/dashboard", headers=tokens[1])
    other = client.get("/api/v1/student/dashboard", headers=tokens[0])
    assert own.status_code == 200, own.text
    assert own.json()["counts"]["submitted_attempts"] == 1
    assert own.json()["counts"]["feedback"] == 1
    assert other.json()["counts"]["submitted_attempts"] == 0
    assert other.json()["counts"]["feedback"] == 0
    history = client.get("/api/v1/student/attempts", headers=tokens[1])
    assert history.status_code == 200, history.text
    assert history.json()["items"][0]["state"] == "submitted"
    for private in [
        "Private",
        "correct_option",
        "awarded_points",
        "is_correct",
        "explanation",
        "score",
    ]:
        assert private not in own.text + history.text
    assert client.get("/api/v1/student/attempts", headers=tokens[0]).json()["total"] == 0
