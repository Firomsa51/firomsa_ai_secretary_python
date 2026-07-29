"""
Message ORM model — an individual message within a conversation.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
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

    sender: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="owner | contact | ai",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full message text",
    )

    telegram_message_id: Mapped[int | None] = mapped_column(
        nullable=True,
        index=True,
        comment="Original Telegram message ID",
    )

    draft_reply: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    edited_draft: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    draft_status: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        index=True,
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    approved_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    ai_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    ai_intent: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    ai_sentiment: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    ai_reasoning: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    requires_human_review: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    sent_via: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )

    def __repr__(self) -> str:
        return (
            f"<Message id={self.id} "
            f"conversation_id={self.conversation_id} "
            f"sender={self.sender!r} "
            f"draft_status={self.draft_status!r}>"
        )
