"""Pydantic v2 schemas for the Message model."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    conversation_id: int
    sender: Literal["owner", "contact", "ai"]
    content: str = Field(..., min_length=1)
    telegram_message_id: int | None = None


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    sender: str
    content: str
    telegram_message_id: int | None
    # ── Phase 2 / Phase 3 draft lifecycle fields ─────────────────────────────
    draft_reply: str | None = None
    edited_draft: str | None = None
    draft_status: Literal["pending", "approved", "rejected", "sent"] | None = None
    approved_at: datetime | None = None
    sent_at: datetime | None = None
    approved_by: str | None = None
    timestamp: datetime
