import json
from typing import Any

from redis.asyncio import Redis

from app.core.config import Settings


class RedisCacheService:
    def __init__(self, settings: Settings, redis: Redis):
        self.settings = settings
        self.redis = redis

    def _cache_key(self, namespace: str, key: str) -> str:
        return f"{self.settings.redis_prefix}:cache:{namespace}:{key}"

    async def get_json(self, namespace: str, key: str) -> dict[str, Any] | None:
        try:
            raw = await self.redis.get(self._cache_key(namespace, key))
        except Exception:
            return None
        if raw is None:
            return None
        return json.loads(raw)

    async def set_json(self, namespace: str, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        try:
            await self.redis.set(
                self._cache_key(namespace, key),
                json.dumps(value),
                ex=ttl or self.settings.cache_ttl_seconds,
            )
        except Exception:
            return
