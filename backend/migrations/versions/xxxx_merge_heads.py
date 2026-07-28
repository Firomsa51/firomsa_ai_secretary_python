"""merge heads

Revision ID: merge_heads
Revises: phase2, phase3, phase4
Create Date: 2026-07-28
"""
from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = 'merge_heads'
down_revision = ('phase2', 'phase3', 'phase4')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
