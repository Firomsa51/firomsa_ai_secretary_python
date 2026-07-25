"""
Message ORM model — an individual message within a conversation.
"""

from datetime import datetime, timezone

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class Message(Base):
    """A single message exchanged in a Telegram conversation."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # "owner" | "contact" | "ai"
    sender: Mapped[str] = mapped_column(
        nullable=False,
        comment="Who sent the message: 'owner', 'contact', or 'ai'",
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Full message text",
    )
    telegram_message_id: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="Original Telegram message ID for deduplication",
    )
    timestamp: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return (
            f"<Message id={self.id} conversation_id={self.conversation_id} "
            f"sender={self.sender!r} timestamp={self.timestamp}>"
        )
