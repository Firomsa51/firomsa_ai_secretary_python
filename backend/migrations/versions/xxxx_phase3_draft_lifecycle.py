"""add draft lifecycle fields (edited_draft, draft_status, approved_at, sent_at, approved_by) to messages

Revision ID: phase3
Revises: phase2
Create Date: 2026-07-26
"""
from alembic import op
import sqlalchemy as sa

revision = "phase3"
down_revision = "phase2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("edited_draft", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("draft_status", sa.String(length=16), nullable=True))
    op.add_column("messages", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("messages", sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("messages", sa.Column("approved_by", sa.String(length=255), nullable=True))
    op.create_index("ix_messages_draft_status", "messages", ["draft_status"])
    op.execute(
        "UPDATE messages SET draft_status = 'pending' "
        "WHERE draft_reply IS NOT NULL AND draft_status IS NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_messages_draft_status", table_name="messages")
    op.drop_column("messages", "approved_by")
    op.drop_column("messages", "sent_at")
    op.drop_column("messages", "approved_at")
    op.drop_column("messages", "draft_status")
    op.drop_column("messages", "edited_draft")
