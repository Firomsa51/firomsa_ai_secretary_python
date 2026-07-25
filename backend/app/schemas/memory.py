"""Pydantic v2 schemas for the Memory model."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MemoryCreate(BaseModel):
    user_id: int
    key: str = Field(..., max_length=255, description="Semantic label, e.g. 'working_hours'")
    value: str = Field(..., description="Free-form text or JSON string")


class MemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    key: str
    value: str
    created_at: datetime
