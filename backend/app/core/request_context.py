from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import Settings
from app.core.sentry import attach_sentry_user_context


class SentryContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next):
        await attach_sentry_user_context(request, self.settings)
        response = await call_next(request)
        return response
