"""
Session management utilities for Telethon StringSession.

StringSession stores the Telegram auth state as a plain string, making it
easy to persist in an environment variable or a database column instead of
a file on disk — essential for cloud / ephemeral deployments.
"""

import logging

from telethon.sessions import StringSession

from app.config import settings

logger = logging.getLogger(__name__)


def load_session() -> StringSession:
    """
    Return a StringSession initialised from TELEGRAM_SESSION env var.
    If the variable is empty the session will be unauthenticated and the
    user must complete the OTP flow to generate a new string.
    """
    raw = settings.telegram_session or ""
    if raw:
        logger.info("Loaded existing Telegram session string (len=%d).", len(raw))
    else:
        logger.info("No existing session string found — a fresh session will be created.")
    return StringSession(raw)


def export_session_string(session: StringSession) -> str:
    """
    Serialise an active session to a string.

    Store this value in the TELEGRAM_SESSION environment variable to
    persist authentication across restarts.
    """
    serialised = session.save()
    logger.info(
        "Session exported (len=%d). Store this as TELEGRAM_SESSION.", len(serialised)
    )
    return serialised
