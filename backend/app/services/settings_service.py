"""
Settings service — fetch-or-create helper for the singleton Settings row.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import Settings

logger = logging.getLogger(__name__)


async def get_or_create_settings(db: AsyncSession) -> Settings:
    """
    Return the singleton Settings row, creating it with defaults if it
    does not exist yet.
    """
    row = await db.scalar(select(Settings))
    if row is None:
        row = Settings()
        db.add(row)
        await db.flush()
        logger.info("Created default Settings row (assistant_mode=%r).", row.assistant_mode)
    return row


async def get_assistant_mode(db: AsyncSession) -> str:
    """Convenience accessor: return the current assistant_mode string."""
    row = await get_or_create_settings(db)
    return row.assistant_mode
