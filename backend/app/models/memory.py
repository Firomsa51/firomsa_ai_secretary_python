"""
Memory ORM model — key/value store for per-user context the AI can recall.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Memory(Base):
    """
    A persistent memory entry for a specific user.

    The AI secretary reads these entries when composing replies so it can
    remember preferences, important facts, and prior commitments.
    """

    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Short semantic key, e.g. "preferred_language", "working_hours"
    key: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Semantic label for this memory entry",
    )
    value: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Stored value — free-form text or JSON string",
    )
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="memories")

    def __repr__(self) -> str:
        return f"<Memory id={self.id} user_id={self.user_id} key={self.key!r}>"
