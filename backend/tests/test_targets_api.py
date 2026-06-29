"""Integration tests for the target registration + verification API.

Uses an in-memory SQLite database and fake DNS/file verifiers wired in via
FastAPI dependency overrides, so the suite runs offline and deterministically.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.targets import get_file_fetcher, get_txt_resolver
from app.db import Base, get_session
from app.main import create_app
from app.verification import WELL_KNOWN_PATH, expected_txt_record


class FakeResolver:
    def __init__(self) -> None:
        self.table: dict[str, list[str]] = {}

    def resolve_txt(self, host: str) -> list[str]:
        return self.table.get(host, [])


class FakeFetcher:
    def __init__(self) -> None:
        self.table: dict[str, str | None] = {}

    def fetch_text(self, url: str) -> str | None:
        return self.table.get(url)


@pytest.fixture
def ctx() -> Iterator[tuple[TestClient, FakeResolver, FakeFetcher]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_session() -> Iterator[Session]:
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    resolver = FakeResolver()
    fetcher = FakeFetcher()

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_txt_resolver] = lambda: resolver
    app.dependency_overrides[get_file_fetcher] = lambda: fetcher

    with TestClient(app) as client:
        yield client, resolver, fetcher

    app.dependency_overrides.clear()


def _create(client: TestClient, base_url: str = "https://example.com") -> dict:
    resp = client.post("/targets", json={"name": "Example", "base_url": base_url})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_target_returns_instructions(ctx) -> None:
    client, _, _ = ctx
    body = _create(client)
    assert body["verified"] is False
    assert body["scope_hosts"] == ["example.com"]  # defaulted to the host
    v = body["verification"]
    assert v["dns_txt_record"] == expected_txt_record(v["token"])
    assert v["file_url"] == f"https://example.com{WELL_KNOWN_PATH}"


def test_create_target_rejects_non_http_url(ctx) -> None:
    client, _, _ = ctx
    resp = client.post("/targets", json={"name": "x", "base_url": "ftp://example.com"})
    assert resp.status_code == 422


def test_get_and_list_targets(ctx) -> None:
    client, _, _ = ctx
    created = _create(client)
    got = client.get(f"/targets/{created['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == created["id"]

    listed = client.get("/targets")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_get_missing_target_404(ctx) -> None:
    client, _, _ = ctx
    assert client.get("/targets/does-not-exist").status_code == 404


def test_verify_via_dns_flips_verified(ctx) -> None:
    client, resolver, _ = ctx
    created = _create(client)
    token = created["verification"]["token"]
    resolver.table["example.com"] = [expected_txt_record(token)]

    resp = client.post(f"/targets/{created['id']}/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["verified"] is True
    assert data["method"] == "dns"
    assert data["target"]["verified"] is True

    # Persisted: a fresh GET reflects the verified flag.
    assert client.get(f"/targets/{created['id']}").json()["verified"] is True


def test_verify_via_file_flips_verified(ctx) -> None:
    client, _, fetcher = ctx
    created = _create(client)
    token = created["verification"]["token"]
    fetcher.table[f"https://example.com{WELL_KNOWN_PATH}"] = token

    resp = client.post(f"/targets/{created['id']}/verify")
    assert resp.status_code == 200
    assert resp.json()["method"] == "file"


def test_verify_fails_when_no_proof(ctx) -> None:
    client, _, _ = ctx
    created = _create(client)
    resp = client.post(f"/targets/{created['id']}/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["verified"] is False
    assert data["method"] is None
    assert data["target"]["verified"] is False


def test_verify_missing_target_404(ctx) -> None:
    client, _, _ = ctx
    assert client.post("/targets/nope/verify").status_code == 404
