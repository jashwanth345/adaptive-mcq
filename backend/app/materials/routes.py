import asyncio
import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from ..auth.routes import current_user
from ..auth.service import Principal
from .extract import MAX_BYTES
from .schemas import MaterialPage, Preview, Title, Uploaded
from .service import MaterialService, file_digest, reject

router = APIRouter(prefix="/api/v1/materials", tags=["Private materials"])
User = Annotated[Principal, Depends(current_user)]


def service(request: Request):
    return request.app.state.materials


Service = Annotated[MaterialService, Depends(service)]


@router.get("", response_model=MaterialPage)
def listing(
    principal: User,
    materials: Service,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    limit: Annotated[int, Query(ge=1, le=24)] = 6,
):
    return materials.listing(principal.user["id"], offset, limit)


@router.get("/{material_id}", response_model=Preview)
def preview(
    material_id: UUID,
    principal: User,
    materials: Service,
    page: Annotated[int, Query(ge=1, le=100)] = 1,
):
    return materials.preview(principal.user["id"], material_id, page)


@router.post(
    "",
    response_model=Uploaded,
    status_code=201,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
async def upload(
    request: Request, principal: User, materials: Service, title: Annotated[Title, Query()]
):
    if (
        request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        != "application/pdf"
    ):
        raise reject("PDF_REQUIRED", 415)
    if request.headers.get("content-encoding", "identity") != "identity":
        raise reject("PDF_REQUIRED", 415)
    lengths = request.headers.getlist("content-length")
    if lengths and (len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,10}", lengths[0])):
        raise reject("INVALID_CONTENT_LENGTH", 400)
    if lengths and int(lengths[0]) > MAX_BYTES:
        raise reject("PDF_TOO_LARGE", 413)
    if not materials.gate.acquire(blocking=False):
        raise reject("PDF_BUSY", 409)
    path, retained = None, False
    try:
        path = materials.new_path()
        size = 0
        try:
            async with asyncio.timeout(15):
                with path.open("xb") as file:
                    async for part in request.stream():
                        size += len(part)
                        if size > MAX_BYTES:
                            raise reject("PDF_TOO_LARGE", 413)
                        file.write(part)
        except TimeoutError:
            raise reject("PDF_UPLOAD_TIMEOUT", 408) from None
        if lengths and size != int(lengths[0]):
            raise reject("INVALID_CONTENT_LENGTH", 400)
        digest = await run_in_threadpool(file_digest, path)
        data = await run_in_threadpool(materials.extract, path)
        try:
            result = await run_in_threadpool(
                materials.store, principal.user["id"], title, path, digest, size, data
            )
        except SQLAlchemyError:
            # A connection failure can make COMMIT's outcome uncertain. Preserve
            # the file for operator reconciliation rather than break a committed row.
            retained = True
            raise
        retained = not result["reused"]
        return result
    except OSError:
        raise reject("UPLOAD_STORAGE_UNAVAILABLE", 503) from None
    finally:
        try:
            if path is not None and not retained:
                path.unlink(missing_ok=True)
        finally:
            materials.gate.release()
