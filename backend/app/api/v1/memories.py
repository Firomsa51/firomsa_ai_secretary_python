"""Memory CRUD endpoints."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.dependencies import DBSession
from app.models.memory import Memory
from app.schemas.memory import MemoryCreate, MemoryRead

router = APIRouter()


@router.post("/", response_model=MemoryRead, status_code=201)
async def create_memory(payload: MemoryCreate, db: DBSession) -> Memory:
    mem = Memory(**payload.model_dump())
    db.add(mem)
    await db.flush()
    await db.refresh(mem)
    return mem


@router.get("/", response_model=list[MemoryRead])
async def list_memories(
    db: DBSession, user_id: int | None = None, limit: int = 100, offset: int = 0
) -> list[Memory]:
    query = select(Memory).order_by(Memory.created_at.desc()).limit(limit).offset(offset)
    if user_id is not None:
        query = query.where(Memory.user_id == user_id)
    result = await db.scalars(query)
    return list(result.all())


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(memory_id: int, db: DBSession) -> None:
    mem = await db.get(Memory, memory_id)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found.")
    await db.delete(mem)
