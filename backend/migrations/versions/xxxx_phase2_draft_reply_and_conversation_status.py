"""add draft_reply, conversations, and settings

Revision ID: phase2
Revises: None
Create Date: 2026-07-25
"""
from alembic import op
import sqlalchemy as sa

revision = "phase2"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Jalqaba gabateewwan uumuu
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_reply", sa.Text(), nullable=True),
    )

    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assistant_mode", sa.String(length=32), server_default="suggestive"),
    )

    # 2. Index-oota uumuu
    op.create_index("ix_conversations_status", "conversations", ["status"])
    op.create_index("ix_conversations_last_message_at", "conversations", ["last_message_at"])


def downgrade() -> None:
    op.drop_index("ix_conversations_last_message_at", table_name="conversations")
    op.drop_index("ix_conversations_status", table_name="conversations")
    op.drop_table("settings")
    op.drop_table("messages")
    op.drop_table("conversations")
