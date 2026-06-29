"""Target ownership verification (Phase 1 item 1).

Before WebHawk will scan a target, the requester must prove they control it. We
support the two industry-standard methods:

- **DNS TXT record** — publish ``webhawk-site-verification=<token>`` as a TXT
  record on the target host.
- **Served file** — serve the raw token at
  ``/.well-known/webhawk-verification.txt`` over HTTP(S).

Either proof is sufficient. This guardrail is the whole point of an *authorized*
scanner, so the logic here is pure and the network is hidden behind small
:class:`TxtResolver` / :class:`FileFetcher` Protocols — the checks are fully
unit-testable offline, and the default implementations are injected at the edge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

#: TXT record value the owner must publish (prefix + the target's token).
TXT_RECORD_PREFIX = "webhawk-site-verification="

#: Path the owner must serve the raw token at.
WELL_KNOWN_PATH = "/.well-known/webhawk-verification.txt"


def expected_txt_record(token: str) -> str:
    """The exact TXT record value we look for."""
    return f"{TXT_RECORD_PREFIX}{token}"


def host_of(base_url: str) -> str | None:
    """Extract the lowercase hostname from a base URL, or ``None`` if absent."""
    host = urlsplit(base_url).hostname
    return host.lower() if host else None


def well_known_url(base_url: str) -> str | None:
    """Build the ``/.well-known`` verification URL for a base URL's origin."""
    parts = urlsplit(base_url)
    if not parts.scheme or not parts.netloc:
        return None
    return urlunsplit((parts.scheme, parts.netloc, WELL_KNOWN_PATH, "", ""))


# ---------------------------------------------------------------------------
# Network abstractions (injectable for tests)
# ---------------------------------------------------------------------------


class TxtResolver(Protocol):
    """Resolve the TXT records for a host (empty list when none / on failure)."""

    def resolve_txt(self, host: str) -> list[str]: ...


class FileFetcher(Protocol):
    """Fetch the body of a URL as text, or ``None`` if it can't be retrieved."""

    def fetch_text(self, url: str) -> str | None: ...


# ---------------------------------------------------------------------------
# Verification checks
# ---------------------------------------------------------------------------


def check_dns(host: str, token: str, resolver: TxtResolver) -> bool:
    """True if the host publishes the expected ``webhawk-site-verification`` TXT."""
    expected = expected_txt_record(token)
    try:
        records = resolver.resolve_txt(host)
    except Exception:  # noqa: BLE001 — any resolver error → not verified
        return False
    return any(record.strip() == expected for record in records)


def check_file(base_url: str, token: str, fetcher: FileFetcher) -> bool:
    """True if the target serves the raw token at the well-known path."""
    url = well_known_url(base_url)
    if url is None:
        return False
    try:
        body = fetcher.fetch_text(url)
    except Exception:  # noqa: BLE001 — any fetch error → not verified
        return False
    return body is not None and body.strip() == token


@dataclass(frozen=True)
class VerificationOutcome:
    """Result of an ownership check."""

    verified: bool
    method: str | None  # "dns" | "file" | None
    detail: str


def verify_ownership(
    base_url: str,
    token: str,
    *,
    resolver: TxtResolver,
    fetcher: FileFetcher,
) -> VerificationOutcome:
    """Attempt DNS then file verification; the first proof that holds wins."""
    host = host_of(base_url)
    if host is None:
        return VerificationOutcome(False, None, "Target base URL has no host to verify.")

    if check_dns(host, token, resolver):
        return VerificationOutcome(
            True, "dns", f"Verified via DNS TXT record on {host}."
        )

    if check_file(base_url, token, fetcher):
        return VerificationOutcome(
            True, "file", f"Verified via the file served at {WELL_KNOWN_PATH}."
        )

    return VerificationOutcome(
        False,
        None,
        "Neither the DNS TXT record nor the verification file was found. "
        "Publish one of them and retry.",
    )


# ---------------------------------------------------------------------------
# Default network-backed implementations (deps imported lazily)
# ---------------------------------------------------------------------------


class DnspythonTxtResolver:
    """:class:`TxtResolver` backed by ``dnspython`` with a bounded timeout."""

    def __init__(self, *, timeout: float = 5.0) -> None:
        self._timeout = timeout

    def resolve_txt(self, host: str) -> list[str]:
        import dns.exception  # lazy: keep the module importable without dnspython
        import dns.resolver

        resolver = dns.resolver.Resolver()
        resolver.lifetime = self._timeout
        resolver.timeout = self._timeout
        try:
            answers = resolver.resolve(host, "TXT")
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            return []
        except dns.exception.DNSException:
            return []
        # dnspython returns TXT as quoted byte chunks; join and decode each record.
        return [b"".join(rdata.strings).decode("utf-8", "replace") for rdata in answers]


class UrllibFileFetcher:
    """:class:`FileFetcher` using the stdlib ``urllib`` (no extra dependency).

    Bounds the response size and time so a hostile/large target can't exhaust us;
    the token is tiny, so a small cap is plenty.
    """

    def __init__(self, *, timeout: float = 8.0, max_bytes: int = 4096) -> None:
        self._timeout = timeout
        self._max_bytes = max_bytes

    def fetch_text(self, url: str) -> str | None:
        from urllib.error import URLError
        from urllib.request import Request, urlopen

        request = Request(url, headers={"User-Agent": "WebHawk-Verifier"})  # noqa: S310 (scheme checked)
        if not url.startswith(("http://", "https://")):
            return None
        try:
            with urlopen(request, timeout=self._timeout) as resp:  # noqa: S310
                raw: bytes = resp.read(self._max_bytes + 1)
        except (URLError, TimeoutError, ValueError, OSError):
            return None
        if len(raw) > self._max_bytes:
            return None
        return raw.decode("utf-8", "replace")
