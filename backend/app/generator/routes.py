from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from ..auth.routes import current_user
from ..auth.service import Principal
from .schemas import Draft, DraftPage, GenerateRequest, Readiness
from .service import GeneratorService

router = APIRouter(prefix="/api/v1/generator", tags=["Private unverified drafts"])
User = Annotated[Principal, Depends(current_user)]


def service(request: Request):
    return request.app.state.generator


Service = Annotated[GeneratorService, Depends(service)]


@router.get("/status", response_model=Readiness)
def status(principal: User, generator: Service):
    return generator.status()


@router.post("/drafts", response_model=Draft)
def generate(payload: GenerateRequest, principal: User, generator: Service):
    return generator.generate(principal.user["id"], payload)


@router.get("/drafts", response_model=DraftPage)
def drafts(
    principal: User,
    generator: Service,
    offset: int = Query(0, ge=0, le=100000),
    limit: int = Query(6, ge=1, le=20),
):
    return generator.list(principal.user["id"], offset, limit)


@router.get("/drafts/{version_id}", response_model=Draft)
def draft(version_id: UUID, principal: User, generator: Service):
    return generator.get(principal.user["id"], version_id)
