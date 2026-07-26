"""
Pydantic v2 schemas for the draft-reply workflow on Message (Phase 3).

There is no dedicated Draft table: a draft is the lifecycle state of the
Message row that produced it (draft_reply from Phase 2; edited_draft,
draft_status, approved_at, sent_at, approved_by added in Phase 3).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DraftStatus = Literal["pending", "approved", "rejected", "sent"]


class DraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    content: str
    draft_reply: str | None
    edited_draft: str | None
    draft_status: DraftStatus | None
    approved_at: datetime | None
    sent_at: datetime | None
    approved_by: str | None
    timestamp: datetime


class DraftEditPayload(BaseModel):
    edited_draft: str = Field(..., min_length=1)
    actor: str | None = Field(None, max_length=255)


class DraftApprovePayload(BaseModel):
    actor: str | None = Field(None, max_length=255)
    edited_draft: str | None = Field(None, min_length=1)


class DraftRejectPayload(BaseModel):
    actor: str | None = Field(None, max_length=255)
    reason: str | None = Field(None, max_length=1000)
