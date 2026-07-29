"""
Settings ORM model — global assistant configuration stored in the database.
Also used as the secure store for the Telegram StringSession.
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Settings(Base):
    """
    Application-level settings for the AI secretary (singleton row).
    Use settings_service.get_or_create_settings() to fetch or initialise it.
    """

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    assistant_mode: Mapped[str] = mapped_column(
        String(32),
        default="suggestive",
        nullable=False,
        comment=(
            "passive    (OFF)    — reads and categorises messages, no drafts\n"
            "suggestive (ASSIST) — default; drafts replies for owner approval\n"
            "autonomous (AUTO)   — may auto-send when allow_auto_reply and all "
            "Phase 4 safety gates pass; otherwise behaves like ASSIST"
        ),
    )

    auto_reply_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    language: Mapped[str] = mapped_column(
        String(10),
        default="en",
        nullable=False,
        comment="BCP-47 language tag for AI responses, e.g. 'en', 'am'",
    )

    telegram_session_string: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Telethon StringSession — treat as a secret; never expose via API",
    )

    # ------------------------------------------------------------------
    # Autonomous mode configuration
    # ------------------------------------------------------------------

    allow_auto_reply: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default="false",
    )

    business_hours_only: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default="false",
    )

    business_hours_start_hour: Mapped[int] = mapped_column(
        Integer,
        default=9,
        nullable=False,
        server_default="9",
    )

    business_hours_end_hour: Mapped[int] = mapped_column(
        Integer,
        default=18,
        nullable=False,
        server_default="18",
    )

    business_hours_timezone: Mapped[str] = mapped_column(
        String(64),
        default="UTC",
        nullable=False,
        server_default="UTC",
    )

    cooldown_minutes: Mapped[int] = mapped_column(
        Integer,
        default=15,
        nullable=False,
        server_default="15",
    )

    max_replies_per_conversation: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    confidence_threshold: Mapped[float] = mapped_column(
        Float,
        default=0.75,
        nullable=False,
        server_default="0.75",
    )

    trusted_contacts_only: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default="false",
    )

    blocked_keywords: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    blocked_categories: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    emergency_override: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default="false",
    )

    # ------------------------------------------------------------------
    # IMPORTANT FIX
    # Use timezone-naive datetime because PostgreSQL column is
    # TIMESTAMP WITHOUT TIME ZONE.
    # ------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<Settings id={self.id} "
            f"mode={self.assistant_mode!r} "
            f"allow_auto_reply={self.allow_auto_reply}>"
        )
