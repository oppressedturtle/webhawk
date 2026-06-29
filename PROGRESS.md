# WebHawk — Progress Log

## 2026-06-29 — Phase 0 item 4: finalize root README (closes Phase 0)

Brought the root `README.md` up to the portfolio bar to **close Phase 0**: added an ASCII
**architecture diagram** (web→api→redis queue→worker→postgres), per-service responsibilities,
a **quick start** (`docker compose up --build`; dashboard :8080, API :8000, env-overridable
ports), a **local development** section (backend venv + `pip install -e '.[dev]'` + ruff/mypy/
pytest + uvicorn/worker; web npm lint/typecheck/test/build/dev — all verified against the actual
`pyproject.toml` optional-deps and compose service names/ports), and a **project layout** tree.
LICENSE (MIT) + `.gitignore` were already in place.

Docs-only change (no code touched). **Roadmap: Phase 0 complete (4/4).** **Next:** Phase 1 item 1
— the authorization guardrail: target registration + ownership verification (DNS TXT token /
served file) before any scan can run.


## 2026-06-24 — Phase 0 item 3: Docker Compose + Dockerfiles + CI

Containerised the whole stack and wired up CI so every push is gated.

- **`backend/Dockerfile`** — multi-stage (venv builder → slim `python:3.12-slim` runtime),
  non-root `webhawk` user, `pip install .`. One image serves both the **API**
  (`uvicorn app.main:app`) and the **worker** (compose overrides CMD with `python -m app.worker`).
- **`web/Dockerfile`** — Node build of the Vite bundle → **nginx** runtime. `web/nginx.conf`
  serves the SPA (history fallback) and reverse-proxies `/api/*` → `api:8000` with prefix strip,
  mirroring the Vite dev proxy so the browser stays **same-origin** (no CORS in the container).
- **`docker-compose.yml`** — `postgres` + `redis` + `api` + `worker` + `web`, healthchecks,
  `depends_on: service_healthy` gating, named volume, env-overridable host ports (web on :8080).
  Backend env uses the `WEBHAWK_` prefix (DATABASE_URL/REDIS_URL). `docker compose config` ✓.
- **`.github/workflows/ci.yml`** — three jobs, concurrency cancel-in-progress:
  **backend** (ruff → mypy strict → pytest), **web** (lint → typecheck → vitest → build),
  **docker** (buildx build of both images with GHA cache, gated on the first two).
- `+ backend/.dockerignore`, `+ web/.dockerignore` to keep build contexts lean.

**Verification (all green, locally):** backend `ruff` ✓ · `mypy app` (strict) ✓ · `pytest` 9/9 ✓;
web `eslint` ✓ · `vite build` ✓; `docker compose config` ✓. (Image builds run in CI — no local
Docker daemon this run.)

**Roadmap:** Phase 0 — 3/4 (item 3 ✅). **Next:** Phase 0 item 4 — finalize the root README
(architecture + one-command compose quick start) to close Phase 0, then Phase 1 (the
authorization/scope guardrail — ownership verification + scope allowlist + audit log).

## 2026-06-22 — Phase 0 item 2: Postgres data layer + Redis worker queue (backend)

**Done:** completed Phase 0 item 2 — the persistence + async-scan hand-off foundation.

- **`app/db.py`** — SQLAlchemy 2.0 `DeclarativeBase`, lazily-created engine + session factory
  (`lru_cache`, `pool_pre_ping`) and a `get_session()` FastAPI dependency. Engine is built on
  first use so the app/tests construct without a live DB.
- **`app/models.py`** — ORM models for the full scan domain: `Target` (authorized site, scope
  allowlist, `verified` + `verification_token` for Phase-1 ownership proof) → `Scan` (status
  lifecycle: QUEUED/RUNNING/COMPLETED/FAILED/CANCELLED, `requested_by` for the audit log) →
  `Finding` (Severity INFO→CRITICAL, title/location/evidence). Cascade deletes + indexes on
  FKs, status and severity. Enums modelled as `StrEnum`.
- **`app/core/queue.py`** — `ScanQueue`: Redis-list FIFO (`RPUSH`/`BLPOP`) carrying a typed
  `ScanJob` (scan_id + target_id, JSON-serialised). Accepts an injected client (testable),
  lazily builds a real one from settings otherwise. `enqueue`/`dequeue`/`depth`.
