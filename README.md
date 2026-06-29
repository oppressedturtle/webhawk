# WebHawk 🦅

An **authorized** web-application vulnerability scanner. Point it at a site you own or are permitted to test; WebHawk crawls it, runs OWASP Top 10 checks, and hands you a clear report with severity, evidence, and remediation.

> Portfolio project, work in progress. **Authorized testing only** — enforced by the product (see below).

## Responsible-use guardrail (built in)

Before any scan you must (1) acknowledge authorization and (2) **prove control** of the target via a DNS TXT token or a served verification file. Scans are scope-limited to an allowlist, rate-limited to stay gentle, and default to **non-destructive** checks. Every scan is logged. This guardrail is the first feature built (Phase 1), not an afterthought.

## Checks

- **Passive** — security headers, cookie flags, TLS config, CORS, mixed content, info disclosure, directory listing, sensitive files, tech/version flags
- **Active (safe)** — reflected XSS, open redirect, clickjacking, CSRF token checks, boolean/error-based SQLi probes (no data modification)
- **Reporting** — CVSS-style severity, request/response evidence, OWASP references, remediation, JSON/PDF export, scan diffing

## Architecture

```
            ┌──────────────┐        ┌──────────────┐
 browser ──▶│  web (nginx) │──/api──▶│  api (FastAPI)│──▶ postgres
            │  React/Vite  │        └──────┬───────┘     (targets,
            └──────────────┘               │              scans,
                                     enqueue│ scan job     findings)
                                           ▼
                                    ┌──────────────┐
                                    │  redis queue │
                                    └──────┬───────┘
                                           │ dequeue
                                           ▼
                                    ┌──────────────┐
                                    │    worker    │──▶ runs the scan,
                                    │  (app.worker)│     writes findings
                                    └──────────────┘
```

- **api** — FastAPI service: target registration, authorization/scope gates, scan orchestration, results API.
- **worker** — pulls scan jobs off the Redis queue and runs crawler + checks out-of-band so the API stays responsive.
- **web** — React (Vite/TS) dashboard, built to static assets and served by nginx, which reverse-proxies `/api/*` to the API (same-origin, no CORS in the browser).
- **postgres** — targets, scans, findings. **redis** — async job queue (and future rate-limit state).

## Quick start

Requires Docker + Docker Compose.

```bash
git clone https://github.com/oppressedturtle/webhawk.git
cd webhawk
docker compose up --build
```

- Dashboard → http://localhost:8080
- API + docs → http://localhost:8000 (`/health`, `/docs`)

Ports are env-overridable (`WEB_PORT`, `API_PORT`, `POSTGRES_PORT`, `REDIS_PORT`).

### Local development

```bash
# Backend (FastAPI + worker)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
ruff check app && mypy app && pytest
uvicorn app.main:app --reload          # API on :8000
python -m app.worker                   # worker (separate shell)

# Frontend
cd web
npm install
npm run lint && npm run typecheck && npm test && npm run build
npm run dev                            # Vite dev server
```

## Project layout

```
backend/
  app/
    api/         FastAPI routers (health, …)
    core/        logging, Redis queue helpers
    config.py    env-driven settings (WEBHAWK_* vars)
    db.py        SQLAlchemy engine/session
    models.py    targets, scans, findings
    main.py      app factory
    worker.py    queue consumer
  tests/         pytest suite
web/
  src/           React dashboard (Vite + TS)
  nginx.conf     static serving + /api reverse proxy
docker-compose.yml   full stack: postgres + redis + api + worker + web
.github/workflows/   CI: backend (ruff/mypy/pytest) + web (lint/typecheck/test/build) + docker buildx
```

## Status

See [`ROADMAP.md`](./ROADMAP.md) and [`PROGRESS.md`](./PROGRESS.md).

## License

MIT — see [`LICENSE`](./LICENSE).
