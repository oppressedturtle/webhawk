"""SQLAlchemy ORM models for WebHawk.

Domain: a **Target** is an authorized site (ownership proven in Phase 1). A
**Scan** is one run against a target and moves through a status lifecycle. Each
scan produces zero or more **Findings** (the vulnerabilities/observations).

Everything here is defined up front so later phases (crawler, passive/active
checks, reporting) only add columns/relations rather than new core models.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class ScanStatus(enum.StrEnum):
    """Lifecycle of a scan job."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Severity(enum.StrEnum):
    """Finding severity, ordered low → high."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Target(Base):
    """An authorized scan target. Ownership verification lands in Phase 1."""

    __tablename__ = "targets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    base_url: Mapped[str] = mapped_column(String(2048))
    # Hosts/paths the scanner is permitted to touch (scope allowlist).
    scope_hosts: Mapped[list[str]] = mapped_column(JSON, default=list)
    # Path prefixes the scanner may touch (empty => any path on an in-scope host).
    scope_paths: Mapped[list[str]] = mapped_column(JSON, default=list)
    # Whether subdomains of the scope hosts are also in scope.
    allow_subdomains: Mapped[bool] = mapped_column(default=False)
    verified: Mapped[bool] = mapped_column(default=False)
    # Explicit authorization acknowledgement — the user affirmed they are
    # permitted to test this target. Required before registration succeeds.
    authorized: Mapped[bool] = mapped_column(default=False)
    authorized_by: Mapped[str | None] = mapped_column(String(255), default=None)
    authorized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    # Token the owner must publish (DNS TXT / served file) to prove control.
    verification_token: Mapped[str] = mapped_column(String(64), default=_uuid)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )

    scans: Mapped[list[Scan]] = relationship(
        back_populates="target",
        cascade="all, delete-orphan",
    )


class Scan(Base):
    """A single scan run against a target."""

    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    target_id: Mapped[str] = mapped_column(
        ForeignKey("targets.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[ScanStatus] = mapped_column(
        SAEnum(ScanStatus, name="scan_status"),
        default=ScanStatus.QUEUED,
        index=True,
    )
    # Identity that requested the scan (for the Phase 1 audit log).
    requested_by: Mapped[str | None] = mapped_column(String(255), default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    target: Mapped[Target] = relationship(back_populates="scans")
    findings: Mapped[list[Finding]] = relationship(
        back_populates="scan",
        cascade="all, delete-orphan",
    )


class Finding(Base):
    """A single vulnerability/observation produced by a scan."""

    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    scan_id: Mapped[str] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), index=True
    )
    severity: Mapped[Severity] = mapped_column(
        SAEnum(Severity, name="finding_severity"),
        default=Severity.INFO,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    # Where it was found (URL/path) and supporting evidence.
    location: Mapped[str | None] = mapped_column(String(2048), default=None)
    evidence: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )

    scan: Mapped[Scan] = relationship(back_populates="findings")
