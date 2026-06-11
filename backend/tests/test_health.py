"""Tests for the health endpoint and app factory."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import __version__
from app.config import Settings
from app.main import create_app


def make_client() -> TestClient:
    app = create_app(Settings(environment="test", debug=True))
    return TestClient(app)


def test_health_ok() -> None:
    client = make_client()
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["uptime_seconds"] >= 0


def test_openapi_served() -> None:
    client = make_client()
    res = client.get("/openapi.json")
    assert res.status_code == 200
    assert res.json()["info"]["title"] == "WebHawk API"


def test_settings_env_prefix(monkeypatch) -> None:
    monkeypatch.setenv("WEBHAWK_PORT", "9999")
    settings = Settings()
    assert settings.port == 9999
    assert settings.is_production is False
