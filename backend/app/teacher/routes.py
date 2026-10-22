from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from ..auth.routes import require_role
from ..auth.service import Principal
from .schemas import Course, CourseDetail, CourseInput, CoursePage, Dashboard, Topic, TopicInput
from .service import TeacherService

router = APIRouter(prefix="/api/v1/teacher", tags=["Teacher workspace"])
Teacher = Annotated[Principal, Depends(require_role("teacher"))]


def service(request: Request):
    return TeacherService(request.app.state.database)


Service = Annotated[TeacherService, Depends(service)]


@router.get("/dashboard", response_model=Dashboard)
def dashboard(principal: Teacher, teacher: Service):
    return teacher.dashboard(principal.user["id"])


@router.get("/courses", response_model=CoursePage)
def courses(
    principal: Teacher,
    teacher: Service,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    limit: Annotated[int, Query(ge=1, le=24)] = 6,
):
    return teacher.courses(principal.user["id"], offset, limit)


@router.post("/courses", response_model=Course, status_code=201)
def create_course(payload: CourseInput, principal: Teacher, teacher: Service):
    return teacher.create(principal.user["id"], payload.title)


@router.get("/courses/{course_id}", response_model=CourseDetail)
def course_detail(course_id: UUID, principal: Teacher, teacher: Service):
    return teacher.detail(principal.user["id"], course_id)


@router.post("/courses/{course_id}/topics", response_model=Topic, status_code=201)
def create_topic(course_id: UUID, payload: TopicInput, principal: Teacher, teacher: Service):
    return teacher.create(principal.user["id"], payload.title, course_id)
