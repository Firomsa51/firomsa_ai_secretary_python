"""
Memory service — reads and writes per-user memory entries used by the AI agent.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Provides CRUD operations over the Memory table and formats entries
    for injection into AI prompts.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def retrieve_all(self, user_id: int) -> list[Memory]:
        """Return all memory entries for a user, ordered by creation date."""
        result = await self._db.scalars(
            select(Memory)
            .where(Memory.user_id == user_id)
            .order_by(Memory.created_at.asc())
        )
        return list(result.all())

    async def retrieve_formatted(self, user_id: int) -> str | None:
        """
        Return memories as a formatted string for prompt injection.
        Returns None if no memories exist for the user.
        """
        memories = await self.retrieve_all(user_id)
        if not memories:
            return None
        lines = [f"- {m.key}: {m.value}" for m in memories]
        return "\n".join(lines)

    async def store(self, user_id: int, key: str, value: str) -> Memory:
        """
        Create or overwrite a memory entry for a user by key.
        """
        existing = await self._db.scalar(
            select(Memory).where(Memory.user_id == user_id, Memory.key == key)
        )
        if existing:
            existing.value = value
            await self._db.flush()
            await self._db.refresh(existing)
            logger.debug("Updated memory key=%r for user_id=%s", key, user_id)
            return existing

        mem = Memory(user_id=user_id, key=key, value=value)
        self._db.add(mem)
        await self._db.flush()
        await self._db.refresh(mem)
        logger.debug("Created memory key=%r for user_id=%s", key, user_id)
        return mem

    async def delete(self, user_id: int, key: str) -> bool:
        """Delete a memory entry by key. Returns True if deleted, False if not found."""
        mem = await self._db.scalar(
            select(Memory).where(Memory.user_id == user_id, Memory.key == key)
        )
        if not mem:
            return False
        await self._db.delete(mem)
        logger.debug("Deleted memory key=%r for user_id=%s", key, user_id)
        return True
