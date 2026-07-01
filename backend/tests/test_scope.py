"""Unit tests for the scope allowlist enforcement engine (Phase 1 item 2).

Pure logic, no network — this is the guardrail that keeps the scanner on the
authorized target, so the boundary/fail-closed behaviour is tested carefully.
"""

from __future__ import annotations

from app.scope import (
    ScopePolicy,
    normalize_host,
    normalize_path_prefix,
)


def test_exact_host_in_scope():
    policy = ScopePolicy.from_target(["example.com"])
    assert policy.is_in_scope("https://example.com/anything")
    assert policy.is_in_scope("http://example.com")  # scheme + no path ok
    # port must not affect the host decision
    assert policy.is_in_scope("https://example.com:8443/x")


def test_other_host_rejected():
    policy = ScopePolicy.from_target(["example.com"])
    d = policy.check("https://other.com/")
    assert d.allowed is False
    assert "not in the authorized scope" in d.reason


def test_subdomain_only_when_enabled():
    strict = ScopePolicy.from_target(["example.com"])
    assert not strict.is_in_scope("https://app.example.com/")

    loose = ScopePolicy.from_target(["example.com"], allow_subdomains=True)
    assert loose.is_in_scope("https://app.example.com/")
    assert loose.is_in_scope("https://deep.app.example.com/")
    assert loose.is_in_scope("https://example.com/")  # apex still in scope


def test_lookalike_suffix_never_matches():
    loose = ScopePolicy.from_target(["example.com"], allow_subdomains=True)
    # A look-alike that merely ends with the string but not on a dot boundary.
    assert not loose.is_in_scope("https://evil-example.com/")
    assert not loose.is_in_scope("https://notexample.com/")


def test_scheme_must_be_http_s():
    policy = ScopePolicy.from_target(["example.com"])
    for url in [
        "ftp://example.com/",
        "file:///etc/passwd",
        "gopher://example.com/",
        "javascript:alert(1)",
    ]:
        d = policy.check(url)
        assert d.allowed is False
        assert "http(s)" in d.reason


def test_malformed_url_fails_closed():
    policy = ScopePolicy.from_target(["example.com"])
    assert not policy.is_in_scope("not a url")
    assert not policy.is_in_scope("https:///nohost")
    assert not policy.is_in_scope("")


def test_path_prefix_boundary():
    policy = ScopePolicy.from_target(["example.com"], path_prefixes=["/app"])
    assert policy.is_in_scope("https://example.com/app")
    assert policy.is_in_scope("https://example.com/app/users")
    # boundary: /app must not put /application in scope
    assert not policy.is_in_scope("https://example.com/application")
    d = policy.check("https://example.com/other")
    assert d.allowed is False
    assert "outside the authorized path prefixes" in d.reason


def test_multiple_path_prefixes():
    policy = ScopePolicy.from_target(["example.com"], path_prefixes=["/a", "/b/c"])
    assert policy.is_in_scope("https://example.com/a/x")
    assert policy.is_in_scope("https://example.com/b/c/deep")
    assert not policy.is_in_scope("https://example.com/b/other")


def test_root_prefix_allows_any_path_and_collapses_others():
    policy = ScopePolicy.from_target(["example.com"], path_prefixes=["/", "/ignored"])
    assert policy.path_prefixes == ()  # root collapses the list
    assert policy.is_in_scope("https://example.com/literally/anything")


def test_no_prefixes_allows_any_path():
    policy = ScopePolicy.from_target(["example.com"])
    assert policy.is_in_scope("https://example.com/deep/nested/path?q=1")


def test_host_normalization_case_and_idna():
    policy = ScopePolicy.from_target(["EXAMPLE.com"])
    assert policy.is_in_scope("https://Example.COM/")
    # trailing dot (FQDN root) is normalized away
    assert policy.is_in_scope("https://example.com./")


def test_normalize_helpers():
    assert normalize_host("  EXAMPLE.com.  ") == "example.com"
    assert normalize_host("") is None
    assert normalize_path_prefix("admin/") == "/admin"
    assert normalize_path_prefix("") == "/"
    assert normalize_path_prefix("/") == "/"
    assert normalize_path_prefix("/a/b/") == "/a/b"


def test_from_target_ignores_empty_hosts():
    policy = ScopePolicy.from_target(["", "example.com", "  "])
    assert policy.hosts == frozenset({"example.com"})
