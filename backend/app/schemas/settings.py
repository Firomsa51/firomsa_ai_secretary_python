"""Pydantic v2 schemas for the Settings model."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class SettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assistant_mode: str
    auto_reply_enabled: bool
    language: str
    created_at: datetime


class SettingsUpdate(BaseModel):
    assistant_mode: Literal["passive", "suggestive", "autonomous"] | None = None
    auto_reply_enabled: bool | None = None
    language: str | None = None
