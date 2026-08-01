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

    IMPORTANT: ordered by id ascending and limited to 1 so that if more
    than one row ever exists in the table (e.g. left over from earlier
    testing / resets), we always deterministically return the SAME row
    every time instead of whichever row the database happens to return
    first for an unfiltered/unordered SELECT. Without this, PATCH
    /settings/ could update one row while the message handler reads a
    different one, making settings changes appear to silently not apply.
    """
    row = await db.scalar(select(Settings).order_by(Settings.id.asc()).limit(1))
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
