"""Pydantic v2 schemas for the User model."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    telegram_id: int = Field(..., description="Telegram user ID")
    username: str | None = Field(None, description="@username without the @")
    first_name: str = Field(..., max_length=255)
    last_name: str | None = Field(None, max_length=255)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: str | None
    first_name: str
    last_name: str | None
    created_at: datetime
