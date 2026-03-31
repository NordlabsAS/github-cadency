"""FastAPI middleware for request logging context."""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class LoggingContextMiddleware(BaseHTTPMiddleware):
    """Add request_id, method, path to all log entries within a request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start = time.monotonic()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=str(request.url.path),
        )

        response = await call_next(request)

        duration_ms = round((time.monotonic() - start) * 1000, 1)
        logger = structlog.get_logger()
        await logger.ainfo(
            "request.completed",
            status=response.status_code,
            duration_ms=duration_ms,
        )

        response.headers["X-Request-ID"] = request_id
        return response
