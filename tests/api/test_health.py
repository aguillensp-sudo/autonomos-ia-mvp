"""Unit tests for GET /health. Correction found during Task 9 (specs/integracion-mvp):
the `redis` field was a hardcoded "not_configured" stub, stale now that Task 3
wires ARQ WorkerSettings — it now pings Redis for real.
"""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


@patch("src.api.routers.health.redis")
@patch("src.api.routers.health.create_client")
def test_health_todo_ok(mock_create_client, mock_redis):
    mock_create_client.return_value = MagicMock()
    mock_redis.from_url.return_value.ping.return_value = True

    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "db": "ok", "redis": "ok"}


@patch("src.api.routers.health.redis")
@patch("src.api.routers.health.create_client")
def test_health_db_error(mock_create_client, mock_redis):
    mock_create_client.side_effect = Exception("db down")
    mock_redis.from_url.return_value.ping.return_value = True

    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "db": "error", "redis": "ok"}


@patch("src.api.routers.health.redis")
@patch("src.api.routers.health.create_client")
def test_health_redis_error(mock_create_client, mock_redis):
    mock_create_client.return_value = MagicMock()
    mock_redis.from_url.side_effect = Exception("redis down")

    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "db": "ok", "redis": "error"}
