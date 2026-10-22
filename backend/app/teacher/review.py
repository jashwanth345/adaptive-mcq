"""Owned teacher editing and evidence-backed approval; no assessment publication."""

import json
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from sqlalchemy import text

from ..auth.security import AuthError
from ..generator.schemas import Candidate, Draft, ShortText
from .routes import Teacher

Note = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=600, pattern=r"^[^\x00]+$"),
]


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: UUID
    action: Literal["approve", "reject"]
    note: Note


class Edit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: UUID
    note: Note
    stem: str = Field(min_length=10, max_length=350)
    explanation: str = Field(min_length=10, max_length=600)
    options: list[ShortText] = Field(min_length=4, max_length=4)
    correct_option: int = Field(strict=True, ge=0, le=3)
    difficulty: Literal["easy", "medium", "hard"]
    cognitive_level: Literal["remember", "understand"]

    @field_validator("stem", "explanation")
    @classmethod
    def bounded_text(cls, value):
        value = Candidate.nonblank(value).strip()
        if len(value) < 10:
            raise ValueError("At least ten non-padding characters are required")
        return value

    @field_validator("options")
    @classmethod
    def distinct_options(cls, value):
        if any("\x00" in item for item in value):
            raise ValueError("Null characters are not allowed")
        return Candidate.distinct(value)


class ReviewSummary(BaseModel):
    id: UUID
    version: int
    topic: str
    stem: str
    mode: str
    state: Literal["pending", "approved", "quarantined", "rejected"]
    created_at: datetime


class ReviewPage(BaseModel):
    items: list[ReviewSummary]
    total: int
    offset: int
    limit: int


class Detail(BaseModel):
    draft: Draft
    version: int
    current: bool
    state: str
    can_approve: bool
    blocker: str | None


class VersionItem(BaseModel):
    id: UUID
    version: int
    created_at: datetime
    events: list[dict]


class Versions(BaseModel):
    items: list[VersionItem]
    total: int
    offset: int
    limit: int


STATE = """CASE WHEN EXISTS(SELECT 1 FROM mcq.teacher_review_events e WHERE e.version_id=v.id AND e.action='reject')
    THEN 'rejected' ELSE COALESCE(r.state,'pending') END AS state"""


