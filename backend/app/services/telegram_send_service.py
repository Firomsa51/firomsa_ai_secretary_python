"""
Shared Telegram-send helper (Phase 4 extraction).

Used by both the manual draft-approval flow (draft_service, Phase 3) and
the autonomous auto-reply engine (autonomous_service, Phase 4), so the
actual Telethon send + bookkeeping logic exists in exactly one place.
"""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.telegram.client import telegram_client

logger = logging.getLogger(__name__)


async def send_text_to_user(
    db: AsyncSession,
    conversation: Conversation,
    user: User,
    text: str,
    sent_via: str,
) -> Message:
    """
    Send `text` to `user` via the live Telethon client and persist it as a
    new outgoing Message row (sender='ai', sent_via=<'manual'|'auto'>).

    Raises HTTPException on failure — appropriate for callers running
    inside a FastAPI request (draft_service). Callers running in the
    background pipeline (autonomous_service) should catch it themselves.
    """
    if not telegram_client.is_connected or not await telegram_client.is_authorised():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Telegram client is not connected/authorised. Cannot send.",
        )

    try:
        sent = await telegram_client.client.send_message(user.telegram_id, text)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send message to telegram_id=%s", user.telegram_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to send message via Telegram: {exc}",
        ) from exc

    now = datetime.now(timezone.utc)
    outgoing = Message(
        conversation_id=conversation.id,
        sender="ai",
        content=text,
        telegram_message_id=getattr(sent, "id", None),
        sent_via=sent_via,
    )
    db.add(outgoing)
    conversation.last_message_at = now
    await db.flush()
    logger.info(
        "Sent message via Telegram: conversation_id=%s outgoing_message_id=%s sent_via=%s",
        conversation.id, outgoing.id, sent_via,
    )
    return outgoing
