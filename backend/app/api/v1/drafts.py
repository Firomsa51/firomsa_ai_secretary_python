"""
Draft management endpoints (Phase 3) — approve / edit / reject / send
AI-generated draft replies.

No new tables: a draft is the lifecycle state of the Message row that
produced it (see Phase 2's draft_reply column, extended in Phase 3).
"""

from fastapi import APIRouter

from app.dependencies import DBSession
from app.schemas.draft import (
    DraftApprovePayload,
    DraftEditPayload,
    DraftRead,
    DraftRejectPayload,
)
from app.services import draft_service

router = APIRouter()


@router.get("/pending", response_model=list[DraftRead])
async def list_pending_drafts(
    db: DBSession,
    conversation_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list:
    return await draft_service.list_pending_drafts(db, conversation_id, limit, offset)


@router.get("/{message_id}", response_model=DraftRead)
async def get_draft(message_id: int, db: DBSession):
    return await draft_service.get_draft(db, message_id)


@router.patch("/{message_id}/edit", response_model=DraftRead)
async def edit_draft(message_id: int, payload: DraftEditPayload, db: DBSession):
    return await draft_service.edit_draft(
        db, message_id, payload.edited_draft, payload.actor
    )


@router.post("/{message_id}/approve", response_model=DraftRead)
async def approve_draft(message_id: int, payload: DraftApprovePayload, db: DBSession):
    return await draft_service.approve_draft(
        db, message_id, payload.actor, payload.edited_draft
    )


@router.post("/{message_id}/reject", response_model=DraftRead)
async def reject_draft(message_id: int, payload: DraftRejectPayload, db: DBSession):
    return await draft_service.reject_draft(db, message_id, payload.actor, payload.reason)


@router.post("/{message_id}/send", response_model=DraftRead)
async def send_draft(message_id: int, db: DBSession):
    return await draft_service.send_approved_draft(db, message_id)
