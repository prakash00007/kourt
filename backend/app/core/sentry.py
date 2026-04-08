from fastapi import Request
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.core.config import Settings
from app.core.security import decode_access_token


def init_sentry(settings: Settings) -> None:
    if not settings.sentry_dsn:
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
        integrations=[FastApiIntegration(), StarletteIntegration()],
        before_send=_before_send,
    )


def _before_send(event, hint):
    request = event.get("request")
    if request:
        headers = request.get("headers") or {}
        scrubbed_headers = {
            key: value
            for key, value in headers.items()
            if key.lower() not in {"authorization", "cookie", "x-api-key"}
        }
        request["headers"] = scrubbed_headers
        if "data" in request:
            request["data"] = "[REDACTED]"
    return event


async def attach_sentry_user_context(request: Request, settings: Settings) -> None:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        sentry_sdk.set_user(None)
        return

    token = auth_header.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(settings, token)
    except Exception:
        sentry_sdk.set_user(None)
        return

    user_id = payload.get("sub")
    if user_id:
        request.state.auth_user_id = user_id
        sentry_sdk.set_user({"id": user_id})
    else:
        sentry_sdk.set_user(None)
