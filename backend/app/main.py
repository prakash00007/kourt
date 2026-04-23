import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.core.metrics import MetricsMiddleware
from app.core.request_context import SentryContextMiddleware
from app.core.sentry import init_sentry
from app.core.middleware import RateLimitMiddleware, RequestContextMiddleware
from app.db.base import Base
import app.models  # noqa: F401
from app.services.container import ServiceContainer


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings)
    init_sentry(settings)
    if settings.disable_chroma_telemetry:
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
    app.state.container = ServiceContainer(settings=settings)
    if settings.create_schema_on_startup:
        async with app.state.container.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    await app.state.container.storage_service.ensure_bucket()
    logger.info("Application startup complete", extra={"extra_data": {"env": settings.app_env}})
    yield
    await app.state.container.close()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI copilot for Indian lawyers: research, summarization, and drafting.",
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_url,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
    if settings.enable_metrics:
        app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SentryContextMiddleware, settings=settings)
    app.add_middleware(
        RateLimitMiddleware,
        settings=settings,
    )

    app.include_router(router, prefix=settings.api_prefix)

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        request_id = getattr(request.state, "request_id", None)
        logger.warning(
            "Application error",
            extra={
                "request_id": request_id,
                "extra_data": {"code": exc.code, "path": request.url.path},
            },
        )
        return ORJSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "request_id": request_id}},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", None)
        logger.warning(
            "Request validation failed",
            extra={"request_id": request_id, "extra_data": {"path": request.url.path, "errors": exc.errors()}},
        )
        return ORJSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "request_validation_error",
                    "message": "Invalid request payload.",
                    "request_id": request_id,
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", None)
        logger.exception(
            "Unhandled server error",
            extra={"request_id": request_id, "extra_data": {"path": request.url.path}},
        )
        return ORJSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred.",
                    "request_id": request_id,
                }
            },
        )

    return app


app = create_app()
