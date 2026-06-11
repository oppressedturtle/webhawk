# WebHawk — Backend (FastAPI)

The API server for WebHawk, an **authorized** web-application vulnerability
scanner. This package currently provides the application skeleton: typed
settings, structured logging, an app factory, and health/OpenAPI surfaces.
Datastores, the authorization/scope guardrails, crawler, and checks land in
later phases (see `../ROADMAP.md`).

## Requirements

- Python 3.11+

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # optional; sensible defaults are built in
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
# Health:  http://localhost:8000/health
# Docs:    http://localhost:8000/docs
```

## Quality gates

```bash
pytest          # tests
ruff check .    # lint
mypy app        # type-check (strict)
```

## Layout

```
app/
  main.py          # create_app() factory + ASGI `app`
  config.py        # pydantic-settings (WEBHAWK_* env vars)
  api/health.py    # /health liveness + version/uptime
  core/logging.py  # structured logging setup
tests/             # pytest suite
```
