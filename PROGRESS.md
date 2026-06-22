# WebHawk — Progress Log

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