class TeacherReviewService:
    def __init__(self, database, generator):
        self.database, self.generator = database, generator

    @staticmethod
    def owned(session, owner, version):
        row = (
            session.execute(
                text(
                    """SELECT v.*, mcq.feedback_confirmed(:owner,v.id) AS feedback_defect,
            NOT EXISTS(SELECT 1 FROM mcq.question_versions n
            WHERE n.question_id=v.question_id AND n.version>v.version) AND NOT q.archived AS current,
            """
                    + STATE
                    + """ FROM mcq.question_versions v JOIN mcq.questions q ON q.id=v.question_id
            LEFT JOIN mcq.question_releases r ON r.version_id=v.id
            WHERE v.id=:version AND v.owner_id=:owner AND v.generation_run_id IS NOT NULL"""
                ),
                {"version": version, "owner": owner},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise AuthError(404, "TEACHER_REVIEW_NOT_FOUND", "This question is unavailable.")
        return row

    def listing(self, owner, offset, limit):
        clause = """FROM mcq.question_versions v JOIN mcq.questions q ON q.id=v.question_id
            JOIN mcq.generation_runs g ON g.id=v.generation_run_id JOIN mcq.topics t ON t.id=v.topic_id
            LEFT JOIN mcq.question_releases r ON r.version_id=v.id
            WHERE v.owner_id=:owner AND NOT q.archived AND NOT EXISTS(
                SELECT 1 FROM mcq.question_versions n WHERE n.question_id=v.question_id AND n.version>v.version)"""
        with self.database.session() as session:
            params = {"owner": owner, "offset": offset, "limit": limit}
            total = session.execute(text("SELECT count(*) " + clause), params).scalar_one()
            rows = (
                session.execute(
                    text(
                        "SELECT v.id,v.version,v.stem,v.created_at,t.name AS topic,g.settings->>'mode' AS mode,"
                        + STATE
                        + " "
                        + clause
                        + " ORDER BY v.created_at DESC,v.id DESC LIMIT :limit OFFSET :offset"
                    ),
                    params,
                )
                .mappings()
                .all()
            )
        return dict(items=[dict(row) for row in rows], total=total, offset=offset, limit=limit)

    def detail(self, owner, version):
        with self.database.session() as session:
            row = self.owned(session, owner, version)
            ready = session.execute(
                text("SELECT mcq.teacher_approval_ready(:owner,:version)"),
                {"owner": owner, "version": version},
            ).scalar_one()
        draft = self.generator.get(owner, version, include_released=True)
        blocker = None
        if not row["current"]:
            blocker = "This version is superseded or archived. Open the latest version."
        elif row["feedback_defect"]:
            blocker = "A confirmed feedback defect requires a corrected new version. This version cannot be reapproved."
        elif row["state"] == "rejected":
            blocker = "Rejected. Save a corrected version before requesting new checks."
        elif draft["mode"] == "mock":
            blocker = "Test-generated content cannot be approved, including after editing."
        elif not ready:
            blocker = "Fresh passing AI review and deterministic validation are required. Recheck the latest version and its source."
        return dict(
            draft=draft,
            version=row["version"],
            current=row["current"],
            state=row["state"],
            can_approve=bool(ready),
            blocker=blocker,
        )

    def versions(self, owner, version, offset, limit):
        with self.database.session() as session:
            row = self.owned(session, owner, version)
            params = {
                "owner": owner,
                "question": row["question_id"],
                "offset": offset,
                "limit": limit,
            }
            total = session.execute(
                text(
                    "SELECT count(*) FROM mcq.question_versions WHERE owner_id=:owner AND question_id=:question"
                ),
                params,
            ).scalar_one()
            rows = (
                session.execute(
                    text("""SELECT v.id,v.version,v.created_at,COALESCE((SELECT jsonb_agg(jsonb_build_object(
                'action',e.action,'note',e.request->>'note','created_at',e.created_at,'validation_report_id',e.validation_report_id) ORDER BY e.created_at DESC,e.id DESC)
                FROM mcq.teacher_review_events e WHERE e.version_id=v.id),'[]'::jsonb) AS events
                FROM mcq.question_versions v WHERE owner_id=:owner AND question_id=:question
                ORDER BY v.version DESC LIMIT :limit OFFSET :offset"""),
                    params,
                )
                .mappings()
                .all()
            )
        return dict(items=[dict(item) for item in rows], total=total, offset=offset, limit=limit)

    def change(self, owner, version, payload, action):
        body = payload.model_dump(mode="json", exclude={"idempotency_key", "action"})
        with self.database.session() as session, session.begin():
            self.owned(session, owner, version)
            result = session.execute(
                text(
                    "SELECT mcq.teacher_review_action(:owner,:version,:key,:action,CAST(:body AS jsonb))"
                ),
                {
                    "owner": owner,
                    "version": version,
                    "key": payload.idempotency_key,
                    "action": action,
                    "body": json.dumps(body),
                },
            ).scalar_one()
        if "error" in result:
            code = result["error"]
            allowed = {
                "TEACHER_REVIEW_NOT_FOUND": 404,
                "TEACHER_REVIEW_FORBIDDEN": 403,
                "TEACHER_REVIEW_STALE": 409,
                "TEACHER_REVIEW_KEY_CONFLICT": 409,
                "TEACHER_REVIEW_REJECTED": 409,
                "TEACHER_APPROVAL_BLOCKED": 409,
                "TEACHER_REVIEW_INVALID": 422,
            }
            if code in allowed:
                raise AuthError(
                    allowed[code], code, "The teacher review action could not be completed."
                ) from None
            raise AuthError(503, "DATABASE_UNAVAILABLE", "The review could not be saved.")
        return self.detail(owner, UUID(result["version_id"]))


router = APIRouter(prefix="/api/v1/teacher/reviews", tags=["Teacher review"])


def service(request):
    return TeacherReviewService(request.app.state.database, request.app.state.generator)


@router.get("", response_model=ReviewPage)
def queue(
    principal: Teacher,
    request: Request,
    offset: int = Query(0, ge=0, le=100000),
    limit: int = Query(6, ge=1, le=24),
):
    return service(request).listing(principal.user["id"], offset, limit)


@router.get("/{version_id}", response_model=Detail)
def detail(version_id: UUID, principal: Teacher, request: Request):
    return service(request).detail(principal.user["id"], version_id)


@router.get("/{version_id}/versions", response_model=Versions)
def versions(
    version_id: UUID,
    principal: Teacher,
    request: Request,
    offset: int = Query(0, ge=0, le=100000),
    limit: int = Query(5, ge=1, le=10),
):
    return service(request).versions(principal.user["id"], version_id, offset, limit)


@router.post("/{version_id}/edits", response_model=Detail)
def edit(version_id: UUID, payload: Edit, principal: Teacher, request: Request):
    return service(request).change(principal.user["id"], version_id, payload, "edit")


@router.post("/{version_id}/decisions", response_model=Detail)
def decision(version_id: UUID, payload: Decision, principal: Teacher, request: Request):
    return service(request).change(principal.user["id"], version_id, payload, payload.action)
