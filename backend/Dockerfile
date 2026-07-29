################################################################################
# Firomsa AI Secretary — Dockerfile
# Target: Render worker/web service (OCI-compatible runtime)
################################################################################

# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Build tools dependencies needed for native C-extensions (cryptg, asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source code
COPY . .

# Switch to non-root user
USER appuser

# ── Environment defaults ───────────────────────────────────────────────────────
ENV PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE ${PORT}

# ── Entrypoint ────────────────────────────────────────────────────────────────
# Runs database migrations gracefully and starts the Uvicorn FastAPI server
CMD ["sh", "-c", "alembic upgrade head || true; uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
