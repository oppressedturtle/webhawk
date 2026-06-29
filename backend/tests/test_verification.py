"""Tests for ownership-verification logic — all network is faked (offline)."""

from __future__ import annotations

from app.verification import (
    WELL_KNOWN_PATH,
    check_dns,
    check_file,
    expected_txt_record,
    host_of,
    verify_ownership,
    well_known_url,
)

TOKEN = "abc123-token"


class FakeResolver:
    def __init__(self, table: dict[str, list[str]], fail: set[str] | None = None):
        self._table = table
        self._fail = fail or set()

    def resolve_txt(self, host: str) -> list[str]:
        if host in self._fail:
            raise RuntimeError("simulated DNS failure")
        return self._table.get(host, [])


class FakeFetcher:
    def __init__(self, table: dict[str, str | None], fail: set[str] | None = None):
        self._table = table
        self._fail = fail or set()

    def fetch_text(self, url: str) -> str | None:
        if url in self._fail:
            raise RuntimeError("simulated fetch failure")
        return self._table.get(url)


# --- helpers ---------------------------------------------------------------


def test_expected_txt_record():
    assert expected_txt_record(TOKEN) == "webhawk-site-verification=abc123-token"


def test_host_of():
    assert host_of("https://Example.com/path") == "example.com"
    assert host_of("not a url") is None


def test_well_known_url():
    assert well_known_url("https://example.com/anything") == f"https://example.com{WELL_KNOWN_PATH}"
    assert well_known_url("bogus") is None


# --- DNS check -------------------------------------------------------------


def test_check_dns_matches_record():
    resolver = FakeResolver({"example.com": ["unrelated", expected_txt_record(TOKEN)]})
    assert check_dns("example.com", TOKEN, resolver) is True


def test_check_dns_no_match():
    resolver = FakeResolver({"example.com": ["webhawk-site-verification=wrong"]})
    assert check_dns("example.com", TOKEN, resolver) is False


def test_check_dns_swallows_resolver_error():
    resolver = FakeResolver({}, fail={"example.com"})
    assert check_dns("example.com", TOKEN, resolver) is False


# --- file check ------------------------------------------------------------


def test_check_file_matches_body():
    url = f"https://example.com{WELL_KNOWN_PATH}"
    fetcher = FakeFetcher({url: f"  {TOKEN}\n"})  # whitespace tolerated
    assert check_file("https://example.com", TOKEN, fetcher) is True


def test_check_file_wrong_body():
    url = f"https://example.com{WELL_KNOWN_PATH}"
    fetcher = FakeFetcher({url: "nope"})
    assert check_file("https://example.com", TOKEN, fetcher) is False


def test_check_file_swallows_fetch_error():
    url = f"https://example.com{WELL_KNOWN_PATH}"
    fetcher = FakeFetcher({}, fail={url})
    assert check_file("https://example.com", TOKEN, fetcher) is False


# --- combined orchestration ------------------------------------------------


def _no_dns() -> FakeResolver:
    return FakeResolver({})


def _no_file() -> FakeFetcher:
    return FakeFetcher({})


def test_verify_ownership_via_dns():
    resolver = FakeResolver({"example.com": [expected_txt_record(TOKEN)]})
    outcome = verify_ownership("https://example.com", TOKEN, resolver=resolver, fetcher=_no_file())
    assert outcome.verified is True
    assert outcome.method == "dns"


def test_verify_ownership_via_file():
    url = f"https://example.com{WELL_KNOWN_PATH}"
    fetcher = FakeFetcher({url: TOKEN})
    outcome = verify_ownership("https://example.com", TOKEN, resolver=_no_dns(), fetcher=fetcher)
    assert outcome.verified is True
    assert outcome.method == "file"


def test_verify_ownership_fails_when_neither_present():
    outcome = verify_ownership("https://example.com", TOKEN, resolver=_no_dns(), fetcher=_no_file())
    assert outcome.verified is False
    assert outcome.method is None


def test_verify_ownership_no_host():
    outcome = verify_ownership("not-a-url", TOKEN, resolver=_no_dns(), fetcher=_no_file())
    assert outcome.verified is False
    assert "no host" in outcome.detail.lower()
