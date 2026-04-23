import logging
import time
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import Settings


logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()

        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-process-time-ms"] = str(round((time.perf_counter() - started) * 1000, 2))
        return response

class RedisRateLimiter:
    def __init__(self, settings: Settings, redis: Redis):
        self.settings = settings
        self.redis = redis

    def _key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "anonymous"

    async def allow(self, request: Request) -> bool:
        key = f"{self.settings.redis_prefix}:ratelimit:{self._key(request)}:{int(time.time() // self.settings.rate_limit_window_seconds)}"
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, self.settings.rate_limit_window_seconds)
        return current <= self.settings.rate_limit_requests


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.endswith("/health") or path.endswith("/health/live") or path.endswith("/health/ready") or path.endswith("/metrics"):
            return await call_next(request)

        redis = request.app.state.container.redis
        limiter = RedisRateLimiter(self.settings, redis)
        try:
            allowed = await limiter.allow(request)
        except Exception:
            logger.warning(
                "Rate limiter unavailable, allowing request",
                extra={"request_id": getattr(request.state, "request_id", None), "extra_data": {"path": request.url.path}},
            )
            return await call_next(request)

        if not allowed:
            request_id = getattr(request.state, "request_id", str(uuid4()))
            logger.warning(
                "Rate limit exceeded",
                extra={"request_id": request_id, "extra_data": {"path": request.url.path}},
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": "Too many requests. Please retry shortly.",
                        "request_id": request_id,
                    }
                },
            )
        return await call_next(request)
