################################################################################
# Firomsa AI Secretary — Backend Dockerfile
################################################################################

# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools for native C-extensions (asyncpg, cryptg)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy backend source code
COPY . .

# Switch to non-root user
USER appuser

ENV PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE ${PORT}

# ── Entrypoint ────────────────────────────────────────────────────────────────
# 1. Runs reset_db.py to clear stuck 'alembic_version' (phase4) table safely
# 2. Applies database migrations (alembic upgrade head)
# 3. Starts FastAPI app via Uvicorn
CMD ["sh", "-c", "python3 reset_db.py || true; alembic upgrade head || true; uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
