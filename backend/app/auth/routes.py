from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .schemas import (
    ChangePasswordRequest,
    Credentials,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from .security import AuthError, unauthorized
from .service import AuthService, Principal

router = APIRouter(prefix="/api/v1", tags=["Authentication"])
bearer = HTTPBearer(auto_error=False, scheme_name="LocalBearer")


def get_auth(request: Request) -> AuthService:
    return request.app.state.auth


def peer(request: Request) -> str:
    # Proxy headers are not trusted. Rate limits use the direct connection only.
    return request.client.host if request.client else "local-unknown"


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    auth: Annotated[AuthService, Depends(get_auth)],
) -> Principal:
    if credentials is None:
        raise unauthorized()
    return auth.authenticate(credentials.credentials)


def require_role(role: str):
    def check(principal: Annotated[Principal, Depends(current_user)]):
        if role not in principal.user["roles"]:
            raise AuthError(403, "ROLE_REQUIRED", "This role is required for the requested action.")
        return principal

    return check


@router.post("/auth/register", response_model=UserResponse, status_code=201)
def register(
    payload: RegisterRequest, request: Request, auth: Annotated[AuthService, Depends(get_auth)]
):
    """Create a student account only. A role field is not accepted."""
    return auth.register(payload, peer(request))


@router.post("/auth/register-teacher", response_model=UserResponse, status_code=201)
def register_teacher(
    payload: RegisterRequest, request: Request, auth: Annotated[AuthService, Depends(get_auth)]
):
    """Create a new isolated teacher workspace; never promote an existing account."""
    return auth.register(payload, peer(request), teacher=True)


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: Credentials, request: Request, auth: Annotated[AuthService, Depends(get_auth)]):
    """JSON credentials; returns a short-lived, revocable bearer token."""
    return auth.login(payload.email, payload.password.get_secret_value(), peer(request))


@router.get("/auth/me", response_model=UserResponse)
def me(principal: Annotated[Principal, Depends(current_user)]):
    return principal.user


@router.post("/auth/logout", status_code=204)
def logout(
    principal: Annotated[Principal, Depends(current_user)],
    auth: Annotated[AuthService, Depends(get_auth)],
):
    auth.logout(principal)
    return Response(status_code=204)


@router.post("/auth/logout-all", status_code=204)
def logout_all(
    principal: Annotated[Principal, Depends(current_user)],
    auth: Annotated[AuthService, Depends(get_auth)],
):
    auth.logout(principal, all_sessions=True)
    return Response(status_code=204)


@router.post("/auth/change-password", status_code=204)
def change_password(
    payload: ChangePasswordRequest,
    principal: Annotated[Principal, Depends(current_user)],
    auth: Annotated[AuthService, Depends(get_auth)],
):
    auth.change_password(
        principal,
        payload.current_password.get_secret_value(),
        payload.new_password.get_secret_value(),
    )
    return Response(status_code=204)


@router.get("/roles/teacher", tags=["Role checks"])
def teacher_access(principal: Annotated[Principal, Depends(require_role("teacher"))]):
    """Role gate only; this is not a teacher dashboard."""
    return {"role": "teacher", "authorized": True}


@router.get("/roles/student", tags=["Role checks"])
def student_access(principal: Annotated[Principal, Depends(require_role("student"))]):
    return {"role": "student", "authorized": True}
