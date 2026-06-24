# WebHawk backend — FastAPI API + scan worker share one image.
# Multi-stage: build a wheel-installed venv, then copy into a slim runtime.
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ---- builder: install the package + deps into an isolated venv ----
FROM base AS builder
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only what's needed to resolve and install dependencies first, so the
# dependency layer caches across source-only changes.
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install .

# ---- runtime: slim image, non-root, just the venv + app ----
FROM base AS runtime
WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH"

# Create an unprivileged user to run the API/worker.
RUN useradd --create-home --uid 10001 webhawk
COPY --from=builder /opt/venv /opt/venv
COPY app ./app
USER webhawk

EXPOSE 8000

# Default command runs the API; the worker service overrides this in compose.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
