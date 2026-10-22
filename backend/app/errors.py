from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


def error_response(request: Request, status: int, code: str, message: str, details=None):
    request_id = getattr(request.state, "request_id", str(uuid4()))
    body = {"error": {"code": code, "message": message, "request_id": request_id}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(
        body, status_code=status, headers={"X-Request-ID": request_id, "Cache-Control": "no-store"}
    )


async def http_error(request: Request, exc: HTTPException):
    # Do not serialize arbitrary exception.detail: future callers may include secrets.
    messages = {
        404: "Route not found.",
        405: "Method not allowed.",
        401: "Authentication required.",
        403: "Access denied.",
    }
    response = error_response(
        request,
        exc.status_code,
        f"HTTP_{exc.status_code}",
        messages.get(exc.status_code, "Request could not be completed."),
    )
    # Preserve protocol headers without forwarding arbitrary content.
    for key, value in (exc.headers or {}).items():
        if key.lower() in {"allow", "www-authenticate", "retry-after"}:
            response.headers[key] = value
    return response


async def validation_error(request: Request, exc: RequestValidationError):
    details = [{"location": list(e["loc"]), "type": e["type"]} for e in exc.errors()]
    return error_response(request, 422, "VALIDATION_ERROR", "Request validation failed.", details)


async def auth_error(request: Request, exc):
    response = error_response(request, exc.status, exc.code, exc.message)
    if exc.status == 401:
        response.headers["WWW-Authenticate"] = "Bearer"
    if exc.retry_after is not None:
        response.headers["Retry-After"] = str(exc.retry_after)
    return response


async def database_error(request: Request, exc):
    return error_response(
        request, 503, "DATABASE_UNAVAILABLE", "Local database operation is unavailable."
    )
