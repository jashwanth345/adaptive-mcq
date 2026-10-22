"""Version-linked reports, owner triage and auditable quarantine."""

import json
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import Field, StringConstraints, model_validator
from sqlalchemy import text

from .assessments import Command
from .auth.routes import current_user
from .auth.security import AuthError
from .auth.service import Principal
from .student.routes import Student
from .teacher.review import Note

Category = Literal[
    "wrong_answer",
    "wrong_explanation",
    "ambiguous",
    "poor_wording",
    "weak_distractor",
    "too_easy",
    "too_difficult",
    "duplicate",
    "not_from_material",
    "mathematical_error",
    "other",
    "rating",
]


class Report(Command):
    version_id: UUID
    category: Category
    rating: Literal["helpful", "poor"] | None = None
    comment: Annotated[
        str, StringConstraints(strip_whitespace=True, max_length=2000, pattern=r"^[^\x00]*$")
    ] = ""

    @model_validator(mode="after")
    def matching_rating(self):
        if (self.category == "rating") != (self.rating is not None):
            raise ValueError("Use a helpful/poor value only for a rating")
        return self


class Decision(Command):
    revision: Annotated[int, Field(strict=True, ge=1)]
    action: Literal["review", "dismiss", "confirm_defect", "acknowledge_grades"]
    note: Note


def checked(data):
    if "error" in data:
        code = data["error"]
        statuses = {
            "FEEDBACK_NOT_FOUND": 404,
            "FEEDBACK_FORBIDDEN": 403,
            "FEEDBACK_STALE": 409,
            "FEEDBACK_KEY_CONFLICT": 409,
            "FEEDBACK_CONFIRMED": 409,
            "FEEDBACK_INVALID": 422,
        }
        raise AuthError(statuses.get(code, 503), code, "Feedback action unavailable.")
    return data


def execute(request, statement, **params):
    with request.app.state.database.session() as session, session.begin():
        data = session.execute(text(statement), params).scalar_one()
    return checked(data)


def prioritize(row, settings):
    row = dict(row)
    ratio = row["open_reporters"] / row["exposures"] if row["exposures"] else 0
    row["report_ratio"] = round(ratio, 4)
    row["priority"] = (
        "score_review"
        if row["grade_review"] == "pending"
        else "elevated"
        if row["open_reporters"] >= settings.feedback_min_reporters
        and ratio >= settings.feedback_report_ratio
        else "standard"
    )
    return row


def policy(request):
    settings = request.app.state.auth.settings
    return {
        "minimum_reporters": settings.feedback_min_reporters,
        "report_ratio": settings.feedback_report_ratio,
        "status": "Review priority only — thresholds to be evaluated",
    }


def change(request, account, target, payload, op):
    return execute(
        request,
        "SELECT mcq.feedback_action(:account,:target,:key,:op,CAST(:body AS jsonb))",
        account=account,
        target=target,
        key=payload.idempotency_key,
        op=op,
        body=json.dumps(payload.model_dump(mode="json", exclude={"idempotency_key", "action"})),
    )


Owner = Annotated[Principal, Depends(current_user)]
router = APIRouter(prefix="/api/v1", tags=["Student feedback"])


@router.post("/student/attempts/{attempt_id}/feedback")
def report(attempt_id: UUID, payload: Report, principal: Student, request: Request):
    return change(request, principal.user["id"], attempt_id, payload, "report")


@router.get("/student/feedback")
def history(
    principal: Student,
    request: Request,
    offset: int = Query(0, ge=0, le=100000),
    limit: int = Query(20, ge=1, le=50),
):
    return execute(
        request,
        "SELECT mcq.feedback_history(:account,:offset,:limit)",
        account=principal.user["id"],
        offset=offset,
        limit=limit,
    )


@router.get("/feedback/reviews")
def queue(
    principal: Owner,
    request: Request,
    offset: int = Query(0, ge=0, le=100000),
    limit: int = Query(20, ge=1, le=50),
):
    data = execute(
        request,
        "SELECT mcq.feedback_queue(:account,:offset,:limit)",
        account=principal.user["id"],
        offset=offset,
        limit=limit,
    )
    data["items"] = [prioritize(row, request.app.state.auth.settings) for row in data["items"]]
    data["policy"] = policy(request)
    return data


@router.get("/feedback/reviews/{version_id}")
def detail(
    version_id: UUID,
    principal: Owner,
    request: Request,
    offset: int = Query(0, ge=0, le=100000),
    limit: int = Query(20, ge=1, le=50),
):
    data = execute(
        request,
        "SELECT mcq.feedback_detail(:account,:target,:offset,:limit)",
        account=principal.user["id"],
        target=version_id,
        offset=offset,
        limit=limit,
    )
    data["summary"] = prioritize(data["summary"], request.app.state.auth.settings)
    return data


@router.post("/feedback/reviews/{version_id}/decisions")
def decide(version_id: UUID, payload: Decision, principal: Owner, request: Request):
    return change(request, principal.user["id"], version_id, payload, payload.action)
