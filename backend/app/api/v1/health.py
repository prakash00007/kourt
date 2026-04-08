from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy import text

from app.api.deps import get_container
from app.services.container import ServiceContainer

router = APIRouter()


@router.get("/health")
async def health_check(container: ServiceContainer = Depends(get_container)) -> dict[str, object]:
    vector_count = container.vector_store.collection.count()
    provider = container.settings.llm_provider
    llm_configured = (
        bool(container.settings.anthropic_api_key)
        if provider == "anthropic"
        else bool(container.settings.openai_api_key)
    )
    try:
        redis_ok = bool(await container.redis.ping())
    except Exception:
        redis_ok = False

    try:
        async with container.session_factory() as session:
            db_ok = bool((await session.execute(text("SELECT 1"))).scalar())
    except Exception:
        db_ok = False

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
