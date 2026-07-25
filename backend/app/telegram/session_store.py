"""
Session store — persists and loads the Telethon StringSession from the database.

The session string is stored in the Settings row (singleton) so it survives
restarts and works on stateless cloud deployments without a session file.

Why the DB instead of just an env var?
  - The session string changes after every re-authentication.
  - Writing back to an env var at runtime is not possible on most platforms.
  - The DB provides a single source of truth that the app can update itself.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Column used to persist the session string in the settings table.
# We reuse the settings singleton rather than adding a dedicated table.
_SESSION_KEY = "telegram_session_string"


async def load_session_string(db: AsyncSession) -> str | None:
    """
    Read the Telegram StringSession from the database.
    Returns None if no session has been stored yet.
    """
    from app.models.settings import Settings  # local import to avoid circulars

    row = await db.scalar(select(Settings))
    if row is None:
        return None
    value: str | None = getattr(row, "telegram_session_string", None)
    if value:
        logger.debug("Loaded Telegram session string from DB (len=%d).", len(value))
    return value


async def save_session_string(db: AsyncSession, session_string: str) -> None:
    """
    Persist the Telegram StringSession to the database settings row,
    creating the row if it does not exist.
    """
    from app.models.settings import Settings  # local import

    row = await db.scalar(select(Settings))
    if row is None:
        row = Settings()
        db.add(row)

    row.telegram_session_string = session_string  # type: ignore[attr-defined]
    await db.commit()
    logger.info(
        "Telegram session string saved to DB (len=%d).", len(session_string)
    )
