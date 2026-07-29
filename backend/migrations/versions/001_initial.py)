"""initial baseline

Revision ID: head_baseline
Revises: None
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa

revision = "head_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("is_trusted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default="false"),
    )

    # 2. Conversations table
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_conversations_status", "conversations", ["status"])
    op.create_index("ix_conversations_last_message_at", "conversations", ["last_message_at"])

    # 3. Messages table
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_reply", sa.Text(), nullable=True),
        sa.Column("edited_draft", sa.Text(), nullable=True),
        sa.Column("draft_status", sa.String(length=16), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("ai_intent", sa.String(length=64), nullable=True),
        sa.Column("ai_sentiment", sa.String(length=32), nullable=True),
        sa.Column("ai_reasoning", sa.Text(), nullable=True),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sent_via", sa.String(length=16), nullable=True),
    )
    op.create_index("ix_messages_draft_status", "messages", ["draft_status"])

    # 4. Settings table
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assistant_mode", sa.String(length=32), server_default="suggestive"),
        sa.Column("allow_auto_reply", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("business_hours_only", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("business_hours_start_hour", sa.Integer(), nullable=False, server_default="9"),
        sa.Column("business_hours_end_hour", sa.Integer(), nullable=False, server_default="18"),
        sa.Column("business_hours_timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("max_replies_per_conversation", sa.Integer(), nullable=True),
        sa.Column("confidence_threshold", sa.Float(), nullable=False, server_default="0.75"),
        sa.Column("trusted_contacts_only", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("blocked_keywords", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("blocked_categories", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("emergency_override", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_table("settings")
    op.drop_index("ix_messages_draft_status", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_last_message_at", table_name="conversations")
    op.drop_index("ix_conversations_status", table_name="conversations")
    op.drop_table("conversations")
    op.drop_table("users")
