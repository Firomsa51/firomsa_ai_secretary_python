"""
Tests for the Phase 4 autonomous reply decision engine.

Each test builds a minimal user/conversation/message/settings fixture and
asserts whether evaluate_and_maybe_autoreply sends (via a mocked Telethon
call) or leaves the draft pending, plus checks the audit log line.
"""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.settings import Settings
from app.models.user import User
from app.services import autonomous_service

pytestmark = pytest.mark.asyncio


async def _make_scenario(
    db_session,
    *,
    allow_auto_reply=True,
    confidence=0.9,
    confidence_threshold=0.75,
    requires_human_review=False,
    is_locked=False,
    is_blocked=False,
    is_trusted=False,
    trusted_contacts_only=False,
    blocked_keywords=None,
    blocked_categories=None,
    business_hours_only=False,
    category=None,
    priority="normal",
    max_replies_per_conversation=None,
    cooldown_minutes=15,
    emergency_override=False,
):
    settings = Settings(
        allow_auto_reply=allow_auto_reply,
        confidence_threshold=confidence_threshold,
        trusted_contacts_only=trusted_contacts_only,
        blocked_keywords=blocked_keywords or [],
        blocked_categories=blocked_categories or [],
        business_hours_only=business_hours_only,
        max_replies_per_conversation=max_replies_per_conversation,
        cooldown_minutes=cooldown_minutes,
        emergency_override=emergency_override,
    )
    db_session.add(settings)

    user = User(
        telegram_id=42, username="carol", first_name="Carol",
        is_blocked=is_blocked, is_trusted=is_trusted,
    )
    db_session.add(user)
    await db_session.flush()

    conversation = Conversation(
        user_id=user.id, status="open", is_locked=is_locked,
        category=category, priority=priority,
    )
    db_session.add(conversation)
    await db_session.flush()

    message = Message(
        conversation_id=conversation.id,
        sender="contact",
        content="Can we reschedule to tomorrow?",
        draft_reply="Sure, tomorrow works for me.",
        draft_status="pending",
        ai_confidence=confidence,
        requires_human_review=requires_human_review,
    )
    db_session.add(message)
    await db_session.commit()

    return settings, user, conversation, message


