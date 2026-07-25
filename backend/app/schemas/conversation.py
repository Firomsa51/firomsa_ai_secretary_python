"""Pydantic v2 schemas for the Conversation model."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    user_id: int
    title: str | None = Field(None, max_length=512)
    category: str | None = Field(None, max_length=128)
    priority: Literal["low", "normal", "high", "urgent"] = "normal"


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str | None
    category: str | None
    priority: str
    created_at: datetime
