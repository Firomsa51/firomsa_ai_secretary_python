"""
Settings ORM model — global assistant configuration stored in the database.
Also used as the secure store for the Telegram StringSession.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Settings(Base):
    """
    Application-level settings for the AI secretary (singleton row).
    Use SettingsService to fetch or initialise it.
    """

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # "passive" | "suggestive" | "autonomous"
    assistant_mode: Mapped[str] = mapped_column(
        String(32),
        default="passive",
        nullable=False,
        comment=(
            "passive   — reads and categorises messages, no auto-replies\n"
            "suggestive — drafts replies for owner approval\n"
            "autonomous — sends replies automatically"
        ),
    )
    auto_reply_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    language: Mapped[str] = mapped_column(
        String(10), default="en", nullable=False,
        comment="BCP-47 language tag for AI responses, e.g. 'en', 'am'",
    )

    # ── Telegram session (Phase 2) ────────────────────────────────────────────
    # Stored in the DB so it survives restarts on stateless cloud deployments.
    # This value is NEVER returned by any public API endpoint.
    telegram_session_string: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Telethon StringSession — treat as a secret; never expose via API",
    )

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Settings id={self.id} mode={self.assistant_mode!r}>"
