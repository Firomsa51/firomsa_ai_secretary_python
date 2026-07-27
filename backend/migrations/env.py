"""
Alembic environment configuration for async SQLAlchemy.
"""

import asyncio
import os
import sys
from logging.config import fileConfig

# ---------------------------------------------------------------------
# Ensure the backend directory is on Python's import path.
# This fixes:
# ModuleNotFoundError: No module named 'app'
# when running Alembic inside Docker/Render.
# ---------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.database import Base

# Import all models so Alembic can detect them
import app.models  # noqa: F401

# ---------------------------------------------------------------------
# Alembic configuration
# ---------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ---------------------------------------------------------------------
# Offline migrations
# ---------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations without a live database connection."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------
# Online migrations
# ---------------------------------------------------------------------
def do_run_migrations(connection):
    """Run migrations using an existing connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against the configured async database."""
    engine = create_async_engine(settings.database_url)

    async with engine.begin() as connection:
        await connection.run_sync(do_run_migrations)

    await engine.dispose()


# ---------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
