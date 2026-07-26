"""
User ORM model — represents a Telegram user known to the secretary.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.memory import Memory


class User(Base):
    """A Telegram user whose conversations are tracked by the secretary."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True,
        comment="Telegram user ID (may exceed 32-bit range)",
    )
    username: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Telegram @username without the @ prefix",
    )
    first_name: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Telegram display first name",
    )
    last_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
    )
    is_trusted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false",
        comment="Trusted contacts are eligible for autonomous auto-replies",
    )
    is_blocked: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false",
        comment="Blocked senders never receive automatic replies (drafts still generated)",
    )
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    memories: Mapped[list["Memory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} telegram_id={self.telegram_id} username={self.username!r}>"
