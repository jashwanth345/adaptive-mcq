import json
from hashlib import sha256

from pydantic import ValidationError
from sqlalchemy import text

from ..auth.security import AuthError
from ..generator.schemas import Candidate
from .client import PROMPT_VERSION, LocalVerifier, fail

POLICY_VERSION = "advisory-review-v1"
PENDING = [
    "Duplicate and mathematical validation",
    "Teacher review",
    "Publication approval",
    "Hardware/model quality evaluation",
]


class VerifierService:
    def __init__(self, database, settings, generator, rag):
        self.database, self.settings, self.generator, self.rag = database, settings, generator, rag
        self.client = LocalVerifier(settings)

    def status(self):
        result = {
            "mode": self.settings.verifier_mode,
            "ready": self.settings.verifier_mode == "mock",
            "model": self.settings.verifier_model,
            "configured_same_model": self.settings.verifier_model == self.settings.generator_model,
            "selection_status": "Hardware-validated model selection: pending",
            "error_code": None,
        }
        if self.settings.verifier_mode == "ollama":
            try:
                self.client.inspect()
                result["ready"] = True
            except AuthError as error:
                result["error_code"] = error.code
        return result

    def source_checks(self, owner, draft):
        try:
            Candidate(
                stem=draft["stem"],
                options=draft["options"],
                correct_option=draft["correct_option"],
                explanation=draft["explanation"],
                citation=draft["source"]["citation"],
                evidence_quote=draft["evidence_quote"],
            )
            valid_schema = True
        except ValidationError:
            valid_schema = False
        with self.database.session() as session:
            row = (
                session.execute(
                    text("""SELECT c.content,c.content_sha256,s.evidence_quote,g.settings,g.model_digest,v.question_type
                FROM mcq.question_versions v JOIN mcq.generation_runs g ON g.id=v.generation_run_id AND g.owner_id=v.owner_id
                JOIN mcq.question_sources s ON s.version_id=v.id AND s.owner_id=v.owner_id
                JOIN mcq.chunks c ON c.id=s.chunk_id AND c.owner_id=s.owner_id
                JOIN mcq.documents d ON d.id=c.document_id AND d.owner_id=c.owner_id
                JOIN mcq.materials m ON m.id=d.material_id AND m.owner_id=d.owner_id
                WHERE v.owner_id=:owner AND v.id=:version AND c.id=:chunk AND NOT m.archived
            """),
                    {"owner": owner, "version": draft["id"], "chunk": draft["source"]["chunk_id"]},
                )
                .mappings()
                .one_or_none()
            )
        source = draft["source"]
        valid_source = bool(
            row
            and row["evidence_quote"] == draft["evidence_quote"]
            and draft["evidence_quote"] in source["excerpt"]
            and source["excerpt"] in row["content"]
            and sha256(row["content"].encode()).hexdigest()
            == row["content_sha256"]
            == source["content_sha256"]
            and sha256(source["excerpt"].encode()).hexdigest() == source["excerpt_sha256"]
        )
        checks = [
            {
                "name": "Question format",
                "outcome": "pass" if valid_schema else "fail",
                "detail": "Four distinct options, bounded text and a valid proposed answer index.",
            },
            {
                "name": "Source integrity",
                "outcome": "pass" if valid_source else "fail",
                "detail": "Stored quotation/excerpt and hashes compared with the owned original chunk. This does not establish factual correctness.",
            },
        ]
        return checks, row

    @staticmethod
    def serialize(row):
        return {
            key: row[key]
            for key in (
                "id",
                "version_id",
                "mode",
                "recommendation",
                "publication_eligible",
                "created_at",
            )
        } | {
            key: row["result"][key]
            for key in (
                "checks",
                "ai_executed",
                "blind_option",
                "reason",
                "model",
                "model_relationship",
                "pending",
            )
        }

    def existing(self, session, owner, key, fingerprint):
        row = (
            session.execute(
                text("""SELECT r.*,j.parameters FROM mcq.verifier_reports r
            JOIN mcq.jobs j ON j.id=r.job_id AND j.owner_id=r.owner_id
            WHERE j.owner_id=:owner AND j.kind='verify' AND j.idempotency_key=:key"""),
                {"owner": owner, "key": key},
            )
            .mappings()
            .one_or_none()
        )
        if row and row["parameters"].get("fingerprint") != fingerprint:
            raise fail("VERIFIER_KEY_CONFLICT", 409)
        return self.serialize(row) if row else None

    def review(self, owner, version, payload):
        draft = self.generator.get(owner, version)
        mode = self.settings.verifier_mode
        if mode == "disabled":
            raise fail("VERIFIER_DISABLED")
        if mode == "ollama" and draft["mode"] == "mock":
            raise fail("VERIFIER_TEST_DRAFT", 409)
        fingerprint = sha256(
            f"{version}|{mode}|{self.settings.verifier_model}|{POLICY_VERSION}".encode()
        ).hexdigest()
        with self.database.session() as session:
            existing = self.existing(session, owner, payload.idempotency_key, fingerprint)
        if existing:
            return existing
        if not self.rag.gate.acquire(blocking=False):
            raise fail("VERIFIER_BUSY", 409)
        try:
            checks, source = self.source_checks(owner, draft)
            basic_pass = all(check["outcome"] == "pass" for check in checks)
            result = {
                "checks": checks,
                "ai_executed": False,
                "blind_option": None,
                "model": "deterministic-test-checks"
                if mode == "mock"
                else self.settings.verifier_model,
                "model_relationship": "not_evaluated",
                "pending": PENDING,
                "policy_version": POLICY_VERSION,
                "prompt_version": PROMPT_VERSION,
                "source_excerpt_sha256": draft["source"]["excerpt_sha256"],
            }
            if mode == "mock":
                recommendation = "NOT_EVALUATED"
                result["reason"] = (
                    "Test review only. No LLM ran; answer correctness, distractor quality, explanation and difficulty have not been evaluated."
                )
                checks.append(
                    {
                        "name": "AI quality review",
                        "outcome": "not_evaluated",
                        "detail": "A test report never constitutes AI verification or approval.",
                    }
                )
            elif not basic_pass:
                recommendation = "REJECT"
                result["reason"] = (
                    "Question format or stored source integrity failed. No AI inference was attempted."
                )
            else:
                if source["question_type"] != "conceptual":
                    raise fail("VERIFIER_UNSUPPORTED_TYPE", 422)
                blind, critique, evidence = self.client.review(draft)
                # Service validates again, including test adapters: never trust an
                # answer without a verbatim quotation in the exact source excerpt.
                if blind.answerable and blind.evidence_quote not in draft["source"]["excerpt"]:
                    raise fail("VERIFIER_EVIDENCE_MISMATCH", 422)
                agreement = blind.answerable and blind.selected_option == draft["correct_option"]
                checks.append(
                    {
                        "name": "Blind answer agreement",
                        "outcome": "pass" if agreement else "fail",
                        "detail": blind.reason,
                    }
                )
                checks.extend(
                    {
                        "name": name.replace("_", " ").capitalize(),
                        "outcome": value,
                        "detail": "Model judgement; not experimentally validated.",
                    }
                    for name, value in critique.model_dump(exclude={"reason"}).items()
                )
                recommendation = (
                    "REJECT"
                    if not blind.answerable or critique.factual_correctness == "issue"
                    else "PASS"
                    if agreement
                    and all(
                        value == "acceptable"
                        for value in critique.model_dump(exclude={"reason"}).values()
                    )
                    else "REGENERATE"
                )
                digest = evidence["blind"]["digest"].removeprefix("sha256:")
                relationship = (
                    "same_checkpoint"
                    if digest == source["model_digest"].removeprefix("sha256:")
                    else "different_checkpoint"
                )
                result.update(
                    ai_executed=True,
                    blind_option=blind.selected_option,
                    reason=critique.reason,
                    model=self.settings.verifier_model,
                    model_relationship=relationship,
                    evidence=evidence,
                    blind=blind.model_dump(),
                    critique=critique.model_dump(),
                )
            with self.database.session() as session, session.begin():
                session.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:owner,11))"),
                    {"owner": str(owner)},
                )
                existing = self.existing(session, owner, payload.idempotency_key, fingerprint)
                if existing:
                    return existing
                job = session.execute(
                    text("""INSERT INTO mcq.jobs(owner_id,kind,state,idempotency_key,parameters,stage,attempts)
                    VALUES(:owner,'verify','completed',:key,CAST(:params AS jsonb),'advisory_report_saved',1) RETURNING id"""),
                    {
                        "owner": owner,
                        "key": payload.idempotency_key,
                        "params": json.dumps(
                            {"fingerprint": fingerprint, "version_id": str(version)}
                        ),
                    },
                ).scalar_one()
                row = (
                    session.execute(
                        text("""INSERT INTO mcq.verifier_reports(owner_id,version_id,job_id,mode,recommendation,result)
                    VALUES(:owner,:version,:job,:mode,:recommendation,CAST(:result AS jsonb)) RETURNING *"""),
                        {
                            "owner": owner,
                            "version": version,
                            "job": job,
                            "mode": mode,
                            "recommendation": recommendation,
                            "result": json.dumps(result, default=str),
                        },
                    )
                    .mappings()
                    .one()
                )
                session.execute(
                    text(
                        "INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id) VALUES(:owner,'verification.report_created','verifier_report',:id)"
                    ),
                    {"owner": owner, "id": row["id"]},
                )
                saved = self.serialize(row)
            return saved
        finally:
            self.rag.gate.release()

    def history(self, owner, version, offset, limit):
        self.generator.get(owner, version)
        with self.database.session() as session:
            params = {"owner": owner, "version": version, "offset": offset, "limit": limit}
            total = session.execute(
                text(
                    "SELECT count(*) FROM mcq.verifier_reports WHERE owner_id=:owner AND version_id=:version"
                ),
                params,
            ).scalar_one()
            rows = (
                session.execute(
                    text(
                        "SELECT * FROM mcq.verifier_reports WHERE owner_id=:owner AND version_id=:version ORDER BY created_at DESC,id DESC LIMIT :limit OFFSET :offset"
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