def _mock_send(monkeypatch):
    fake_sent = SimpleNamespace(id=999)
    mock_client = SimpleNamespace(send_message=AsyncMock(return_value=fake_sent))
    monkeypatch.setattr(autonomous_service.telegram_client, "is_connected", True)
    monkeypatch.setattr(
        autonomous_service.telegram_client, "is_authorised", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(autonomous_service.telegram_client, "client", mock_client)
    return mock_client


async def test_sends_when_all_gates_pass(db_session, monkeypatch):
    _, user, conversation, message = await _make_scenario(db_session)
    mock_client = _mock_send(monkeypatch)

    await autonomous_service.evaluate_and_maybe_autoreply(db_session, conversation, message, user)

    mock_client.send_message.assert_awaited_once()
    assert message.draft_status == "sent"
    assert message.approved_by == "autonomous_engine"
    assert message.sent_at is not None


async def test_blocks_when_allow_auto_reply_disabled(db_session, monkeypatch):
    _, user, conversation, message = await _make_scenario(db_session, allow_auto_reply=False)
    mock_client = _mock_send(monkeypatch)

    await autonomous_service.evaluate_and_maybe_autoreply(db_session, conversation, message, user)

    mock_client.send_message.assert_not_awaited()
    assert message.draft_status == "pending"


async def test_blocks_when_requires_human_review(db_session, monkeypatch):
    _, user, conversation, message = await _make_scenario(
        db_session, requires_human_review=True
    )
    mock_client = _mock_send(monkeypatch)

    await autonomous_service.evaluate_and_maybe_autoreply(db_session, conversation, message, user)

    mock_client.send_message.assert_not_awaited()
    assert message.draft_status == "pending"


async def test_blocks_when_confidence_below_threshold(db_session, monkeypatch):
    _, user, conversation, message = await _make_scenario(
        db_session, confidence=0.5, confidence_threshold=0.75
    )
    mock_client = _mock_send(monkeypatch)

    await autonomous_service.evaluate_and_maybe_autoreply(db_session, conversation, message, user)

    mock_client.send_message.assert_not_awaited()
    assert message.draft_status == "pending"


async def test_blocks_when_conversation_locked(db_session, monkeypatch):
    _, user, conversation, message = await _make_scenario(db_session, is_locked=True)
    mock_client = _mock_send(monkeypatch)

    await autonomous_service.evaluate_and_maybe_autoreply(db_session, conversation, message, user)

    mock_client.send_message.assert_not_awaited()
    assert message.draft_status == "pending"


async def test_blocks_when_sender_blocked(db_session, monkeypatch):
    _, user, conversation, message = await _make_scenario(db_session, is_blocked=True)
    mock_client = _mock_send(monkeypatch)

    await autonomous_service.evaluate_and_maybe_autoreply(db_session, conversation, message, user)

    mock_client.send_message.assert_not_awaited()
    assert message.draft_status == "pending"


async def test_blocks_when_trusted_contacts_only_and_not_trusted(db_session, monkeypatch):
    _, user, conversation, message = await _make_scenario(
        db_session, trusted_contacts_only=True, is_trusted=False
    )
    mock_client = _mock_send(monkeypatch)

    await autonomous_service.evaluate_and_maybe_autoreply(db_session, conversation, message, user)

    mock_client.send_message.assert_not_awaited()
    assert message.draft_status == "pending"


async def test_allows_when_trusted_contacts_only_and_is_trusted(db_session, monkeypatch):
    _, user, conversation, message = await _make_scenario(
        db_session, trusted_contacts_only=True, is_trusted=True
    )
    mock_client = _mock_send(monkeypatch)

    await autonomous_service.evaluate_and_maybe_autoreply(db_session, conversation, message, user)

    mock_client.send_message.assert_awaited_once()
    assert message.draft_status == "sent"


async def test_blocks_on_blocked_keyword(db_session, monkeypatch):
    _, user, conversation, message = await _make_scenario(
        db_session, blocked_keywords=["reschedule"]
    )
    mock_client = _mock_send(monkeypatch)

    await autonomous_service.evaluate_and_maybe_autoreply(db_session, conversation, message, user)

    mock_client.send_message.assert_not_awaited()
    assert message.draft_status == "pending"


async def test_blocks_on_blocked_category(db_session, monkeypatch):
    _, user, conversation, message = await _make_scenario(
        db_session, category="legal", blocked_categories=["legal"]
    )
    mock_client = _mock_send(monkeypatch)

    await autonomous_service.evaluate_and_maybe_autoreply(db_session, conversation, message, user)

    mock_client.send_message.assert_not_awaited()
    assert message.draft_status == "pending"


async def test_blocks_when_max_replies_per_conversation_reached(db_session, monkeypatch):
    _, user, conversation, message = await _make_scenario(
        db_session, max_replies_per_conversation=1
    )
    prior = Message(
        conversation_id=conversation.id, sender="ai", content="Earlier auto reply.",
        sent_via="auto",
    )
    db_session.add(prior)
    await db_session.commit()

    mock_client = _mock_send(monkeypatch)
    await autonomous_service.evaluate_and_maybe_autoreply(db_session, conversation, message, user)

    mock_client.send_message.assert_not_awaited()
    assert message.draft_status == "pending"


async def test_cooldown_blocks_rapid_repeat_send(db_session, monkeypatch):
    _, user, conversation, message = await _make_scenario(db_session, cooldown_minutes=60)
    recent = Message(
        conversation_id=conversation.id, sender="ai", content="Just sent.",
        sent_via="auto",
    )
    db_session.add(recent)
    await db_session.commit()

    mock_client = _mock_send(monkeypatch)
    await autonomous_service.evaluate_and_maybe_autoreply(db_session, conversation, message, user)

    mock_client.send_message.assert_not_awaited()
    assert message.draft_status == "pending"


async def test_emergency_override_bypasses_business_hours_for_urgent(db_session, monkeypatch):
    _, user, conversation, message = await _make_scenario(
        db_session,
        business_hours_only=True,
        emergency_override=True,
        priority="urgent",
    )
    mock_client = _mock_send(monkeypatch)

    await autonomous_service.evaluate_and_maybe_autoreply(db_session, conversation, message, user)

    mock_client.send_message.assert_awaited_once()
    assert message.draft_status == "sent"


async def test_audit_log_written_on_skip(db_session, monkeypatch, caplog):
    _, user, conversation, message = await _make_scenario(db_session, allow_auto_reply=False)
    _mock_send(monkeypatch)

    with caplog.at_level(logging.INFO, logger="app.services.autonomous_service"):
        await autonomous_service.evaluate_and_maybe_autoreply(
            db_session, conversation, message, user
        )

    assert any("decision=draft_only" in r.message for r in caplog.records)


async def test_audit_log_written_on_send(db_session, monkeypatch, caplog):
    _, user, conversation, message = await _make_scenario(db_session)
    _mock_send(monkeypatch)

    with caplog.at_level(logging.INFO, logger="app.services.autonomous_service"):
        await autonomous_service.evaluate_and_maybe_autoreply(
            db_session, conversation, message, user
        )

    assert any("decision=auto_sent" in r.message for r in caplog.records)
