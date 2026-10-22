"""Snapshot-based assessment attempts. Answer keys are released by database policy."""

import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text

from .assessments import Command
from .auth.security import AuthError
from .student.routes import Student


class Choice(BaseModel):
    model_config = {"extra": "forbid"}
    position: int = Field(strict=True, ge=1, le=50)
    selected_option: int | None = Field(None, strict=True, ge=0, le=3)
    flagged: bool = Field(False, strict=True)


class Submit(Command):
    revision: int = Field(strict=True, ge=1)


class Save(Submit):
    answers: list[Choice] = Field(min_length=1, max_length=50)

    @field_validator("answers")
    @classmethod
    def unique_positions(cls, value):
        if len({a.position for a in value}) != len(value):
            raise ValueError("Each position appears once")
        return value


class Practice(Command):
    version_id: UUID


class Item(BaseModel):
    position: int
    version_id: UUID
    stem: str
    options: list[str]
    selected_option: int | None
    flagged: bool
    under_review: bool
    correct_option: int | None = None
    explanation: str | None = None
    is_correct: bool | None = None
    source_quotes: list[str] | None = None


class Score(BaseModel):
    awarded_points: float
    possible_points: float
    item_count: int


class AttemptView(BaseModel):
    id: UUID
    assessment_id: UUID
    title: str
    kind: str
    state: Literal["in_progress", "submitted", "expired"]
    revision: int
    deadline: datetime | None
    server_now: datetime
    started_at: datetime
    submitted_at: datetime | None
    release_policy: str
    results_released: bool
    items: list[Item]
    result: Score | None


def checked(result):
    if "error" not in result:
        return result
    code = result["error"]
    statuses = {
        "ATTEMPT_NOT_FOUND": 404,
        "ATTEMPT_FORBIDDEN": 403,
        "ATTEMPT_UNAVAILABLE": 409,
        "ATTEMPT_STALE": 409,
        "ATTEMPT_KEY_CONFLICT": 409,
        "ATTEMPT_FINISHED": 409,
        "PRACTICE_BLOCKED": 409,
        "ATTEMPT_INVALID": 422,
    }
    raise AuthError(
        statuses.get(code, 503),
        code if code in statuses else "DATABASE_UNAVAILABLE",
        "The attempt action could not be completed.",
    )


class AttemptService:
    def __init__(self, database):
        self.database = database

    def view(self, student, target):
        # Viewing may finalize a timed-out attempt; commit this transition explicitly.
        with self.database.session() as session, session.begin():
            result = session.execute(
                text("SELECT mcq.attempt_view(:student,:target)"),
                dict(student=student, target=target),
            ).scalar_one()
        return checked(result)

    def change(self, student, target, payload, operation):
        body = payload.model_dump(mode="json", exclude={"idempotency_key", "version_id"})
        with self.database.session() as session, session.begin():
            result = session.execute(
                text("SELECT mcq.attempt_action(:student,:target,:key,:op,CAST(:body AS jsonb))"),
                dict(
                    student=student,
                    target=target,
                    key=payload.idempotency_key,
                    op=operation,
                    body=json.dumps(body),
                ),
            ).scalar_one()
        checked(result)
        return self.view(student, UUID(result["attempt_id"]))


router = APIRouter(prefix="/api/v1/student", tags=["Assessment attempts"])


def service(request):
    return AttemptService(request.app.state.database)


@router.post(
    "/assessments/{assessment_id}/attempts",
    response_model=AttemptView,
    response_model_exclude_none=True,
)
def start(assessment_id: UUID, payload: Command, principal: Student, request: Request):
    return service(request).change(principal.user["id"], assessment_id, payload, "start")


@router.get("/attempts/{attempt_id}", response_model=AttemptView, response_model_exclude_none=True)
def view(attempt_id: UUID, principal: Student, request: Request):
    return service(request).view(principal.user["id"], attempt_id)


@router.post(
    "/attempts/{attempt_id}/save", response_model=AttemptView, response_model_exclude_none=True
)
def save(attempt_id: UUID, payload: Save, principal: Student, request: Request):
    return service(request).change(principal.user["id"], attempt_id, payload, "save")


@router.post(
    "/attempts/{attempt_id}/submit", response_model=AttemptView, response_model_exclude_none=True
)
def submit(attempt_id: UUID, payload: Submit, principal: Student, request: Request):
    return service(request).change(principal.user["id"], attempt_id, payload, "submit")


@router.post("/practice/start", response_model=AttemptView, response_model_exclude_none=True)
def practice(payload: Practice, principal: Student, request: Request):
    return service(request).change(principal.user["id"], payload.version_id, payload, "practice")
