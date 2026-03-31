"""Tests for the LoggingContextMiddleware."""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.logging import configure_logging
from app.main import app


@pytest.fixture(autouse=True)
def _setup_logging():
    configure_logging(level="INFO", json_output=True)


@pytest.mark.asyncio
async def test_request_id_header():
    """Response should include X-Request-ID header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/health")
    assert "X-Request-ID" in resp.headers
    assert len(resp.headers["X-Request-ID"]) == 8


@pytest.mark.asyncio
async def test_request_completed_log(capsys):
    """Non-health requests should emit a request.completed log."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Use a route that exists but doesn't need auth — health is skipped,
        # so use a route that returns a non-500 even without auth.
        resp = await ac.get("/api/health/nonexistent")
    captured = capsys.readouterr()
    # Look for any request.completed log line
    lines = [l for l in captured.out.strip().split("\n") if l.strip()]
    completed_lines = []
    for line in lines:
        try:
            data = json.loads(line)
            if data.get("event") == "request.completed":
                completed_lines.append(data)
        except (json.JSONDecodeError, ValueError):
            continue
    assert len(completed_lines) >= 1
    log = completed_lines[0]
    assert log["event_type"] == "system.http"
    assert "duration_ms" in log
    assert "status" in log
    assert "request_id" in log
    assert "method" in log
    assert "path" in log


@pytest.mark.asyncio
async def test_health_check_not_logged(capsys):
    """Health check requests should NOT emit request.completed logs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.get("/api/health")
    captured = capsys.readouterr()
    lines = [l for l in captured.out.strip().split("\n") if l.strip()]
    for line in lines:
        try:
            data = json.loads(line)
            if data.get("event") == "request.completed" and data.get("path") == "/api/health":
                pytest.fail("Health check should not emit request.completed log")
        except (json.JSONDecodeError, ValueError):
            continue


@pytest.mark.asyncio
async def test_request_id_is_unique():
    """Each request should get a unique request_id."""
    transport = ASGITransport(app=app)
    ids = []
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for _ in range(5):
            resp = await ac.get("/api/health")
            ids.append(resp.headers["X-Request-ID"])
    assert len(set(ids)) == 5
