"""Scope allowlist enforcement (Phase 1 item 2).

WebHawk is an *authorized* scanner: it must only ever touch hosts and paths the
user was permitted to test. This module is the single chokepoint that answers
"is this URL in scope?" — the crawler (Phase 2) and every passive/active check
(Phases 3–4) must consult it before issuing a request, so an in-scope decision
here is what keeps the scanner from wandering off the authorized target.

Design principles:

- **Fail closed.** Anything we can't confidently place in scope is rejected: a
  malformed URL, a non-http(s) scheme, a host not on the allowlist, or a path
  outside the permitted prefixes.
- **No accidental widening.** Host matching is exact by default; subdomains are
  only in scope when explicitly enabled, and even then a look-alike suffix
  (``evil-example.com`` vs ``example.com``) can never match because we compare on
  a dotted label boundary. Path prefixes match on a ``/`` boundary too, so
  ``/admin`` does not put ``/administrator`` in scope.
- **Pure & normalized.** Hosts are lowercased and IDNA-encoded so a unicode
  homograph can't smuggle a different host past the allowlist; the port never
  affects the host decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

ALLOWED_SCHEMES = frozenset({"http", "https"})


@dataclass(frozen=True)
class ScopeDecision:
    """Whether a URL is in scope, with a human-readable reason."""

    allowed: bool
    reason: str


def normalize_host(host: str) -> str | None:
    """Lowercase + IDNA-encode a host so allowlist checks see the real ASCII host.

    Returns ``None`` for an empty/unusable host.
    """
    cleaned = host.strip().rstrip(".").lower()
    if not cleaned:
        return None
    try:
        return cleaned.encode("idna").decode("ascii")
    except (UnicodeError, ValueError):
        # Already ASCII, or an IP literal / un-encodable host — use as-is.
        return cleaned


def normalize_path_prefix(prefix: str) -> str:
    """Normalize a path prefix to a leading-slash, no-trailing-slash form.

    ``""``/``"/"`` become ``"/"`` (root — matches everything). ``"admin/"``
    becomes ``"/admin"``.
    """
    p = prefix.strip()
    if not p.startswith("/"):
        p = "/" + p
    if len(p) > 1:
        p = p.rstrip("/") or "/"
    return p


def _path_matches(path: str, prefix: str) -> bool:
    """Does ``path`` fall under ``prefix`` on a path-segment boundary?"""
    if prefix == "/":
        return True
    path = path or "/"
    return path == prefix or path.startswith(prefix + "/")


@dataclass(frozen=True)
class ScopePolicy:
    """An immutable in/out-of-scope decision maker for one target."""

    hosts: frozenset[str]
    path_prefixes: tuple[str, ...] = ()  # empty => any path allowed
    allow_subdomains: bool = False

    @classmethod
    def from_target(
        cls,
        hosts: list[str],
        *,
        path_prefixes: list[str] | None = None,
        allow_subdomains: bool = False,
    ) -> ScopePolicy:
        """Build a policy from a target's raw allowlist, normalizing everything."""
        normed_hosts = frozenset(
            h for h in (normalize_host(x) for x in hosts) if h is not None
        )
        normed_paths = tuple(normalize_path_prefix(p) for p in (path_prefixes or []))
        # A root prefix makes all others redundant — collapse to "any path".
        if "/" in normed_paths:
            normed_paths = ()
        return cls(
            hosts=normed_hosts,
            path_prefixes=normed_paths,
            allow_subdomains=allow_subdomains,
        )

    def _host_in_scope(self, host: str) -> bool:
        if host in self.hosts:
            return True
        if self.allow_subdomains:
            # Match on a dotted boundary so "evil-example.com" != "example.com".
            return any(host.endswith("." + allowed) for allowed in self.hosts)
        return False

    def check(self, url: str) -> ScopeDecision:
        """Decide whether ``url`` is within this policy's authorized scope."""
        parts = urlsplit(url.strip())
        scheme = parts.scheme.lower()
        if scheme not in ALLOWED_SCHEMES:
            return ScopeDecision(False, f"Scheme '{parts.scheme or ''}' is not http(s).")

        raw_host = parts.hostname
        if not raw_host:
            return ScopeDecision(False, "URL has no host.")
        host = normalize_host(raw_host)
        if host is None:
            return ScopeDecision(False, "URL host could not be parsed.")

        if not self._host_in_scope(host):
            return ScopeDecision(False, f"Host '{host}' is not in the authorized scope.")

        if self.path_prefixes:
            path = parts.path or "/"
            if not any(_path_matches(path, pre) for pre in self.path_prefixes):
                return ScopeDecision(
                    False, f"Path '{path}' is outside the authorized path prefixes."
                )

        return ScopeDecision(True, "In scope.")

    def is_in_scope(self, url: str) -> bool:
        """Convenience boolean form of :meth:`check`."""
        return self.check(url).allowed
