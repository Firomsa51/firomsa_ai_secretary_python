"""Pydantic v2 schemas for the Settings model."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assistant_mode: str
    auto_reply_enabled: bool
    language: str
    allow_auto_reply: bool
    business_hours_only: bool
    business_hours_start_hour: int
    business_hours_end_hour: int
    business_hours_timezone: str
    cooldown_minutes: int
    max_replies_per_conversation: int | None
    confidence_threshold: float
    trusted_contacts_only: bool
    blocked_keywords: list[str]
    blocked_categories: list[str]
    emergency_override: bool
    created_at: datetime


class SettingsUpdate(BaseModel):
    assistant_mode: Literal["passive", "suggestive", "autonomous"] | None = None
    auto_reply_enabled: bool | None = None
    language: str | None = None
    allow_auto_reply: bool | None = None
    business_hours_only: bool | None = None
    business_hours_start_hour: int | None = Field(None, ge=0, le=23)
    business_hours_end_hour: int | None = Field(None, ge=0, le=23)
    business_hours_timezone: str | None = None
    cooldown_minutes: int | None = Field(None, ge=0)
    max_replies_per_conversation: int | None = Field(None, ge=0)
    confidence_threshold: float | None = Field(None, ge=0.0, le=1.0)
    trusted_contacts_only: bool | None = None
    blocked_keywords: list[str] | None = None
    blocked_categories: list[str] | None = None
    emergency_override: bool | None = None
