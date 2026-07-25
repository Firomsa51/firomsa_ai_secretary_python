"""
Conversation ORM model — a grouped thread of messages with a single user.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.message import Message


class Conversation(Base):
    """A logical conversation thread between the owner and a Telegram contact."""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(
        String(512), nullable=True,
        comment="Auto-generated or user-provided title for the conversation",
    )
    category: Mapped[str | None] = mapped_column(
        String(128), nullable=True,
        comment="e.g. work, personal, networking, support",
    )
    priority: Mapped[str] = mapped_column(
        String(32), default="normal", nullable=False,
        comment="low | normal | high | urgent",
    )
    # ── Phase 2 additions ─────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(16), default="open", nullable=False, index=True,
        comment="open | closed — only 'open' conversations receive new incoming messages",
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        comment="Timestamp of the most recent message in this conversation",
    )
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.timestamp",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Conversation id={self.id} user_id={self.user_id} "
            f"status={self.status!r} category={self.category!r} priority={self.priority!r}>"
        )
