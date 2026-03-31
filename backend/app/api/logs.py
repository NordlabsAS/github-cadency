"""Frontend log ingestion endpoint."""

from fastapi import APIRouter, Response, status

from app.logging import get_logger
from app.schemas.schemas import FrontendLogBatch

router = APIRouter()

logger = get_logger("app.frontend")

MAX_ENTRIES = 50


@router.post("/logs/ingest", status_code=status.HTTP_204_NO_CONTENT)
async def ingest_logs(batch: FrontendLogBatch) -> Response:
    """Receive frontend log entries and emit them through the structlog pipeline."""
    for entry in batch.entries[:MAX_ENTRIES]:
        log_fn = logger.error if entry.level == "error" else logger.warning
        log_fn(
            entry.message,
            event_type=entry.event_type,
            source="frontend",
            url=entry.url,
            frontend_timestamp=entry.timestamp,
            **(entry.context or {}),
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
