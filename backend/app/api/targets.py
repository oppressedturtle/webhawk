"""Target registration + ownership-verification endpoints (Phase 1 item 1).

A target must be registered and then *verified* (proof of control) before any
scan can run against it. Registration hands back the token plus instructions for
both verification methods; ``/verify`` runs the check and flips ``verified`` on
success. Scans (added later) will refuse to start on an unverified target.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import AnyHttpUrl, BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Target
from app.scope import ScopePolicy
from app.verification import (
    WELL_KNOWN_PATH,
    DnspythonTxtResolver,
    FileFetcher,
    TxtResolver,
    UrllibFileFetcher,
    VerificationOutcome,
    expected_txt_record,
    host_of,
    verify_ownership,
    well_known_url,
)

router = APIRouter(prefix="/targets", tags=["targets"])


# --- dependency providers (overridable in tests) ---------------------------


def get_txt_resolver() -> TxtResolver:
    return DnspythonTxtResolver()


def get_file_fetcher() -> FileFetcher:
    return UrllibFileFetcher()


SessionDep = Annotated[Session, Depends(get_session)]
ResolverDep = Annotated[TxtResolver, Depends(get_txt_resolver)]
FetcherDep = Annotated[FileFetcher, Depends(get_file_fetcher)]


# --- schemas ---------------------------------------------------------------


class TargetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    base_url: AnyHttpUrl
    scope_hosts: list[str] = Field(default_factory=list)
    scope_paths: list[str] = Field(default_factory=list)
    allow_subdomains: bool = False
    # The user must explicitly confirm authorization to test this target.
    # Registration is refused unless this is true (the guardrail is a feature).
    authorized: bool = Field(
        description="You must confirm you are authorized to scan this target."
    )
    authorized_by: str | None = Field(default=None, max_length=255)


class VerificationInstructions(BaseModel):
    token: str
    dns_txt_record: str
    file_path: str
    file_url: str | None


class TargetOut(BaseModel):
    id: str
    name: str
    base_url: str
    scope_hosts: list[str]
    scope_paths: list[str]
    allow_subdomains: bool
    verified: bool
    authorized: bool
    authorized_by: str | None
    verification: VerificationInstructions


class ScopeCheckResult(BaseModel):
    url: str
    in_scope: bool
    reason: str


class VerifyResult(BaseModel):
    verified: bool
    method: str | None
    detail: str
    target: TargetOut


def _to_out(target: Target) -> TargetOut:
    return TargetOut(
        id=target.id,
        name=target.name,
        base_url=target.base_url,
        scope_hosts=target.scope_hosts,
        scope_paths=target.scope_paths,
        allow_subdomains=target.allow_subdomains,
        verified=target.verified,
        authorized=target.authorized,
        authorized_by=target.authorized_by,
        verification=VerificationInstructions(
            token=target.verification_token,
            dns_txt_record=expected_txt_record(target.verification_token),
            file_path=WELL_KNOWN_PATH,
            file_url=well_known_url(target.base_url),
        ),
    )


def _get_or_404(session: Session, target_id: str) -> Target:
    target = session.get(Target, target_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found.")
    return target


# --- endpoints -------------------------------------------------------------


@router.post("", response_model=TargetOut, status_code=status.HTTP_201_CREATED)
def create_target(body: TargetCreate, session: SessionDep) -> TargetOut:
    """Register a target. Returns the token + how to prove ownership.

    Refuses registration unless the caller explicitly acknowledges authorization
    (``authorized: true``) — the affirmation is recorded with a timestamp.
    """
    if not body.authorized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must confirm you are authorized to scan this target.",
        )

    base_url = str(body.base_url)
    host = host_of(base_url)
    if host is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid base URL."
        )

    # Default the scope allowlist to the target's own host when none is supplied.
    scope = body.scope_hosts or [host]

    target = Target(
        name=body.name,
        base_url=base_url,
        scope_hosts=scope,
        scope_paths=body.scope_paths,
        allow_subdomains=body.allow_subdomains,
        authorized=True,
        authorized_by=body.authorized_by,
        authorized_at=datetime.now(UTC),
    )
    session.add(target)
    session.commit()
    session.refresh(target)
    return _to_out(target)


@router.get("/{target_id}/scope-check", response_model=ScopeCheckResult)
def scope_check(target_id: str, url: str, session: SessionDep) -> ScopeCheckResult:
    """Report whether ``url`` falls within a target's authorized scope.

    Consulted by the UI (and, later, every crawler/check) before touching a URL.
    """
    target = _get_or_404(session, target_id)
    policy = ScopePolicy.from_target(
        target.scope_hosts,
        path_prefixes=target.scope_paths,
        allow_subdomains=target.allow_subdomains,
    )
    decision = policy.check(url)
    return ScopeCheckResult(url=url, in_scope=decision.allowed, reason=decision.reason)


@router.get("", response_model=list[TargetOut])
def list_targets(session: SessionDep) -> list[TargetOut]:
    """List all registered targets, newest first."""
    targets = session.execute(select(Target).order_by(Target.created_at.desc())).scalars().all()
    return [_to_out(t) for t in targets]


@router.get("/{target_id}", response_model=TargetOut)
def get_target(target_id: str, session: SessionDep) -> TargetOut:
    """Fetch a single target."""
    return _to_out(_get_or_404(session, target_id))


@router.post("/{target_id}/verify", response_model=VerifyResult)
def verify_target(
    target_id: str,
    session: SessionDep,
    resolver: ResolverDep,
    fetcher: FetcherDep,
) -> VerifyResult:
    """Run ownership verification (DNS then file). Flips ``verified`` on success."""
    target = _get_or_404(session, target_id)

    outcome: VerificationOutcome = verify_ownership(
        target.base_url,
        target.verification_token,
        resolver=resolver,
        fetcher=fetcher,
    )

    if outcome.verified and not target.verified:
        target.verified = True
        session.commit()
        session.refresh(target)

    return VerifyResult(
        verified=outcome.verified,
        method=outcome.method,
        detail=outcome.detail,
        target=_to_out(target),
    )
