from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware

from .adaptive import router as adaptive_router
from .analytics import router as analytics_router
from .assessments import router as assessment_router
from .attempts import router as attempt_router
from .auth.routes import router as auth_router
from .auth.security import AuthError
from .auth.service import AuthService
from .config import PROJECT_ROOT, Settings, load_settings
from .database import Database
from .errors import auth_error, database_error, http_error, validation_error
from .evaluation import router as evaluation_router
from .feedback import router as feedback_router
from .generator.routes import router as generator_router
from .generator.service import GeneratorService
from .materials.routes import router as material_router
from .materials.service import MaterialService
from .middleware import RequestMiddleware
from .rag.routes import router as rag_router
from .rag.service import RagService
from .student.routes import router as student_router
from .teacher.review import router as teacher_review_router
from .teacher.routes import router as teacher_router
from .validation.routes import router as validation_router
from .validation.service import ValidationService
from .verifier.routes import router as verifier_router
from .verifier.service import VerifierService


class LiveResponse(BaseModel):
    status: Literal["alive"] = "alive"
    service: Literal["adaptive-mcq-backend"] = "adaptive-mcq-backend"


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    scope: Literal["backend_foundation"] = "backend_foundation"
    checks: dict[str, str]


def get_database(request: Request) -> Database:
    return request.app.state.database


def get_session(database: Annotated[Database, Depends(get_database)]):
    with database.session() as session:
        yield session


def create_app(settings: Settings | None = None, *, database_factory=Database) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database = database_factory(settings)
        app.state.database = database
        try:
            app.state.auth = AuthService(database, settings)
            app.state.materials = MaterialService(
                database, PROJECT_ROOT / settings.upload_directory
            )
            app.state.rag = RagService(database, settings)
            app.state.generator = GeneratorService(database, settings, app.state.rag)
            app.state.verifier = VerifierService(
                database, settings, app.state.generator, app.state.rag
            )
            app.state.validation = ValidationService(
                database, app.state.generator, app.state.verifier, app.state.rag
            )
            yield
        finally:
            database.close()

    app = FastAPI(
        title="Adaptive MCQ — Local API",
        version="0.19.0",
        description="Local accounts, dashboards, PDFs, retrieval, draft review and teacher versioned editing/approval. Default generation and review use labelled test fixtures that cannot be approved. Real LLM adapters await hardware and quality validation. Teacher approval requires fresh passing evidence; classroom publication and authorized reference-code admission are available. Saved attempts, server grading, result release, candidate adaptive profiles, feedback review and scoped operational analytics are available.",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(AuthError, auth_error)
    app.add_exception_handler(SQLAlchemyError, database_error)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestMiddleware, allowed_origin=settings.frontend_origin)
    router = APIRouter(prefix="/api/v1/health", tags=["Health"])

    @router.get("/live", response_model=LiveResponse)
    def live(response: Response):
        """Process liveness, independent of database availability."""
        response.headers["Cache-Control"] = "no-store"
        return LiveResponse()

    @router.get(
        "/ready",
        response_model=ReadyResponse,
        responses={
            503: {
                "model": ReadyResponse,
                "description": "Database foundation unavailable or incomplete",
            }
        },
    )
    def ready(response: Response, database: Annotated[Database, Depends(get_database)]):
        """Checks connectivity, pgvector, migration checksums and runtime role."""
        result = database.readiness()
        response.status_code = 200 if result["status"] == "ready" else 503
        response.headers["Cache-Control"] = "no-store"
        return result

    app.include_router(router)
    app.include_router(auth_router)
    app.include_router(teacher_router)
    app.include_router(assessment_router)
    app.include_router(attempt_router)
    app.include_router(adaptive_router)
    app.include_router(analytics_router)
    app.include_router(evaluation_router)
    app.include_router(feedback_router)
    app.include_router(teacher_review_router)
    app.include_router(student_router)
    app.include_router(material_router)
    app.include_router(rag_router)
    app.include_router(generator_router)
    app.include_router(verifier_router)
    app.include_router(validation_router)

    @app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
    def offline_docs():
        return HTMLResponse(
            Path(__file__).with_name("docs.html").read_text(encoding="utf-8"),
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'",
            },
        )

    return app
