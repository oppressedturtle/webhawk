# WebHawk — Roadmap

**Stack:** Python · FastAPI · React (Vite, TypeScript) · Postgres · Redis + worker queue (RQ/Celery) · Docker
**Goal:** Production-grade **authorized** web-application vulnerability scanner (OWASP Top 10). Crawl a target you own/are permitted to test, run safe passive + active checks, produce a clear report with severity, evidence, and remediation. Portfolio-quality: tested, containerized, CI'd, deploy-ready.
**Repo visibility:** public — Yanis's portfolio.

> **Authorized testing only — enforced in the product.** Before any scan, the user must confirm authorization AND prove control of the target (DNS TXT token or a served verification file). Scans are scope-limited (allowlist), rate-limited/gentle, and default to **non-destructive** checks. This guardrail is a feature, not an afterthought.

Each roadmap item is a self-contained increment completed in one session, then committed + pushed. Work in order; skip ahead only if blocked.

## Phase 0 — Foundation
- [x] FastAPI backend + React (Vite/TS) dashboard skeletons
- [x] Postgres (targets, scans, findings), Redis + worker queue for async scans
- [x] Docker Compose (api + worker + web + postgres + redis), Dockerfiles, CI stub
- [x] README, MIT LICENSE, .gitignore

## Phase 1 — Authorization & scope (guardrail first)
- [x] Target registration + ownership verification (DNS TXT token / served file) _(`app/verification.py` + `app/api/targets.py`: register a target → get a token + DNS-TXT and well-known-file instructions; `/targets/{id}/verify` proves control via either method (network behind injectable `TxtResolver`/`FileFetcher` Protocols; dnspython + stdlib-urllib defaults) and flips `verified`. 21 offline tests)_
- [ ] Explicit authorization acknowledgement, scope allowlist (hosts/paths), global rate limit _(**authorization ack + scope allowlist done**: registration now refuses unless the caller confirms `authorized:true` (recorded with who/when); `app/scope.py` `ScopePolicy` is the fail-closed in/out-of-scope engine — exact-host + opt-in subdomain (dot-boundary, no look-alike), path-prefix boundary matching, http(s)-only, IDNA-normalized — surfaced via `GET /targets/{id}/scope-check`; 13 scope + API tests. **Remaining: global rate limit.**)_
- [ ] Audit log of who scanned what, when

## Phase 2 — Crawler / spider
- [ ] Scoped crawler: respect scope allowlist, robots awareness, depth/rate limits
- [ ] Form + input + endpoint discovery, session/cookie handling, sitemap parsing

## Phase 3 — Passive checks (non-intrusive)
- [ ] Security headers (CSP, HSTS, X-Frame-Options, etc.), cookie flags (HttpOnly/Secure/SameSite)
- [ ] TLS/cert config, server/tech banners + known-version flags
- [ ] CORS misconfig, mixed content, info disclosure, directory listing, sensitive-file exposure

## Phase 4 — Active checks (safe, non-destructive)
- [ ] Reflected XSS (benign markers), open redirect, clickjacking
- [ ] CSRF token presence/validation checks
- [ ] SQLi detection via boolean/error-based **safe** probes (no data modification)
- [ ] Rate-limited, cancellable, with clear "what was sent" evidence

## Phase 5 — Reporting
- [ ] Findings model: severity (CVSS-style), evidence (request/response), OWASP refs, remediation
- [ ] Report UI + export (JSON, PDF), false-positive marking, scan diffing across runs

## Phase 6 — Scan management & UX
- [ ] Scheduled scans, scan history, live progress, cancel
- [ ] Auth (users), API keys, dashboard polish, accessibility

## Phase 7 — Hardening & Tests
- [ ] Unit/integration tests incl. scope-enforcement + authorization-gate tests
- [ ] Test target app (intentionally vulnerable sandbox) for E2E scanning
- [ ] GitHub Actions CI: lint, typecheck, pytest, build

## Phase 8 — Deploy-Ready
- [ ] Multi-stage builds, env docs, deploy guide, polished README w/ screenshots + architecture

## SECURITY PHASE
Audit the scanner itself: ensure scope/authorization cannot be bypassed, no SSRF beyond authorized scope, safe handling of target responses, dependency CVEs, secrets, authz on the API, worker isolation. Document in `SECURITY.md`.

## QA PHASE
Stand up the vulnerable test target, run a full scan, verify findings are accurate (low false positives), confirm scope + authorization gates block out-of-scope/unverified targets. Log in `PROGRESS.md`.

## SHIP PHASE
Push final commits/tags to the **public** repo, verify CI, tag `v1.0.0`, notify Yanis.
