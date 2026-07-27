################################################################################
# Firomsa AI Secretary — Dockerfile
# Target: Render worker service (or any OCI-compatible runtime)
################################################################################

# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools needed for some native dependencies (cryptg, asyncpg)
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

# Ensure migrations directory is present
RUN mkdir -p migrations/versions

# Switch to non-root user
USER appuser

# ── Environment defaults (overridden at runtime) ───────────────────────────────
ENV PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE ${PORT}

# ── Entrypoint (TEMPORARY DEBUG VERSION) ───────────────────────────────────────
# This prints out the actual migration files and content as seen inside the
# running container, plus checks for any duplicate/shadow migrations folder,
# before running Alembic. Once we've diagnosed the issue, revert this CMD
# back to the clean one-liner below:
#
#   CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
#
CMD ["sh", "-c", "echo '--- MIGRATIONS FOLDER ---' && ls -la migrations/versions/ && echo '--- PHASE2 FILE CONTENT ---' && cat migrations/versions/xxxx_phase2_draft_reply_and_conversation_status.py && echo '--- SEARCHING FOR OTHER MIGRATIONS DIRS ---' && find / -maxdepth 5 -type d -name migrations 2>/dev/null && echo '--- RUNNING ALEMBIC ---' && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
