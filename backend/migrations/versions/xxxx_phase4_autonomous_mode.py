"""add phase4 autonomous mode fields (message AI signals + settings rules + user trust/block + conversation lock)

Revision ID: phase4
Revises: phase3
Create Date: 2026-07-26
"""
from alembic import op
import sqlalchemy as sa

revision = "phase4"
down_revision = "phase3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("ai_confidence", sa.Float(), nullable=True))
    op.add_column("messages", sa.Column("ai_intent", sa.String(length=64), nullable=True))
    op.add_column("messages", sa.Column("ai_sentiment", sa.String(length=32), nullable=True))
    op.add_column("messages", sa.Column("ai_reasoning", sa.Text(), nullable=True))
    op.add_column(
        "messages",
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column("messages", sa.Column("sent_via", sa.String(length=16), nullable=True))

    op.add_column(
        "conversations",
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default="false"),
    )

    op.add_column(
        "users", sa.Column("is_trusted", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column(
        "users", sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default="false")
    )

    op.add_column(
        "settings",
        sa.Column("allow_auto_reply", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "settings",
        sa.Column("business_hours_only", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "settings",
        sa.Column("business_hours_start_hour", sa.Integer(), nullable=False, server_default="9"),
    )
    op.add_column(
        "settings",
        sa.Column("business_hours_end_hour", sa.Integer(), nullable=False, server_default="18"),
    )
    op.add_column(
        "settings",
        sa.Column(
            "business_hours_timezone", sa.String(length=64), nullable=False, server_default="UTC"
        ),
    )
    op.add_column(
        "settings",
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False, server_default="15"),
    )
    op.add_column(
        "settings",
        sa.Column("max_replies_per_conversation", sa.Integer(), nullable=True)
    )
    op.add_column(
        "settings",
        sa.Column("confidence_threshold", sa.Float(), nullable=False, server_default="0.75"),
    )
    op.add_column(
        "settings",
        sa.Column("trusted_contacts_only", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "settings",
        sa.Column("blocked_keywords", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "settings",
        sa.Column("blocked_categories", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "settings",
        sa.Column("emergency_override", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("settings", "emergency_override")
    op.drop_column("settings", "blocked_categories")
    op.drop_column("settings", "blocked_keywords")
    op.drop_column("settings", "trusted_contacts_only")
    op.drop_column("settings", "confidence_threshold")
    op.drop_column("settings", "max_replies_per_conversation")
    op.drop_column("settings", "cooldown_minutes")
    op.drop_column("settings", "business_hours_timezone")
    op.drop_column("settings", "business_hours_end_hour")
    op.drop_column("settings", "business_hours_start_hour")
    op.drop_column("settings", "business_hours_only")
    op.drop_column("settings", "allow_auto_reply")

    op.drop_column("users", "is_blocked")
    op.drop_column("users", "is_trusted")

    op.drop_column("conversations", "is_locked")

    op.drop_column("messages", "sent_via")
    op.drop_column("messages", "requires_human_review")
    op.drop_column("messages", "ai_reasoning")
    op.drop_column("messages", "ai_sentiment")
    op.drop_column("messages", "ai_intent")
    op.drop_column("messages", "ai_confidence")
