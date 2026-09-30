import logging
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Removed 'ai' from the imports here
from .api import documents, relational, tabular
from .config import get_settings
from .schemas.common import ErrorResponse, HealthResponse, ValidationIssue

log = logging.getLogger("sdp")

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Privacy-safe synthetic tabular, relational and document data on demand.",
    )
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=["*"], allow_headers=["*"], expose_headers=["Content-Disposition"])

    @app.middleware("http")
    async def timing(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - start) * 1000:.1f}"
        return response

    @app.exception_handler(RequestValidationError)
    async def on_validation(_: Request, exc: RequestValidationError):
        issues = [ValidationIssue(loc=list(e["loc"]), msg=str(e["msg"]), type=e["type"]) for e in exc.errors()]
        body = ErrorResponse(code="validation_error", message="Request failed validation.", issues=issues)
        return JSONResponse(status_code=422, content=body.model_dump())

    @app.exception_handler(StarletteHTTPException)
    async def on_http(_: Request, exc: StarletteHTTPException):
        code = "not_implemented" if exc.status_code == 501 else f"http_{exc.status_code}"
        body = ErrorResponse(code=code, message=str(exc.detail))
        return JSONResponse(status_code=exc.status_code, content=body.model_dump())

    @app.exception_handler(Exception)
    async def on_unhandled(_: Request, exc: Exception):
        log.exception("Unhandled error")
        body = ErrorResponse(code="internal_error", message="Unexpected server error.")
        return JSONResponse(status_code=500, content=body.model_dump())

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    def health():
        return HealthResponse(version=settings.version, llm_configured=settings.llm_configured)

    # Removed 'ai.router' from the loop here
    for r in (tabular.router, relational.router, documents.router):
        app.include_router(r)
        
    return app

app = create_app()