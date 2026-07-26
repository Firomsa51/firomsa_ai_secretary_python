"""
Tests for the Phase 3 draft management service (approve/edit/reject/send).
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.services import draft_service

pytestmark = pytest.mark.asyncio


async def _make_draft_message(db_session, draft_reply="Sure, 3pm works."):
    user = User(telegram_id=1, username="bob", first_name="Bob")
    db_session.add(user)
    await db_session.flush()

    conversation = Conversation(user_id=user.id, status="open")
    db_session.add(conversation)
    await db_session.flush()

    message = Message(
        conversation_id=conversation.id,
        sender="contact",
        content="Can we meet?",
        draft_reply=draft_reply,
        draft_status="pending",
    )
    db_session.add(message)
    await db_session.commit()
    return user, conversation, message


async def test_get_draft_404_for_missing_message(db_session):
    with pytest.raises(HTTPException) as exc_info:
        await draft_service.get_draft(db_session, message_id=9999)
    assert exc_info.value.status_code == 404


async def test_get_draft_400_when_no_draft_reply(db_session):
    user = User(telegram_id=2, username="nodraft", first_name="No")
    db_session.add(user)
    await db_session.flush()
    conversation = Conversation(user_id=user.id, status="open")
    db_session.add(conversation)
    await db_session.flush()
    message = Message(conversation_id=conversation.id, sender="contact", content="hi")
    db_session.add(message)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await draft_service.get_draft(db_session, message.id)
    assert exc_info.value.status_code == 400


async def test_edit_draft_updates_edited_draft(db_session):
    _, _, message = await _make_draft_message(db_session)

    updated = await draft_service.edit_draft(
        db_session, message.id, edited_draft="Actually, does 4pm work?", actor="firomsa"
    )
    assert updated.edited_draft == "Actually, does 4pm work?"
    assert updated.draft_status == "pending"


async def test_approve_draft_sets_status_and_timestamps(db_session):
    _, _, message = await _make_draft_message(db_session)

    approved = await draft_service.approve_draft(db_session, message.id, actor="firomsa")
    assert approved.draft_status == "approved"
    assert approved.approved_by == "firomsa"
    assert approved.approved_at is not None


async def test_reject_draft_sets_status_rejected(db_session):
    _, _, message = await _make_draft_message(db_session)

    rejected = await draft_service.reject_draft(
        db_session, message.id, actor="firomsa", reason="Not relevant anymore."
    )
    assert rejected.draft_status == "rejected"
    assert rejected.approved_at is None


async def test_send_requires_approved_status(db_session):
    _, _, message = await _make_draft_message(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await draft_service.send_approved_draft(db_session, message.id)
    assert exc_info.value.status_code == 400


async def test_send_approved_draft_calls_telethon_and_records_outgoing_message(
    db_session, monkeypatch
):
    _, conversation, message = await _make_draft_message(db_session)
    await draft_service.approve_draft(db_session, message.id, actor="firomsa")

    fake_sent_message = SimpleNamespace(id=555)
    mock_client = SimpleNamespace(send_message=AsyncMock(return_value=fake_sent_message))

    monkeypatch.setattr(draft_service.telegram_client, "is_connected", True)
    monkeypatch.setattr(
        draft_service.telegram_client, "is_authorised", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(draft_service.telegram_client, "client", mock_client)

    result = await draft_service.send_approved_draft(db_session, message.id)

    assert result.draft_status == "sent"
    assert result.sent_at is not None
    mock_client.send_message.assert_awaited_once()

    outgoing = (
        await db_session.scalars(
            select(Message).where(
                Message.conversation_id == conversation.id, Message.sender == "ai"
            )
        )
    ).all()
    assert len(outgoing) == 1
    assert outgoing[0].content == message.draft_reply


async def test_send_fails_if_telegram_not_connected(db_session, monkeypatch):
    _, _, message = await _make_draft_message(db_session)
    await draft_service.approve_draft(db_session, message.id, actor="firomsa")

    monkeypatch.setattr(draft_service.telegram_client, "is_connected", False)

    with pytest.raises(HTTPException) as exc_info:
        await draft_service.send_approved_draft(db_session, message.id)
    assert exc_info.value.status_code == 502
