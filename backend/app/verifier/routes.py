from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from ..auth.routes import current_user
from ..auth.service import Principal
from .schemas import History, Readiness, Report, VerifyRequest
from .service import VerifierService

router = APIRouter(prefix="/api/v1/verifier", tags=["Advisory draft reviews"])
User = Annotated[Principal, Depends(current_user)]


def service(request: Request):
    return request.app.state.verifier


Service = Annotated[VerifierService, Depends(service)]


@router.get("/status", response_model=Readiness)
def status(principal: User, verifier: Service):
    return verifier.status()


@router.post("/drafts/{version_id}/reports", response_model=Report)
def review(version_id: UUID, payload: VerifyRequest, principal: User, verifier: Service):
    return verifier.review(principal.user["id"], version_id, payload)


@router.get("/drafts/{version_id}/reports", response_model=History)
def history(
    version_id: UUID,
    principal: User,
    verifier: Service,
    offset: int = Query(0, ge=0, le=100000),
    limit: int = Query(3, ge=1, le=10),
):
    return verifier.history(principal.user["id"], version_id, offset, limit)
