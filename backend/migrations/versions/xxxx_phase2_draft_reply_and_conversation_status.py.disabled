"""add draft_reply to messages, status/last_message_at to conversations, default assistant_mode

Revision ID: <FILL_IN>
Revises: <SET_TO_YOUR_CURRENT_ALEMBIC_HEAD>
Create Date: 2026-07-25
"""
from alembic import op
import sqlalchemy as sa

# TODO: fill these in based on `alembic heads` in your repo before running.
revision = "<FILL_IN>"
down_revision = "<SET_TO_YOUR_CURRENT_ALEMBIC_HEAD>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("draft_reply", sa.Text(), nullable=True))

    op.add_column(
        "conversations",
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_conversations_status", "conversations", ["status"])
    op.create_index("ix_conversations_last_message_at", "conversations", ["last_message_at"])

    # Default assistant_mode: "passive" -> "suggestive" (OFF -> ASSIST)
    op.alter_column("settings", "assistant_mode", server_default="suggestive")
    op.execute(
        "UPDATE settings SET assistant_mode = 'suggestive' WHERE assistant_mode = 'passive'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE settings SET assistant_mode = 'passive' WHERE assistant_mode = 'suggestive'"
    )
    op.alter_column("settings", "assistant_mode", server_default="passive")

    op.drop_index("ix_conversations_last_message_at", table_name="conversations")
    op.drop_index("ix_conversations_status", table_name="conversations")
    op.drop_column("conversations", "last_message_at")
    op.drop_column("conversations", "status")

    op.drop_column("messages", "draft_reply")
