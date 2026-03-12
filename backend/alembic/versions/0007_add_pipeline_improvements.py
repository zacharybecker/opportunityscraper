"""add pipeline improvements

Revision ID: 0007_pipeline
Revises: 0006_proposals
Create Date: 2026-03-11

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0007_pipeline'
down_revision: Union[str, None] = '0006_proposals'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add position column to pipeline_entries
    op.add_column('pipeline_entries', sa.Column('position', sa.Integer(), server_default='0'))

    # Create pipeline_comments table
    op.create_table('pipeline_comments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('pipeline_entry_id', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['pipeline_entry_id'], ['pipeline_entries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('pipeline_comments')
    op.drop_column('pipeline_entries', 'position')
