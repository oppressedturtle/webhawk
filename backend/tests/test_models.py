"""Model tests — exercised against an in-memory SQLite DB.

These verify the schema (tables, relationships, cascade, enum round-trip)
without needing a live Postgres instance.
"""

from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Finding, Scan, ScanStatus, Severity, Target


def make_session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_target_scan_finding_round_trip() -> None:
    session = make_session()
    target = Target(name="Example", base_url="https://example.com", scope_hosts=["example.com"])
    scan = Scan(target=target, requested_by="owner@example.com")
    finding = Finding(
        scan=scan,
        severity=Severity.HIGH,
        title="Missing CSP header",
        location="https://example.com/",
    )
    session.add(target)
    session.commit()

    loaded = session.execute(select(Target)).scalar_one()
    assert loaded.id is not None
    assert loaded.verification_token  # auto-populated
    assert loaded.verified is False
    assert loaded.scope_hosts == ["example.com"]
    assert len(loaded.scans) == 1
    assert loaded.scans[0].status is ScanStatus.QUEUED
    assert loaded.scans[0].findings[0].severity is Severity.HIGH
    assert finding.created_at is not None


def test_cascade_delete_removes_scans_and_findings() -> None:
    session = make_session()
    target = Target(name="T", base_url="https://t.example")
    scan = Scan(target=target)
    Finding(scan=scan, title="x")
    session.add(target)
    session.commit()

    session.delete(target)
    session.commit()

    assert session.execute(select(Scan)).first() is None
    assert session.execute(select(Finding)).first() is None


def test_severity_and_status_values() -> None:
    assert [s.value for s in Severity] == ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert ScanStatus.QUEUED.value == "QUEUED"
