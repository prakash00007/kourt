import re
import time

from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware


REQUEST_COUNT = Counter(
    "kourt_http_requests_total",
    "Total HTTP requests handled by the API.",
    ["method", "path", "status_code"],
)
REQUEST_DURATION = Histogram(
    "kourt_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
IN_PROGRESS = Gauge(
    "kourt_http_requests_in_progress",
    "Number of HTTP requests currently in progress.",
)

_UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_INT_PATTERN = re.compile(r"/\d+")


def normalize_metrics_path(path: str) -> str:
    path = _UUID_PATTERN.sub(":id", path)
    path = _INT_PATTERN.sub("/:int", path)
    return path


def render_metrics() -> bytes:
    return generate_latest()


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        method = request.method
        path = normalize_metrics_path(request.url.path)
        started = time.perf_counter()

        IN_PROGRESS.inc()
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
        except Exception:
            status_code = "500"
            REQUEST_COUNT.labels(method=method, path=path, status_code=status_code).inc()
            REQUEST_DURATION.labels(method=method, path=path).observe(time.perf_counter() - started)
            raise
        finally:
            IN_PROGRESS.dec()

        REQUEST_COUNT.labels(method=method, path=path, status_code=status_code).inc()
        REQUEST_DURATION.labels(method=method, path=path).observe(time.perf_counter() - started)
        return response
