"""Tests for the frontend log ingestion endpoint."""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.logging import configure_logging
from app.main import app


@pytest.fixture(autouse=True)
def _setup_logging():
    configure_logging(level="INFO", json_output=True)


@pytest.mark.asyncio
async def test_ingest_logs_returns_204(capsys):
    """POST /api/logs/ingest should return 204 and emit structured logs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/logs/ingest", json={
            "entries": [
                {
                    "level": "error",
                    "message": "Failed to load dashboard",
                    "event_type": "frontend.error",
                    "context": {"component": "Dashboard", "status": 500},
                    "timestamp": "2026-03-31T12:00:00.000Z",
                    "url": "http://localhost:3001/",
                    "user_agent": "TestAgent/1.0",
                }
            ]
        })
    assert resp.status_code == 204

    captured = capsys.readouterr()
    lines = [l for l in captured.out.strip().split("\n") if l.strip()]
    frontend_logs = []
    for line in lines:
        try:
            data = json.loads(line)
            if data.get("source") == "frontend":
                frontend_logs.append(data)
        except (json.JSONDecodeError, ValueError):
            continue

    assert len(frontend_logs) >= 1
    log = frontend_logs[0]
    assert log["event"] == "Failed to load dashboard"
    assert log["event_type"] == "frontend.error"
    assert log["source"] == "frontend"
    assert log["url"] == "http://localhost:3001/"
    assert log["component"] == "Dashboard"
    assert log["status"] == 500


@pytest.mark.asyncio
async def test_ingest_empty_batch():
    """Empty entries list should still return 204."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/logs/ingest", json={"entries": []})
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_ingest_warn_level(capsys):
    """Warn-level entries should be logged at warning level."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/logs/ingest", json={
            "entries": [
                {
                    "level": "warn",
                    "message": "Slow API response",
                    "event_type": "frontend.warn",
                }
            ]
        })
    assert resp.status_code == 204

    captured = capsys.readouterr()
    lines = [l for l in captured.out.strip().split("\n") if l.strip()]
    for line in lines:
        try:
            data = json.loads(line)
            if data.get("event") == "Slow API response":
                assert data["level"] == "warning"
                assert data["source"] == "frontend"
                return
        except (json.JSONDecodeError, ValueError):
            continue
    pytest.fail("Expected warn-level frontend log not found")


@pytest.mark.asyncio
async def test_ingest_caps_at_max_entries(capsys):
    """Should only process first 50 entries even if more are sent."""
    transport = ASGITransport(app=app)
    entries = [
        {"level": "error", "message": f"Error #{i}"}
        for i in range(60)
    ]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/logs/ingest", json={"entries": entries})
    assert resp.status_code == 204

    captured = capsys.readouterr()
    lines = [l for l in captured.out.strip().split("\n") if l.strip()]
    frontend_logs = []
    for line in lines:
        try:
            data = json.loads(line)
            if data.get("source") == "frontend":
                frontend_logs.append(data)
        except (json.JSONDecodeError, ValueError):
            continue
    assert len(frontend_logs) == 50


@pytest.mark.asyncio
async def test_ingest_no_auth_required():
    """Endpoint should work without authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/logs/ingest", json={
            "entries": [{"level": "error", "message": "no auth"}]
        })
    assert resp.status_code == 204
