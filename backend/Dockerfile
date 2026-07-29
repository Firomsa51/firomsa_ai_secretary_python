################################################################################
# Firomsa AI Secretary — Dockerfile
# Target: Render worker service (or any OCI-compatible runtime)
################################################################################

# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools needed for native dependencies (cryptg, asyncpg)
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

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Switch to non-root user
USER appuser

# ── Environment defaults (overridden at runtime) ───────────────────────────────
ENV PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE ${PORT}

# ── Entrypoint ────────────────────────────────────────────────────────────────
# 1. Force stamp database to head_baseline (clears stuck 'phase4' revision)
# 2. Run alembic upgrade head
# 3. Start Uvicorn API server
CMD ["sh", "-c", "alembic stamp head_baseline || alembic -c backend/alembic.ini stamp head_baseline || true; alembic upgrade head || alembic -c backend/alembic.ini upgrade head; uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