- **`app/worker.py`** — separate worker entry point (`python -m app.worker`): blocking consume
  loop with SIGINT/SIGTERM graceful shutdown, per-job exception isolation, and a `max_jobs`
  hook for deterministic tests. `process_job` is the placeholder the Phase 2–4 scan pipeline
  fills in.
- **Tests:** `test_models.py` (round-trip + cascade delete + enum values against in-memory
  SQLite) and `test_queue.py` (job JSON round-trip, FIFO order, worker drains the queue via a
  fake Redis). Added deps: `sqlalchemy`, `psycopg[binary]`, `redis`.
- **Verified:** pytest **9/9**, ruff clean, mypy strict clean (11 files). No live infra needed.
- **Roadmap:** Phase 0 — 2/4.
- **Next:** Phase 0 item 3 — Docker Compose (api + worker + web + postgres + redis), Dockerfiles, CI stub.

## 2026-06-15 — Phase 0: React (Vite/TS) dashboard skeleton

**Done:** completed Phase 0 item 1 (skeletons) by building the front end on top of the
existing untracked Vite/TS config scaffold.

- **`web/src/api.ts`** — typed backend client: `Health` interface mirroring the FastAPI
  `HealthResponse`, an `ApiError` (carries HTTP status; status `0` = network failure),
  and `getHealth(signal)` over the `/api` base (Vite proxies `/api/*` → FastAPI :8000).
- **`web/src/App.tsx`** — dashboard shell with a discriminated `Status` union
  (loading | ok | error). Fetches health on mount via `AbortController`, renders
  status/version/uptime, and shows a friendly "Cannot reach the backend" + Retry on
  failure. Includes the authorized-testing-only footer (product guardrail messaging).
- **`web/src/main.tsx`** (React 18 `createRoot`, StrictMode, null-root guard),
  **`index.css`** (dark/light theme tokens), **`test/setup.ts`** (jest-dom + cleanup).
- **`web/src/App.test.tsx`** — 3 tests: renders health, network-down message, API-error
  message. **`.eslintrc.cjs`** added; `@types/node` + `"node"` in tsconfig types so
  `vite.config.ts` typechecks.
- Ignored `.ruff_cache/` (was untracked).

**Verification (all green):** `tsc --noEmit` clean · `eslint . --max-warnings 0` clean ·
`vitest run` 3/3 · `vite build` succeeds (32 modules, 46.75 kB gzip JS).

**Roadmap:** Phase 0 item 1 ✅. **Next:** Phase 0 item 2 — Postgres (targets/scans/findings)
+ Redis + worker queue; then Docker Compose (api+worker+web+postgres+redis).


## 2026-06-11 — Phase 0: FastAPI backend skeleton

**Done:**
- Stood up the `backend/` package (Python 3.11+, `pyproject.toml` with
  fastapi/uvicorn/pydantic + dev tools ruff/mypy/pytest).
- `app/config.py`: typed `pydantic-settings` (`WEBHAWK_*` env prefix, `.env`
  support, cached `get_settings()`), incl. placeholders for Postgres/Redis URLs
  wired up next.
- `app/core/logging.py`: dependency-free structured logging (idempotent setup).
- `app/main.py`: `create_app()` factory with CORS for the dashboard + OpenAPI
  docs; `app/api/health.py` exposes `/health` (status/version/uptime).
- Tests (pytest + TestClient): health 200, OpenAPI served, env-prefix settings —
  3/3 passing. `ruff check` clean, `mypy --strict` clean.
- Backend `README.md` + `.env.example`.

**Roadmap:** Phase 0 item 1 — backend half done (React/Vite dashboard skeleton
is the remaining half).

**Next:** React (Vite/TS) dashboard skeleton, then Postgres+Prisma… (Postgres
models + Redis worker queue), then Docker Compose for the full stack.

## 2026-06-08 — Project kickoff
- Added to the autonomous build pipeline (security project, builds in rotation).
- Defined 8-phase roadmap. Authorization + scope verification is Phase 1 — the responsible-use guardrail is a core feature.
- Foundation committed: README, MIT LICENSE, .gitignore. Public repo created.
- **Next:** Phase 0 — FastAPI backend + React dashboard, Postgres, Redis worker queue, Docker Compose.
