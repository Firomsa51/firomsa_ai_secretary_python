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
    draft_reply: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment=(
            "AI-generated draft reply for this incoming message. "
            "Never sent automatically — the original message content is untouched."
        ),
    )
    edited_draft: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Owner-edited version of draft_reply. If set, this is what gets sent.",
    )
    draft_status: Mapped[str | None] = mapped_column(
        String(16), nullable=True, index=True,
        comment="pending | approved | rejected | sent — null if no draft was generated",
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    approved_by: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Identifier of who approved this draft ('autonomous_engine' for Phase 4 auto-sends)",
    )
    # ── Phase 4 additions — AI signal + autonomous-send tracking ─────────────
    ai_confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Model's self-reported confidence (0.0-1.0) that an automatic reply would be safe/accurate",
    )
    ai_intent: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="Short label for the detected intent, e.g. 'schedule_meeting'",
    )
    ai_sentiment: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="positive | neutral | negative | urgent",
    )
    ai_reasoning: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Model's one-line explanation for its confidence score",
    )
    requires_human_review: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false",
        comment="AI-flagged: financial/legal/medical/auth-code/human-request content — never auto-send",
    )
    sent_via: Mapped[str | None] = mapped_column(
        String(16), nullable=True,
        comment="'manual' (owner approved) | 'auto' (autonomous engine) — null if never sent",
    )
    timestamp: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return (
            f"<Message id={self.id} conversation_id={self.conversation_id} "
            f"sender={self.sender!r} draft_status={self.draft_status!r}>"
        )
