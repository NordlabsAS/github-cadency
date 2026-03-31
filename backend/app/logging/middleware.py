"""FastAPI middleware for request logging context."""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Paths to skip logging (health checks, infrastructure probes)
_SKIP_PATHS = frozenset({"/api/health"})


class LoggingContextMiddleware(BaseHTTPMiddleware):
    """Add request_id, method, path to all log entries within a request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = uuid.uuid4().hex[:8]
        path = request.url.path

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=path,
        )

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 1)

        if path not in _SKIP_PATHS:
            logger = structlog.get_logger("app.middleware")
            await logger.ainfo(
                "request.completed",
                status=response.status_code,
                duration_ms=duration_ms,
                event_type="system.http",
            )

        response.headers["X-Request-ID"] = request_id
        return response
