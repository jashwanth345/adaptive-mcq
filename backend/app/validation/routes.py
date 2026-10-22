from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from ..auth.routes import current_user
from ..auth.service import Principal
from .math_check import check_math
from .schemas import History, MathPreview, MathRequest, Report, ValidateRequest

router = APIRouter(prefix="/api/v1/validation", tags=["Deterministic validation"])
User = Annotated[Principal, Depends(current_user)]


@router.post("/math-check", response_model=MathPreview)
def math_preview(payload: MathRequest, principal: User):
    return {
        "result": check_math(payload.stem, payload.options, payload.correct_option),
        "saved": False,
        "publication_eligible": False,
    }


@router.post("/drafts/{version_id}/reports", response_model=Report)
def validate(version_id: UUID, payload: ValidateRequest, principal: User, request: Request):
    return request.app.state.validation.validate(principal.user["id"], version_id, payload)


@router.get("/drafts/{version_id}/reports", response_model=History)
def history(
    version_id: UUID,
    principal: User,
    request: Request,
    offset: int = Query(0, ge=0, le=100000),
    limit: int = Query(3, ge=1, le=10),
):
    return request.app.state.validation.history(principal.user["id"], version_id, offset, limit)
