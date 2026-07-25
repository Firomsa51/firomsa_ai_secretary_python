"""Conversation CRUD endpoints."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.dependencies import DBSession
from app.models.conversation import Conversation
from app.schemas.conversation import ConversationCreate, ConversationRead

router = APIRouter()


@router.post("/", response_model=ConversationRead, status_code=201)
async def create_conversation(payload: ConversationCreate, db: DBSession) -> Conversation:
    convo = Conversation(**payload.model_dump())
    db.add(convo)
    await db.flush()
    await db.refresh(convo)
    return convo


@router.get("/{conversation_id}", response_model=ConversationRead)
async def get_conversation(conversation_id: int, db: DBSession) -> Conversation:
    convo = await db.get(Conversation, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return convo


@router.get("/", response_model=list[ConversationRead])
async def list_conversations(
    db: DBSession, user_id: int | None = None, limit: int = 50, offset: int = 0
) -> list[Conversation]:
    query = select(Conversation).order_by(Conversation.created_at.desc()).limit(limit).offset(offset)
    if user_id is not None:
        query = query.where(Conversation.user_id == user_id)
    result = await db.scalars(query)
    return list(result.all())


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: int, db: DBSession) -> None:
    convo = await db.get(Conversation, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    await db.delete(convo)
