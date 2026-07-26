"""
Draft management service (Phase 3, updated in Phase 4) — the approve /
edit / reject / send lifecycle for AI-generated draft replies.

No new "Draft" table: a draft is inherently 1:1 with the incoming Message
it replies to, so lifecycle fields live directly on Message. Actions are
audit-logged via the standard logger. The actual Telethon send call now
lives in telegram_send_service.py, shared with the Phase 4 autonomous
engine, so that logic exists in exactly one place.
"""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.services.telegram_send_service import send_text_to_user

logger = logging.getLogger(__name__)


async def _get_message_with_draft_or_404(db: AsyncSession, message_id: int) -> Message:
    message = await db.get(Message, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found.")
    if message.draft_reply is None:
        raise HTTPException(
            status_code=400, detail="This message has no AI draft reply."
        )
    return message


async def list_pending_drafts(
    db: AsyncSession,
    conversation_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Message]:
    query = (
        select(Message)
        .where(Message.draft_status == "pending")
        .order_by(Message.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )
    if conversation_id is not None:
        query = query.where(Message.conversation_id == conversation_id)
    result = await db.scalars(query)
    return list(result.all())


async def get_draft(db: AsyncSession, message_id: int) -> Message:
    return await _get_message_with_draft_or_404(db, message_id)


async def edit_draft(
    db: AsyncSession, message_id: int, edited_draft: str, actor: str | None
) -> Message:
    message = await _get_message_with_draft_or_404(db, message_id)
    if message.draft_status == "sent":
        raise HTTPException(
            status_code=400, detail="Cannot edit a draft that has already been sent."
        )

    message.edited_draft = edited_draft
    if message.draft_status == "rejected":
        message.draft_status = "pending"

    await db.commit()
    logger.info(
        "AUDIT draft edited: message_id=%s actor=%s conversation_id=%s",
        message.id, actor, message.conversation_id,
    )
    return message


async def approve_draft(
    db: AsyncSession,
    message_id: int,
    actor: str | None,
    edited_draft: str | None = None,
) -> Message:
    message = await _get_message_with_draft_or_404(db, message_id)
    if message.draft_status == "sent":
        raise HTTPException(status_code=400, detail="This draft has already been sent.")

    if edited_draft is not None:
        message.edited_draft = edited_draft

    message.draft_status = "approved"
    message.approved_at = datetime.now(timezone.utc)
    message.approved_by = actor

    await db.commit()
    logger.info(
        "AUDIT draft approved: message_id=%s actor=%s conversation_id=%s",
        message.id, actor, message.conversation_id,
    )
    return message


async def reject_draft(
    db: AsyncSession,
    message_id: int,
    actor: str | None,
    reason: str | None,
) -> Message:
    message = await _get_message_with_draft_or_404(db, message_id)
    if message.draft_status == "sent":
        raise HTTPException(status_code=400, detail="This draft has already been sent.")

    message.draft_status = "rejected"
    message.approved_at = None
    message.approved_by = None

    await db.commit()
    logger.info(
        "AUDIT draft rejected: message_id=%s actor=%s conversation_id=%s reason=%r",
        message.id, actor, message.conversation_id, reason,
    )
    return message


async def send_approved_draft(db: AsyncSession, message_id: int) -> Message:
    """
    Send an approved draft to the contact via the shared send helper, and
    mark this message's lifecycle as sent (sent_via='manual').
    """
    message = await _get_message_with_draft_or_404(db, message_id)
    if message.draft_status != "approved":
        raise HTTPException(
            status_code=400,
            detail="Only an approved draft can be sent. Approve it first.",
        )

    conversation = await db.get(Conversation, message.conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    user = await db.get(User, conversation.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    text_to_send = message.edited_draft or message.draft_reply
    if not text_to_send:
        raise HTTPException(status_code=400, detail="Draft has no content to send.")

    outgoing = await send_text_to_user(db, conversation, user, text_to_send, sent_via="manual")

    message.draft_status = "sent"
    message.sent_at = datetime.now(timezone.utc)

    await db.commit()
    logger.info(
        "AUDIT draft sent (manual): message_id=%s conversation_id=%s outgoing_message_id=%s",
        message.id, conversation.id, outgoing.id,
    )
    return message
