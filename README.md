# WebHawk 🦅

An **authorized** web-application vulnerability scanner. Point it at a site you own or are permitted to test; WebHawk crawls it, runs OWASP Top 10 checks, and hands you a clear report with severity, evidence, and remediation.

> Portfolio project, work in progress. **Authorized testing only** — enforced by the product (see below).

## Responsible-use guardrail (built in)
Before any scan you must (1) acknowledge authorization and (2) **prove control** of the target via a DNS TXT token or a served verification file. Scans are scope-limited to an allowlist, rate-limited to stay gentle, and default to **non-destructive** checks. Every scan is logged.

## Checks
- **Passive** — security headers, cookie flags, TLS config, CORS, mixed content, info disclosure, directory listing, sensitive files, tech/version flags
- **Active (safe)** — reflected XSS, open redirect, clickjacking, CSRF token checks, boolean/error-based SQLi probes (no data modification)
- **Reporting** — CVSS-style severity, request/response evidence, OWASP references, remediation, JSON/PDF export, scan diffing

## Stack
Python · FastAPI · React (Vite/TS) · Postgres · Redis + worker queue · Docker · GitHub Actions

## Status
See [`ROADMAP.md`](./ROADMAP.md) and [`PROGRESS.md`](./PROGRESS.md).

## License
MIT — see [`LICENSE`](./LICENSE).
