"""
Autonomous reply decision engine (Phase 4).

Evaluates every safety/config gate from the Settings row plus per-message
AI signals (confidence, requires_human_review) before allowing an
automatic send. If any gate fails, the message is left as a normal
pending draft for manual review — exactly the Phase 3 workflow, just
reached automatically instead of by the owner tapping "approve".

Every decision (sent or skipped) is audit-logged via the standard logger.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.settings import Settings
from app.models.user import User
from app.services.settings_service import get_or_create_settings
from app.services.telegram_send_service import send_text_to_user

logger = logging.getLogger(__name__)


def _business_hours_ok(settings: Settings) -> bool:
    if not settings.business_hours_only:
        return True
    try:
        from zoneinfo import ZoneInfo
        now_local = datetime.now(ZoneInfo(settings.business_hours_timezone))
    except Exception:  # noqa: BLE001 — unknown/invalid tz string, fail safe to UTC
        now_local = datetime.now(timezone.utc)
    return settings.business_hours_start_hour <= now_local.hour < settings.business_hours_end_hour


async def _cooldown_ok(db: AsyncSession, conversation: Conversation, settings: Settings) -> bool:
    if settings.cooldown_minutes <= 0:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.cooldown_minutes)
    last_auto = await db.scalar(
        select(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.sent_via == "auto",
        )
        .order_by(Message.timestamp.desc())
        .limit(1)
    )
    if last_auto is None:
        return True
    last_ts = last_auto.timestamp
    if last_ts.tzinfo is None:
        last_ts = last_ts.replace(tzinfo=timezone.utc)
    return last_ts <= cutoff


async def _under_reply_limit(db: AsyncSession, conversation: Conversation, settings: Settings) -> bool:
    if settings.max_replies_per_conversation is None:
        return True
    count = await db.scalar(
        select(func.count())
        .select_from(Message)
        .where(Message.conversation_id == conversation.id, Message.sent_via == "auto")
    )
    return (count or 0) < settings.max_replies_per_conversation


def _blocked_keyword_hit(content: str, blocked_keywords: list) -> str | None:
    lowered = content.lower()
    for kw in blocked_keywords or []:
        if kw and str(kw).lower() in lowered:
            return str(kw)
    return None


async def evaluate_and_maybe_autoreply(
    db: AsyncSession,
    conversation: Conversation,
    message: Message,
    user: User,
) -> None:
    """
    Run every Phase 4 safety/config gate for `message`. If all pass, send
    the draft automatically via Telethon. Otherwise leave it as a normal
    pending draft (already set by the agent). Always audit-logs the
    decision, sent or not.
    """
    settings = await get_or_create_settings(db)
    text_to_send = message.edited_draft or message.draft_reply

    reasons_failed: list[str] = []

    if not settings.allow_auto_reply:
        reasons_failed.append("allow_auto_reply is disabled")
    if not text_to_send:
        reasons_failed.append("no draft content")
    if conversation.is_locked:
        reasons_failed.append("conversation is locked")
    if message.requires_human_review:
        reasons_failed.append("AI flagged this message as requiring human review")

    # NOTE: the reply text is now a fixed template (not AI-generated), so a
    # missing/low confidence score no longer implies an unsafe or low
    # quality reply — it usually just means the classifier call failed to
    # return valid JSON (e.g. a transient LLM formatting issue). We only
    # gate on confidence when we actually have a numeric score below the
    # configured threshold; a None score no longer blocks auto-reply on
    # its own. Safety is still enforced independently via
    # requires_human_review and blocked_keywords/categories below.
    if message.ai_confidence is not None and message.ai_confidence < settings.confidence_threshold:
        reasons_failed.append(
            f"confidence {message.ai_confidence!r} below threshold {settings.confidence_threshold}"
        )

    hit = _blocked_keyword_hit(message.content, settings.blocked_keywords)
    if hit:
        reasons_failed.append(f"blocked keyword matched: {hit!r}")
    if conversation.category and conversation.category in (settings.blocked_categories or []):
        reasons_failed.append(f"category {conversation.category!r} is blocked")
    if user.is_blocked:
        reasons_failed.append("sender is blocked")
    if settings.trusted_contacts_only and not user.is_trusted:
        reasons_failed.append("trusted_contacts_only is enabled and sender is not trusted")

    is_emergency = settings.emergency_override and conversation.priority == "urgent"

    if not _business_hours_ok(settings) and not is_emergency:
        reasons_failed.append("outside configured business hours")
    if not await _cooldown_ok(db, conversation, settings) and not is_emergency:
        reasons_failed.append("cooldown period has not elapsed")
    if not await _under_reply_limit(db, conversation, settings):
        reasons_failed.append("maximum_replies_per_conversation reached")

    if reasons_failed:
        logger.info(
            "AUDIT autonomous decision: message_id=%s conversation_id=%s sender_telegram_id=%s "
            "confidence=%s decision=draft_only reason=%s",
            message.id, conversation.id, user.telegram_id,
            message.ai_confidence, "; ".join(reasons_failed),
        )
        return

    try:
        outgoing = await send_text_to_user(db, conversation, user, text_to_send, sent_via="auto")
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "AUDIT autonomous decision: message_id=%s conversation_id=%s decision=send_failed error=%s",
            message.id, conversation.id, exc,
        )
        return

    now = datetime.now(timezone.utc)
    message.draft_status = "sent"
    message.approved_at = now
    message.approved_by = "autonomous_engine"
    message.sent_at = now

    await db.commit()
    logger.info(
        "AUDIT autonomous decision: message_id=%s conversation_id=%s sender_telegram_id=%s "
        "confidence=%s decision=auto_sent outgoing_message_id=%s reply=%r",
        message.id, conversation.id, user.telegram_id,
        message.ai_confidence, outgoing.id, text_to_send,
    )
