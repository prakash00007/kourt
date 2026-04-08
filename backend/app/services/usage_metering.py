from datetime import datetime
from uuid import UUID

from redis.asyncio import Redis

from app.core.config import Settings


class UsageMeteringService:
    def __init__(self, settings: Settings, redis: Redis):
        self.settings = settings
        self.redis = redis

    async def check_and_increment_draft_usage(self, user_id: UUID) -> tuple[bool, int]:
        today = datetime.utcnow().strftime("%Y%m%d")
        key = f"{self.settings.redis_prefix}:usage:drafts:{user_id}:{today}"
        try:
            current = await self.redis.incr(key)
            if current == 1:
                await self.redis.expire(key, 60 * 60 * 24)
        except Exception:
            return True, 0
        allowed = current <= self.settings.draft_daily_limit
        return allowed, current
