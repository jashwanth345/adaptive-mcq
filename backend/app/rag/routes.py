from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from ..auth.routes import current_user
from ..auth.service import Principal
from .schemas import IndexStatus, SearchRequest, SearchResponse
from .service import RagService

router = APIRouter(prefix="/api/v1/rag", tags=["Local source retrieval"])
User = Annotated[Principal, Depends(current_user)]


def service(request: Request):
    return request.app.state.rag


Service = Annotated[RagService, Depends(service)]


@router.get("/materials/{material_id}", response_model=IndexStatus)
def status(material_id: UUID, principal: User, rag: Service):
    return rag.status(principal.user["id"], material_id)


@router.post("/materials/{material_id}/index", response_model=IndexStatus)
def index(material_id: UUID, principal: User, rag: Service):
    return rag.index(principal.user["id"], material_id)


@router.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest, principal: User, rag: Service):
    return rag.search(principal.user["id"], payload)
