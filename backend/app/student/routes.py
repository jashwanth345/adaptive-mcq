from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from ..auth.routes import require_role
from ..auth.service import Principal
from .schemas import AttemptPage, Dashboard, Preferences
from .service import StudentService

router = APIRouter(prefix="/api/v1/student", tags=["Student workspace"])
Student = Annotated[Principal, Depends(require_role("student"))]


def service(request: Request):
    return StudentService(request.app.state.database)


Service = Annotated[StudentService, Depends(service)]


@router.get("/dashboard", response_model=Dashboard)
def dashboard(principal: Student, student: Service):
    return student.dashboard(principal.user["id"])


@router.get("/attempts", response_model=AttemptPage)
def attempts(
    principal: Student,
    student: Service,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    limit: Annotated[int, Query(ge=1, le=24)] = 6,
):
    return student.attempts(principal.user["id"], offset, limit)


@router.post("/preferences", response_model=Preferences)
def preferences(payload: Preferences, principal: Student, student: Service):
    return student.preferences(principal.user["id"], payload.preferred_difficulty)
