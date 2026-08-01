"""
Telethon event handlers — Phase 2 pipeline; Phase 3 added draft lifecycle;
Phase 4 wires the autonomous decision engine in for 'autonomous' mode and
persists the new AI signal fields (confidence/intent/sentiment/reasoning/
requires_human_review) onto the Message row.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient, events
from telethon.tl.types import Message as TelethonMessage, User as TelethonUser

from app.ai.agent import AgentResult, ConversationContext, FiromsaAgent
from app.ai.memory import MemoryService
from app.ai.providers import get_ai_provider
from app.database import AsyncSessionLocal
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.services import autonomous_service
from app.services.settings_service import get_assistant_mode

logger = logging.getLogger(__name__)

MODE_OFF = "passive"
MODE_ASSIST = "suggestive"
MODE_AUTO = "autonomous"


def register_handlers(client: TelegramClient) -> None:
    logger.info("Registering Telegram event handlers...")

    @client.on(events.NewMessage(incoming=True))
    async def on_new_message(event: events.NewMessage.Event) -> None:
        await _handle_incoming_message(event)

    @client.on(events.MessageEdited(incoming=True))
    async def on_message_edited(event: events.MessageEdited.Event) -> None:
        logger.debug("Message edited: id=%s", event.message.id)

    @client.on(events.MessageRead)
    async def on_message_read(event: events.MessageRead.Event) -> None:
        logger.debug("Messages read up to id=%s in peer=%s", event.max_id, event.peer)

    logger.info("Telegram event handlers registered.")


async def _handle_incoming_message(event: events.NewMessage.Event) -> None:
    msg: TelethonMessage = event.message

    if not await _should_process(event, msg):
        return

    sender = await event.get_sender()

    try:
        async with AsyncSessionLocal() as db:
            user = await _get_or_create_user(db, sender)
            conversation = await _get_or_create_conversation(db, user)

            message = await _store_message(db, conversation, msg)
            if message is None:
                await db.commit()
                return

            await db.commit()
            await db.refresh(conversation)
            await db.refresh(message)

            mode = await get_assistant_mode(db)
            logger.info(
                "Processing message id=%s in mode=%r for user_id=%s",
                message.id, mode, user.id,
            )

            if mode == MODE_OFF:
                logger.info("Assistant mode is OFF - message stored only.")
                return

            await _run_agent_and_save(db, conversation, message, user, sender)

            if mode == MODE_AUTO:
                await autonomous_service.evaluate_and_maybe_autoreply(
                    db, conversation, message, user
                )

    except Exception:  # noqa: BLE001
        logger.exception("Failed to process incoming Telegram message id=%s", msg.id)


async def _should_process(event: events.NewMessage.Event, msg: TelethonMessage) -> bool:
    if not event.is_private:
        logger.debug("Ignoring non-private message id=%s.", msg.id)
        return False
    if msg.action is not None:
        logger.debug("Ignoring service message id=%s.", msg.id)
        return False
    sender = await event.get_sender()
    if sender is None:
        logger.debug("Ignoring message id=%s with unresolved sender.", msg.id)
        return False
    if getattr(sender, "bot", False):
        logger.debug("Ignoring message id=%s from bot sender.", msg.id)
        return False
    if not isinstance(sender, TelethonUser):
        logger.debug("Ignoring message id=%s from non-user sender.", msg.id)
        return False
    if not (msg.text or msg.message):
        logger.debug("Ignoring non-text message id=%s.", msg.id)
        return False
    return True


async def _get_or_create_user(db: AsyncSession, sender: TelethonUser) -> User:
    user = await db.scalar(select(User).where(User.telegram_id == sender.id))
    if user is not None:
        changed = False
        if user.username != sender.username:
            user.username = sender.username
            changed = True
        if sender.first_name and user.first_name != sender.first_name:
            user.first_name = sender.first_name
            changed = True
        if user.last_name != sender.last_name:
            user.last_name = sender.last_name
            changed = True
        if changed:
            await db.flush()
        return user

    user = User(
        telegram_id=sender.id,
        username=sender.username,
        first_name=sender.first_name or "Unknown",
        last_name=sender.last_name,
    )
    db.add(user)
    await db.flush()
    logger.info("Created new User telegram_id=%s username=%s", sender.id, sender.username)
    return user


async def _get_or_create_conversation(db: AsyncSession, user: User) -> Conversation:
    conversation = await db.scalar(
        select(Conversation)
        .where(Conversation.user_id == user.id, Conversation.status == "open")
        .order_by(Conversation.last_message_at.desc())
    )
    if conversation is not None:
        return conversation

    conversation = Conversation(user_id=user.id, status="open")
    db.add(conversation)
    await db.flush()
    logger.info("Opened new Conversation id=%s for user_id=%s", conversation.id, user.id)
    return conversation


async def _store_message(
    db: AsyncSession, conversation: Conversation, msg: TelethonMessage
) -> Message | None:
    existing = await db.scalar(
        select(Message).where(
            Message.conversation_id == conversation.id,
            Message.telegram_message_id == msg.id,
        )
    )
    if existing is not None:
        logger.info(
            "Duplicate Telegram message id=%s already stored as Message id=%s - skipping.",
            msg.id, existing.id,
        )
        return None

    content = msg.text or msg.message or ""
    message = Message(
        conversation_id=conversation.id,
        sender="contact",
        content=content,
        telegram_message_id=msg.id,
    )
    db.add(message)
    conversation.last_message_at = datetime.now(timezone.utc)
    await db.flush()
    logger.info("Stored Message id=%s (conversation_id=%s)", message.id, conversation.id)
    return message


def _build_history(conversation: Conversation, exclude_message_id: int) -> list[dict[str, str]]:
    history: list[dict[str, str]] = []
    for m in conversation.messages:
        if m.id == exclude_message_id:
            continue
        history.append({"sender": m.sender, "content": m.content})
        if m.draft_status in ("pending", "approved") and (m.edited_draft or m.draft_reply):
            history.append({"sender": "ai", "content": m.edited_draft or m.draft_reply})
    return history


async def _run_agent_and_save(
    db: AsyncSession,
    conversation: Conversation,
    message: Message,
    user: User,
    sender: TelethonUser,
) -> AgentResult:
    history = _build_history(conversation, exclude_message_id=message.id)

    sender_name = sender.username or sender.first_name or f"user_{user.telegram_id}"
    ctx = ConversationContext(
        user_id=user.id,
        sender_name=sender_name,
        latest_message=message.content,
        history=history,
    )

    agent = FiromsaAgent(provider=get_ai_provider(), memory_service=MemoryService(db))

    try:
        result = await agent.process(ctx)
    except Exception:  # noqa: BLE001
        logger.exception("AI agent processing failed for message id=%s", message.id)
        return AgentResult(draft_reply=None, category=None, priority=None, summary=None)

    if result.category:
        conversation.category = result.category
    if result.priority:
        conversation.priority = result.priority
    if result.draft_reply:
        message.draft_reply = result.draft_reply
        message.draft_status = "pending"
        message.edited_draft = None
        message.approved_at = None
        message.sent_at = None
        message.approved_by = None
        message.sent_via = None

    message.ai_confidence = result.confidence
    message.ai_intent = result.intent
    message.ai_sentiment = result.sentiment
    message.ai_reasoning = result.reasoning
    message.requires_human_review = result.requires_human_review

    await db.commit()
    logger.info(
        "Agent result saved: message_id=%s category=%r priority=%r confidence=%s "
        "requires_human_review=%s draft_len=%s",
        message.id, result.category, result.priority, result.confidence,
        result.requires_human_review,
        len(result.draft_reply) if result.draft_reply else 0,
    )
    return result
