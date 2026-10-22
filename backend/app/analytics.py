"""Operational analytics from authoritative events; never a learning-gain claim."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from sqlalchemy import text

from .auth.security import AuthError
from .student.routes import Student
from .teacher.routes import Teacher

router = APIRouter(prefix="/api/v1", tags=["Analytics"])
Offset = Annotated[int, Query(ge=0, le=1000000)]
Limit = Annotated[int, Query(ge=1, le=50)]


def read(request, account, audience, target, offset, limit, ranking=False):
    with request.app.state.database.session() as session:
        data = session.execute(
            text("SELECT mcq.analytics_data(:account,:audience,:target,:offset,:limit,:ranking)"),
            dict(
                account=account,
                audience=audience,
                target=target,
                offset=offset,
                limit=limit,
                ranking=ranking,
            ),
        ).scalar_one()
    if "error" in data:
        code = data["error"]
        raise AuthError(
            {"ANALYTICS_FORBIDDEN": 403, "ANALYTICS_NOT_FOUND": 404, "ANALYTICS_INVALID": 422}.get(
                code, 503
            ),
            code,
            "Analytics are unavailable for this selection.",
        )
    return data


@router.get("/student/analytics")
def student(principal: Student, request: Request, offset: Offset = 0, limit: Limit = 20):
    return read(request, principal.user["id"], "student", None, offset, limit)


@router.get("/teacher/analytics")
def teacher(principal: Teacher, request: Request, offset: Offset = 0, limit: Limit = 20):
    return read(request, principal.user["id"], "teacher", None, offset, limit)


@router.get("/teacher/assessments/{assessment_id}/analytics")
def assessment(
    assessment_id: UUID,
    principal: Teacher,
    request: Request,
    offset: Offset = 0,
    limit: Limit = 20,
    ranking: bool = False,
):
    return read(request, principal.user["id"], "teacher", assessment_id, offset, limit, ranking)
