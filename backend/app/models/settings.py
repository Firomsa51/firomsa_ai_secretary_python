"""
Settings ORM model — global assistant configuration stored in the database.
Also used as the secure store for the Telegram StringSession.
"""

from datetime import datetime, timezone

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
        Boolean, default=False, nullable=False
    )
    language: Mapped[str] = mapped_column(
        String(10), default="en", nullable=False,
        comment="BCP-47 language tag for AI responses, e.g. 'en', 'am'",
    )

    telegram_session_string: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Telethon StringSession — treat as a secret; never expose via API",
    )

    # ── Phase 4 — autonomous mode configuration ──────────────────────────────
    allow_auto_reply: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false",
        comment="Master switch: must be true for 'autonomous' mode to ever auto-send",
    )
    business_hours_only: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false",
    )
    business_hours_start_hour: Mapped[int] = mapped_column(
        Integer, default=9, nullable=False, server_default="9",
        comment="Hour (0-23, local to business_hours_timezone) auto-replies may start",
    )
    business_hours_end_hour: Mapped[int] = mapped_column(
        Integer, default=18, nullable=False, server_default="18",
        comment="Hour (0-23, local to business_hours_timezone) auto-replies must stop",
    )
    business_hours_timezone: Mapped[str] = mapped_column(
        String(64), default="UTC", nullable=False, server_default="UTC",
        comment="IANA timezone name used to evaluate business_hours_*",
    )
    cooldown_minutes: Mapped[int] = mapped_column(
        Integer, default=15, nullable=False, server_default="15",
        comment="Minimum minutes between two auto-sent replies in the same conversation",
    )
    max_replies_per_conversation: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Cap on total auto-sent replies per conversation; null = unlimited",
    )
    confidence_threshold: Mapped[float] = mapped_column(
        Float, default=0.75, nullable=False, server_default="0.75",
        comment="Minimum ai_confidence (0.0-1.0) required before auto-sending",
    )
    trusted_contacts_only: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false",
        comment="If true, only User.is_trusted senders are eligible for auto-reply",
    )
    blocked_keywords: Mapped[list] = mapped_column(
        JSON, default=list, nullable=False,
        comment="List of case-insensitive substrings; any match blocks auto-send",
    )
    blocked_categories: Mapped[list] = mapped_column(
        JSON, default=list, nullable=False,
        comment="Conversation categories that are never auto-replied to",
    )
    emergency_override: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false",
        comment=(
            "If true, an 'urgent'-priority conversation may bypass "
            "business_hours_only and cooldown_minutes (all other gates still apply)"
        ),
    )

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Settings id={self.id} mode={self.assistant_mode!r} allow_auto_reply={self.allow_auto_reply}>"
