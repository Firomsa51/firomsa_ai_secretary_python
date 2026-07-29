"""
Memory ORM model — key/value store for per-user context the AI can recall.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Memory(Base):
    """
    A persistent memory entry for a specific user.
    """

    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Semantic label for this memory entry",
    )

    value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Stored value",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="memories",
    )

    def __repr__(self) -> str:
        return (
            f"<Memory id={self.id} "
            f"user_id={self.user_id} "
            f"key={self.key!r}>"
        )
