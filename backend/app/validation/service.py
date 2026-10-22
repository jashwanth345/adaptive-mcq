import json

from sqlalchemy import text

from ..auth.security import AuthError
from .duplicates import CORPUS_LIMIT, compare
from .math_check import check_math

POLICY = "deterministic-validation-v1"


def fail(code, status=409):
    return AuthError(status, code, "Draft validation could not complete.")


class ValidationService:
    def __init__(self, database, generator, verifier, rag):
        self.database, self.generator, self.verifier, self.rag = database, generator, verifier, rag

    @staticmethod
    def serialize(row):
        return {
            key: row[key]
            for key in (
                "id",
                "version_id",
                "created_at",
                "policy_version",
                "technical_pass",
                "publication_eligible",
            )
        } | {key: row["result"][key] for key in ("checks", "math", "duplicates", "blockers")}

    def existing(self, session, owner, version, key):
        row = (
            session.execute(
                text(
                    "SELECT * FROM mcq.validation_reports WHERE owner_id=:owner AND idempotency_key=:key"
                ),
                {"owner": owner, "key": key},
            )
            .mappings()
            .one_or_none()
        )
        if row and (row["version_id"] != version or row["policy_version"] != POLICY):
            raise fail("VALIDATION_KEY_CONFLICT")
        return self.serialize(row) if row else None

    def validate(self, owner, version, payload):
        draft = self.generator.get(owner, version, include_released=True)
        with self.database.session() as session:
            existing = self.existing(session, owner, version, payload.idempotency_key)
        if existing:
            return existing
        if not self.rag.gate.acquire(blocking=False):
            raise fail("VALIDATION_BUSY")
        try:
            checks, source = self.verifier.source_checks(owner, draft)
            with self.database.session() as session, session.begin():
                # Same owner lock as generation, plus the shared single-process gate.
                session.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:owner,10))"),
                    {"owner": str(owner)},
                )
                existing = self.existing(session, owner, version, payload.idempotency_key)
                if existing:
                    return existing
                q = (
                    session.execute(
                        text(
                            "SELECT v.question_id,v.question_type,NOT q.archived AND NOT EXISTS(SELECT 1 FROM mcq.question_versions newer WHERE newer.question_id=v.question_id AND newer.version>v.version) AS current_version FROM mcq.question_versions v JOIN mcq.questions q ON q.id=v.question_id WHERE v.id=:version AND v.owner_id=:owner"
                        ),
                        {"owner": owner, "version": version},
                    )
                    .mappings()
                    .one()
                )
                params = {"owner": owner, "question": q["question_id"], "version": version}
                rows = (
                    session.execute(
                        text("""SELECT * FROM (
                    SELECT DISTINCT ON (v.question_id) v.id,v.stem,v.question_id
                    FROM mcq.question_versions v JOIN mcq.questions q ON q.id=v.question_id AND q.owner_id=v.owner_id
                    WHERE v.owner_id=:owner AND v.question_id<>:question AND NOT q.archived
                    ORDER BY v.question_id,v.version DESC
                ) corpus ORDER BY id LIMIT :limit"""),
                        {**params, "limit": CORPUS_LIMIT + 1},
                    )
                    .mappings()
                    .all()
                )
                corpus_hash = session.execute(
                    text("SELECT mcq.validation_corpus(:owner,:question)"), params
                ).scalar_one()
                review = (
                    session.execute(
                        text(
                            "SELECT * FROM mcq.verifier_reports WHERE owner_id=:owner AND version_id=:version ORDER BY created_at DESC,id DESC LIMIT 1"
                        ),
                        params,
                    )
                    .mappings()
                    .one_or_none()
                )
                duplicate = compare(draft["stem"], rows)
                math = check_math(
                    draft["stem"], draft["options"], draft["correct_option"], q["question_type"]
                )
                real = draft["mode"] == "ollama"
                ai_pass = bool(
                    review
                    and review["mode"] == "ollama"
                    and review["recommendation"] == "PASS"
                    and review["result"].get("ai_executed") is True
                    and review["result"].get("blind_option") == draft["correct_option"]
                )
                blockers = []
                if not q["current_version"]:
                    blockers.append("This question is archived or has a newer version.")
                if not real:
                    blockers.append("Test-generated content cannot be released.")
                if not ai_pass:
                    blockers.append(
                        "A current real-AI verifier PASS with matching blind answer is required."
                    )
                if checks[0]["outcome"] != "pass":
                    blockers.append("Question format failed.")
                if checks[1]["outcome"] != "pass":
                    blockers.append("Source integrity failed.")
                if duplicate["status"] != "pass":
                    blockers.append(
                        "Duplicate candidates found."
                        if duplicate["match_count"]
                        else "Duplicate scan is incomplete; the comparison limit was reached."
                    )
                if math["status"] not in ("pass", "not_applicable"):
                    blockers.append("Mathematical validation failed or is unsupported.")
                technical_pass = not blockers
                result = {
                    "checks": checks,
                    "math": math,
                    "duplicates": duplicate,
                    "blockers": blockers,
                    "question_type": q["question_type"],
                    "generation_mode": draft["mode"],
                }
                saved = (
                    session.execute(
                        text("""INSERT INTO mcq.validation_reports(owner_id,version_id,idempotency_key,policy_version,verifier_report_id,corpus_hash,schema_pass,source_pass,duplicate_status,math_status,technical_pass,result)
                    VALUES(:owner,:version,:key,:policy,:review,:corpus,:schema,:source,:duplicate,:math,:passed,CAST(:result AS jsonb)) RETURNING *"""),
                        {
                            "owner": owner,
                            "version": version,
                            "key": payload.idempotency_key,
                            "policy": POLICY,
                            "review": review["id"] if review else None,
                            "corpus": corpus_hash,
                            "schema": checks[0]["outcome"] == "pass",
                            "source": checks[1]["outcome"] == "pass",
                            "duplicate": duplicate["status"],
                            "math": math["status"],
                            "passed": technical_pass,
                            "result": json.dumps(result),
                        },
                    )
                    .mappings()
                    .one()
                )
                session.execute(
                    text(
                        "INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id) VALUES(:owner,'validation.report_created','validation_report',:id)"
                    ),
                    {"owner": owner, "id": saved["id"]},
                )
                return self.serialize(saved)
        finally:
            self.rag.gate.release()

    def history(self, owner, version, offset, limit):
        self.generator.get(owner, version, include_released=True)
        with self.database.session() as session:
            params = {"owner": owner, "version": version, "offset": offset, "limit": limit}
            total = session.execute(
                text(
                    "SELECT count(*) FROM mcq.validation_reports WHERE owner_id=:owner AND version_id=:version"
                ),
                params,
            ).scalar_one()
            rows = (
                session.execute(
                    text(
                        "SELECT * FROM mcq.validation_reports WHERE owner_id=:owner AND version_id=:version ORDER BY created_at DESC,id DESC LIMIT :limit OFFSET :offset"
                    ),
                    params,
                )
                .mappings()
                .all()
            )
            return {
                "items": [self.serialize(row) for row in rows],
                "total": total,
                "offset": offset,
                "limit": limit,
            }
