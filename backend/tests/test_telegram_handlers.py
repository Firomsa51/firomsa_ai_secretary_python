"""
Tests for the Phase 2 Telegram message handling pipeline.

External services (Telethon events/sender objects, the AI agent, and the
AI provider) are mocked — only persistence logic and mode-branching are
exercised against a real (in-memory) database.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from app.ai.agent import AgentResult
from app.models.message import Message
from app.models.settings import Settings
from app.models.user import User
from app.telegram import handlers

pytestmark = pytest.mark.asyncio


def make_sender(telegram_id=111, username="alice", first_name="Alice", last_name=None, bot=False):
    sender = MagicMock()
    sender.id = telegram_id
    sender.username = username
    sender.first_name = first_name
    sender.last_name = last_name
    sender.bot = bot
    return sender


def make_message(msg_id=1, text="Hello there", action=None):
    msg = MagicMock()
    msg.id = msg_id
    msg.text = text
    msg.message = text
    msg.action = action
    return msg


def make_event(is_private=True, sender=None, message=None):
    event = MagicMock()
    event.is_private = is_private
    event.message = message
    event.get_sender = AsyncMock(return_value=sender)
    return event


async def test_should_process_accepts_private_text_from_user():
    sender = make_sender()
    msg = make_message()
    event = make_event(is_private=True, sender=sender, message=msg)
    assert await handlers._should_process(event, msg) is True


async def test_should_process_rejects_group_messages():
    sender = make_sender()
    msg = make_message()
    event = make_event(is_private=False, sender=sender, message=msg)
    assert await handlers._should_process(event, msg) is False


async def test_should_process_rejects_bot_sender():
    sender = make_sender(bot=True)
    msg = make_message()
    event = make_event(is_private=True, sender=sender, message=msg)
    assert await handlers._should_process(event, msg) is False


async def test_should_process_rejects_service_messages():
    sender = make_sender()
    msg = make_message(action=MagicMock())
    event = make_event(is_private=True, sender=sender, message=msg)
    assert await handlers._should_process(event, msg) is False


async def test_get_or_create_user_creates_then_reuses(db_session):
    sender = make_sender()

    user = await handlers._get_or_create_user(db_session, sender)
    await db_session.commit()
    assert user.telegram_id == sender.id

    same_user = await handlers._get_or_create_user(db_session, sender)
    assert same_user.id == user.id

    rows = (await db_session.scalars(select(User))).all()
    assert len(rows) == 1


async def test_get_or_create_conversation_reuses_open_conversation(db_session):
    sender = make_sender()
    user = await handlers._get_or_create_user(db_session, sender)
    await db_session.commit()

    convo1 = await handlers._get_or_create_conversation(db_session, user)
    await db_session.commit()
    convo2 = await handlers._get_or_create_conversation(db_session, user)

    assert convo1.id == convo2.id
    assert convo1.status == "open"


async def test_store_message_persists_and_dedups(db_session):
    sender = make_sender()
    user = await handlers._get_or_create_user(db_session, sender)
    conversation = await handlers._get_or_create_conversation(db_session, user)
    await db_session.commit()

    msg = make_message(msg_id=555, text="hi")
    stored = await handlers._store_message(db_session, conversation, msg)
    await db_session.commit()
    assert stored is not None
    assert stored.telegram_message_id == 555

    duplicate = await handlers._store_message(db_session, conversation, msg)
    assert duplicate is None

    all_messages = (await db_session.scalars(select(Message))).all()
    assert len(all_messages) == 1


async def test_run_agent_and_save_updates_conversation_and_message(db_session, monkeypatch):
    sender = make_sender()
    user = await handlers._get_or_create_user(db_session, sender)
    conversation = await handlers._get_or_create_conversation(db_session, user)
    await db_session.commit()

    msg = make_message(msg_id=42, text="Can we meet tomorrow?")
    message = await handlers._store_message(db_session, conversation, msg)
    await db_session.commit()

    fake_result = AgentResult(
        draft_reply="Sure, does 3pm work?",
        category="scheduling",
        priority="high",
        summary="Contact wants to meet.",
    )

    async def fake_process(self, ctx):
        return fake_result

    monkeypatch.setattr("app.ai.agent.FiromsaAgent.process", fake_process)
    monkeypatch.setattr(handlers, "get_ai_provider", lambda: MagicMock())

    await handlers._run_agent_and_save(db_session, conversation, message, user, sender)

    await db_session.refresh(conversation)
    await db_session.refresh(message)

    assert conversation.category == "scheduling"
    assert conversation.priority == "high"
    assert message.draft_reply == "Sure, does 3pm work?"


async def test_off_mode_skips_agent(db_session, monkeypatch):
    """When assistant_mode is 'passive' (OFF), the agent must not run."""
    settings_row = Settings(assistant_mode="passive")
    db_session.add(settings_row)
    await db_session.commit()

    agent_ran = {"called": False}

    async def fake_run_agent_and_save(*args, **kwargs):
        agent_ran["called"] = True

    monkeypatch.setattr(handlers, "_run_agent_and_save", fake_run_agent_and_save)
    monkeypatch.setattr(handlers, "AsyncSessionLocal", lambda: db_session)

    sender = make_sender()
    msg = make_message(msg_id=999, text="Just checking in")
    event = make_event(is_private=True, sender=sender, message=msg)

    await handlers._handle_incoming_message(event)

    assert agent_ran["called"] is False
    stored = (await db_session.scalars(select(Message))).all()
    assert len(stored) == 1
