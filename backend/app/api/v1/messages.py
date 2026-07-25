"""Message CRUD endpoints."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.dependencies import DBSession
from app.models.message import Message
from app.schemas.message import MessageCreate, MessageRead

router = APIRouter()


@router.post("/", response_model=MessageRead, status_code=201)
async def create_message(payload: MessageCreate, db: DBSession) -> Message:
    msg = Message(**payload.model_dump())
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return msg


@router.get("/{message_id}", response_model=MessageRead)
async def get_message(message_id: int, db: DBSession) -> Message:
    msg = await db.get(Message, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found.")
    return msg


@router.get("/", response_model=list[MessageRead])
async def list_messages(
    db: DBSession,
    conversation_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Message]:
    query = (
        select(Message)
        .order_by(Message.timestamp.asc())
        .limit(limit)
        .offset(offset)
    )
    if conversation_id is not None:
        query = query.where(Message.conversation_id == conversation_id)
    result = await db.scalars(query)
    return list(result.all())
