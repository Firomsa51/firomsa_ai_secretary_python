"""create initial messages table

Revision ID: phase1_initial
Revises: None
Create Date: 2026-07-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'phase1_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        # Asirratti kolonniiwwan gabatee messages keessatti barbaaddu dabali
    )

def downgrade():
    op.drop_table('messages')
