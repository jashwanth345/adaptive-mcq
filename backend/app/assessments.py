"""Local, teacher-owned classroom publication and authorized code admission."""

import hashlib
import hmac
import json
import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import text

from .auth.security import AuthError
from .student.routes import Student
from .teacher.routes import Teacher


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    idempotency_key: UUID


class DraftInput(Command):
    title: str = Field(min_length=1, max_length=200)
    version_ids: list[UUID] = Field(min_length=1, max_length=50)
    time_limit_seconds: int | None = Field(None, strict=True, ge=60, le=14400)
    max_attempts: int = Field(1, strict=True, ge=1, le=100)
    randomize_questions: bool = Field(False, strict=True)
    randomize_options: bool = Field(False, strict=True)
    release_policy: Literal["after_submit", "after_close"] = "after_submit"

    @field_validator("title")
    @classmethod
    def title_text(cls, value):
        value = value.strip()
        if not value or any(ord(c) < 32 for c in value):
            raise ValueError("A readable title is required")
        return value

    @field_validator("version_ids")
    @classmethod
    def unique_versions(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Questions must be distinct")
        return value


class Create(DraftInput):
    course_id: UUID


class Save(DraftInput):
    revision: int = Field(strict=True, ge=1)


class Issue(Command):
    expiry_hours: int = Field(24, strict=True, ge=1, le=720)


class Publish(Issue):
    revision: int = Field(strict=True, ge=1)


class Participant(Command):
    email: EmailStr = Field(max_length=254)
    active: bool = Field(True, strict=True)

    @field_validator("email")
    @classmethod
    def lower_email(cls, value):
        return value.lower()


class Join(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    code: str = Field(min_length=1, max_length=64, repr=False)


class Summary(BaseModel):
    id: UUID
    title: str
    course_id: UUID
    state: Literal["draft", "published", "closed"]
    revision: int
    question_count: int
    created_at: datetime


class Page(BaseModel):
    items: list[Summary]
    total: int
    offset: int
    limit: int


class SettingsView(BaseModel):
    time_limit_seconds: int | None
    max_attempts: int
    randomize_questions: bool
    randomize_options: bool
    release_policy: str


class QuestionView(BaseModel):
    version_id: UUID
    position: int
    version: int
    stem: str
    state: str
    mode: str


class ParticipantView(BaseModel):
    student_id: UUID
    email: str
    display_name: str
    active: bool


class CodeView(BaseModel):
    id: UUID
    expires_at: datetime | None
    revoked_at: datetime | None
    active: bool


class Detail(Summary, SettingsView):
    can_publish: bool
    questions: list[QuestionView]
    participants: list[ParticipantView]
    codes: list[CodeView]
    issued_code: str | None = None


class Admission(SettingsView):
    id: UUID
    title: str
    question_count: int
    available: bool


class Admissions(BaseModel):
    items: list[Admission]
    total: int
    offset: int
    limit: int


def reference_code(secret, owner, key, counter=0):
    """80 secret-derived bits, reproducible only for retries of the same command."""
    raw = (
        hmac.new(
            secret.encode(), f"mcq-reference-v1:{owner}:{key}:{counter}".encode(), hashlib.sha256
        )
        .hexdigest()[:20]
        .upper()
    )
    return "MCQ-" + "-".join(raw[i : i + 4] for i in range(0, 20, 4))


def code_digest(value):
    normalized = re.sub(r"[\s-]", "", value).upper()
    # Malformed and unknown codes follow the same database-backed rate limit.
    if not re.fullmatch(r"MCQ[0-9A-F]{20}", normalized):
        normalized = "invalid-reference-code"
    return hashlib.sha256(normalized.encode()).hexdigest()


ERRORS = {
    "ASSESSMENT_FORBIDDEN": 403,
    "ASSESSMENT_NOT_FOUND": 404,
    "ASSESSMENT_KEY_CONFLICT": 409,
    "ASSESSMENT_STALE": 409,
    "ASSESSMENT_INVALID": 422,
    "ASSESSMENT_QUESTION_UNAVAILABLE": 409,
    "ASSESSMENT_BLOCKED": 409,
    "PARTICIPANT_UNAVAILABLE": 409,
    "PARTICIPANT_LIMIT": 409,
    "ASSESSMENT_UNAVAILABLE": 404,
    "CODE_RATE_LIMIT": 429,
}


def check_result(result):
    if "error" in result:
        code = result["error"]
        if code not in ERRORS:
            raise AuthError(503, "DATABASE_UNAVAILABLE", "The assessment could not be saved.")
        raise AuthError(
            ERRORS[code],
            code,
            "The assessment action is unavailable.",
            retry_after=60 if code == "CODE_RATE_LIMIT" else None,
        )


class AssessmentService:
    def __init__(self, database, settings):
        self.database, self.settings = database, settings

    @staticmethod
    def owned(session, owner, target):
        row = (
            session.execute(
                text("""SELECT a.*,(SELECT count(*) FROM mcq.assessment_questions
            WHERE assessment_id=a.id) AS question_count FROM mcq.assessments a
            WHERE a.id=:target AND a.owner_id=:owner AND a.kind='classroom'"""),
                {"owner": owner, "target": target},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise AuthError(404, "ASSESSMENT_NOT_FOUND", "This assessment is unavailable.")
        return dict(row)

    def listing(self, owner, offset, limit):
        with self.database.session() as session:
            params = dict(owner=owner, offset=offset, limit=limit)
            clause = "FROM mcq.assessments a WHERE owner_id=:owner AND kind='classroom'"
            total = session.execute(text("SELECT count(*) " + clause), params).scalar_one()
            rows = (
                session.execute(
                    text(
                        "SELECT a.*,(SELECT count(*) FROM mcq.assessment_questions WHERE assessment_id=a.id) AS question_count "
                        + clause
                        + " ORDER BY created_at DESC,id DESC LIMIT :limit OFFSET :offset"
                    ),
                    params,
                )
                .mappings()
                .all()
            )
        return dict(items=[dict(r) for r in rows], total=total, offset=offset, limit=limit)

    def detail(self, owner, target, issued=None, code_id=None):
        with self.database.session() as session:
            # Serialize the readiness result and metadata with mutations by this teacher.
            session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(CAST(:owner AS text),10))"),
                {"owner": owner},
            )
            result = self.owned(session, owner, target)
            params = dict(target=target)
            result["can_publish"] = (
                result["state"] == "draft"
                and session.execute(
                    text("SELECT mcq.assessment_ready(:target)"), params
                ).scalar_one()
            )
            result["questions"] = [
                dict(r)
                for r in session.execute(
                    text("""SELECT aq.version_id,aq.position,v.version,v.stem,
                COALESCE(r.state,'pending') AS state,COALESCE(g.settings->>'mode','legacy') AS mode
                FROM mcq.assessment_questions aq JOIN mcq.question_versions v ON v.id=aq.version_id
                LEFT JOIN mcq.generation_runs g ON g.id=v.generation_run_id
                LEFT JOIN mcq.question_releases r ON r.version_id=v.id
                WHERE aq.assessment_id=:target ORDER BY aq.position"""),
                    params,
                ).mappings()
            ]
            result["participants"] = [
                dict(r)
                for r in session.execute(
                    text("""SELECT p.student_id,u.email,u.display_name,p.active
                FROM mcq.assessment_participants p JOIN mcq.users u ON u.id=p.student_id
                WHERE p.assessment_id=:target ORDER BY u.email"""),
                    params,
                ).mappings()
            ]
            result["codes"] = [
                dict(r)
                for r in session.execute(
                    text("""SELECT id,expires_at,revoked_at,
                revoked_at IS NULL AND expires_at>clock_timestamp() AS active FROM mcq.reference_codes
                WHERE assessment_id=:target ORDER BY created_at DESC,id DESC LIMIT 20"""),
                    params,
                ).mappings()
            ]
            result["issued_code"] = None
            if issued and code_id and result["state"] == "published":
                live = session.execute(
                    text("""SELECT EXISTS(SELECT 1 FROM mcq.reference_codes
                    WHERE id=:code AND assessment_id=:target AND code_digest=:digest
                    AND revoked_at IS NULL AND expires_at>clock_timestamp())"""),
                    {**params, "code": code_id, "digest": code_digest(issued)},
                ).scalar_one()
                if live:
                    result["issued_code"] = issued
        return result

    def change(self, owner, target, payload, action):
        body = payload.model_dump(mode="json", exclude={"idempotency_key"})
        issued = None
        for counter in range(4):
            if action in ("publish", "rotate"):
                issued = reference_code(
                    self.settings.jwt_secret.get_secret_value(),
                    owner,
                    payload.idempotency_key,
                    counter,
                )
            with self.database.session() as session, session.begin():
                result = session.execute(
                    text(
                        "SELECT mcq.assessment_action(:owner,:target,:key,:op,CAST(:body AS jsonb),:digest)"
                    ),
                    dict(
                        owner=owner,
                        target=target,
                        key=payload.idempotency_key,
                        op=action,
                        body=json.dumps(body),
                        digest=code_digest(issued) if issued else None,
                    ),
                ).scalar_one()
            if result.get("error") != "CODE_COLLISION":
                break
        check_result(result)
        return self.detail(owner, UUID(result["assessment_id"]), issued, result.get("code_id"))

    def join(self, student, payload):
        with self.database.session() as session, session.begin():
            result = session.execute(
                text("SELECT mcq.join_assessment(:student,:digest)"),
                dict(student=student, digest=code_digest(payload.code)),
            ).scalar_one()
        # Commit unsuccessful guesses as well, so rate limits survive rejected requests.
        check_result(result)
        return self.admissions(student, 0, 1, UUID(result["assessment_id"]))["items"][0]

    def admissions(self, student, offset, limit, target=None):
        clause = """FROM mcq.assessment_admissions j JOIN mcq.assessments a ON a.id=j.assessment_id
            WHERE j.student_id=:student"""
        if target:
            clause += " AND a.id=:target"
        with self.database.session() as session:
            params = dict(student=student, offset=offset, limit=limit, target=target)
            total = session.execute(text("SELECT count(*) " + clause), params).scalar_one()
            rows = (
                session.execute(
                    text(
                        """SELECT a.id,a.title,a.time_limit_seconds,a.max_attempts,
                a.randomize_questions,a.randomize_options,a.release_policy,
                (SELECT count(*) FROM mcq.assessment_questions WHERE assessment_id=a.id) AS question_count,
                mcq.assessment_access(:student,a.id,j.code_id) AS available """
                        + clause
                        + " ORDER BY j.joined_at DESC,a.id DESC LIMIT :limit OFFSET :offset"
                    ),
                    params,
                )
                .mappings()
                .all()
            )
        return dict(items=[dict(r) for r in rows], total=total, offset=offset, limit=limit)


router = APIRouter(prefix="/api/v1", tags=["Classroom assessments"])


def service(request):
    return AssessmentService(request.app.state.database, request.app.state.auth.settings)


@router.get("/teacher/assessments", response_model=Page)
def listing(
    principal: Teacher,
    request: Request,
    offset: int = Query(0, ge=0, le=100000),
    limit: int = Query(6, ge=1, le=24),
):
    return service(request).listing(principal.user["id"], offset, limit)


@router.post("/teacher/assessments", response_model=Detail, status_code=201)
def create(payload: Create, principal: Teacher, request: Request):
    return service(request).change(principal.user["id"], None, payload, "create")


@router.get("/teacher/assessments/{assessment_id}", response_model=Detail)
def detail(assessment_id: UUID, principal: Teacher, request: Request):
    return service(request).detail(principal.user["id"], assessment_id)


@router.post("/teacher/assessments/{assessment_id}/save", response_model=Detail)
def save(assessment_id: UUID, payload: Save, principal: Teacher, request: Request):
    return service(request).change(principal.user["id"], assessment_id, payload, "save")


@router.post("/teacher/assessments/{assessment_id}/publish", response_model=Detail)
def publish(assessment_id: UUID, payload: Publish, principal: Teacher, request: Request):
    return service(request).change(principal.user["id"], assessment_id, payload, "publish")


@router.post("/teacher/assessments/{assessment_id}/rotate", response_model=Detail)
def rotate(assessment_id: UUID, payload: Issue, principal: Teacher, request: Request):
    return service(request).change(principal.user["id"], assessment_id, payload, "rotate")


@router.post("/teacher/assessments/{assessment_id}/revoke", response_model=Detail)
def revoke(assessment_id: UUID, payload: Command, principal: Teacher, request: Request):
    return service(request).change(principal.user["id"], assessment_id, payload, "revoke")


@router.post("/teacher/assessments/{assessment_id}/close", response_model=Detail)
def close(assessment_id: UUID, payload: Command, principal: Teacher, request: Request):
    return service(request).change(principal.user["id"], assessment_id, payload, "close")


@router.post("/teacher/assessments/{assessment_id}/participants", response_model=Detail)
def participant(assessment_id: UUID, payload: Participant, principal: Teacher, request: Request):
    return service(request).change(principal.user["id"], assessment_id, payload, "participant")


@router.post("/student/assessments/join", response_model=Admission)
def join(payload: Join, principal: Student, request: Request):
    return service(request).join(principal.user["id"], payload)


@router.get("/student/assessments", response_model=Admissions)
def admissions(
    principal: Student,
    request: Request,
    offset: int = Query(0, ge=0, le=100000),
    limit: int = Query(6, ge=1, le=24),
):
    return service(request).admissions(principal.user["id"], offset, limit)
