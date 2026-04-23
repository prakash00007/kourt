from fastapi import APIRouter, Depends, Response, status
from prometheus_client import CONTENT_TYPE_LATEST
from sqlalchemy import text

from app.api.deps import get_container
from app.core.metrics import render_metrics
from app.services.container import ServiceContainer

router = APIRouter()


async def _dependency_status(container: ServiceContainer) -> tuple[bool, bool]:
    try:
        redis_ok = bool(await container.redis.ping())
    except Exception:
        redis_ok = False

    try:
        async with container.session_factory() as session:
            db_ok = bool((await session.execute(text("SELECT 1"))).scalar())
    except Exception:
        db_ok = False
    return redis_ok, db_ok


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "live"}


@router.get("/health/ready")
async def health_ready(
    response: Response,
    container: ServiceContainer = Depends(get_container),
) -> dict[str, object]:
    redis_ok, db_ok = await _dependency_status(container)
    provider = container.settings.llm_provider
    llm_configured = (
        bool(container.settings.anthropic_api_key)
        if provider == "anthropic"
        else bool(container.settings.openai_api_key)
    )
    storage_ok = True
    try:
        await container.storage_service.ensure_bucket()
    except Exception:
        storage_ok = False

    ready = redis_ok and db_ok and llm_configured and storage_ok
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if ready else "not_ready",
        "checks": {
            "database": db_ok,
            "redis": redis_ok,
            "llm_configured": llm_configured,
            "storage": storage_ok,
        },
    }


@router.get("/health")
async def health_check(container: ServiceContainer = Depends(get_container)) -> dict[str, object]:
    vector_count = container.vector_store.collection.count()
    provider = container.settings.llm_provider
    llm_configured = (
        bool(container.settings.anthropic_api_key)
        if provider == "anthropic"
        else bool(container.settings.openai_api_key)
    )
    redis_ok, db_ok = await _dependency_status(container)

    overall_status = "ok" if redis_ok and db_ok else "degraded"
    return {
        "status": overall_status,
        "app": container.settings.app_name,
        "version": container.settings.app_version,
        "services": {
            "database_ready": db_ok,
            "redis_ready": redis_ok,
            "vector_store_ready": vector_count >= 0,
            "vector_document_count": vector_count,
            "llm_provider": provider,
            "llm_configured": llm_configured,
        },
    }


@router.get("/metrics")
async def metrics() -> Response:
    return Response(content=render_metrics(), media_type=CONTENT_TYPE_LATEST)
