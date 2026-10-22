"""Teacher-only smoke artifacts and consent-confirmed pseudonymous study exports."""

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from evaluation.fixtures import smoke_inputs
from evaluation.reporting import review_pack, summarize
from evaluation.runner import run
from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text

from .assessments import Command
from .auth.security import AuthError
from .teacher.routes import Teacher

router = APIRouter(prefix="/api/v1/teacher/evaluation", tags=["Evaluation harness"])


class StudyExport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assessment_ids: list[UUID] = Field(min_length=1, max_length=8)
    consent_confirmed: Literal[True]

    @field_validator("consent_confirmed", mode="before")
    @classmethod
    def explicit_consent(cls, value):
        if value is not True:
            raise ValueError("Explicit confirmation is required")
        return value

    @field_validator("assessment_ids")
    @classmethod
    def distinct(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Choose distinct assessments")
        return value


def checked(data):
    if "error" in data:
        code = data["error"]
        raise AuthError(
            {
                "EVALUATION_FORBIDDEN": 403,
                "EVALUATION_NOT_FOUND": 404,
                "EVALUATION_LIMIT": 409,
                "EVALUATION_EXPORT_LIMIT": 422,
                "EVALUATION_INVALID": 422,
            }.get(code, 503),
            code,
            "Evaluation request could not complete.",
        )
    return data


def access(request, account, op, target=None, retry=None, body=None):
    with request.app.state.database.session() as session, session.begin():
        data = session.execute(
            text("SELECT mcq.evaluation_access(:account,:op,:target,:retry,CAST(:body AS jsonb))"),
            dict(account=account, op=op, target=target, retry=retry, body=json.dumps(body or {})),
        ).scalar_one()
    return checked(data)


@router.get("/runs")
def listing(principal: Teacher, request: Request):
    return access(request, principal.user["id"], "list")


@router.post("/runs")
def smoke(payload: Command, principal: Teacher, request: Request):
    old = access(request, principal.user["id"], "retry", retry=payload.idempotency_key)
    if old["found"]:
        return old
    dataset, config = smoke_inputs()
    result = run(dataset, config)  # Constant mock configuration; no request-controlled model mode.
    return access(
        request,
        principal.user["id"],
        "save",
        retry=payload.idempotency_key,
        body={"run": result, "summary": summarize(result)},
    )


@router.get("/runs/{run_id}")
def detail(run_id: UUID, principal: Teacher, request: Request):
    return access(request, principal.user["id"], "get", target=run_id)


@router.get("/runs/{run_id}/review-pack")
def reviews(run_id: UUID, principal: Teacher, request: Request):
    data = access(request, principal.user["id"], "get", target=run_id)
    blind, mapping, template = review_pack(data["run"])
    return {"reviewer_items": blind, "operator_only_map": mapping, "ratings_template": template}


def pseudonymize(rows):
    salt = secrets.token_bytes(32)

    def alias(kind, value):
        return kind + "-" + hmac.new(salt, str(value).encode(), hashlib.sha256).hexdigest()[:24]

    return [
        {
            "sequence": index,
            "learner": alias("learner", row["student_id"]),
            "assessment": alias("assessment", row["assessment_id"]),
            "attempt": alias("attempt", row["attempt_id"]),
            "version": alias("version", row["version_id"]),
            "topic": alias("topic", row["topic_id"]),
            "difficulty": row["difficulty"],
            "is_correct": row["is_correct"],
        }
        for index, row in enumerate(rows, 1)
    ]


@router.post("/adaptive-export")
def export(payload: StudyExport, principal: Teacher, request: Request):
    with request.app.state.database.session() as session, session.begin():
        data = checked(
            session.execute(
                text("SELECT mcq.evaluation_events(:account,CAST(:targets AS uuid[]))"),
                dict(account=principal.user["id"], targets=payload.assessment_ids),
            ).scalar_one()
        )
    return {
        "format": "adaptive-export-v1",
        "consent_confirmed": True,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "events": pseudonymize(data["events"]),
        "scope": "Released submitted first-exposure evidence in selected owned classroom assessments; skips, repeats, expired and quarantined items excluded. Selected history is incomplete for learners with activity elsewhere.",
        "identity_policy": "Fresh per-export pseudonyms; no names, emails, comments, question text, raw IDs or event timestamps. These records are pseudonymous, not guaranteed anonymous. Do not publish learner exports.",
        "learning_outcomes": "To be evaluated; this is not a randomized or counterbalanced study.",
    }
