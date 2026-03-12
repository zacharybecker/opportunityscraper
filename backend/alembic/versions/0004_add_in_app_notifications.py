"""add in-app notifications

Revision ID: 0004_in_app_notifs
Revises: 0003_local_auth
Create Date: 2026-03-11

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0004_in_app_notifs'
down_revision: Union[str, None] = '0003_local_auth'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('in_app_notifications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), server_default='system'),
        sa.Column('link', sa.String(2048), nullable=True),
        sa.Column('is_read', sa.Boolean(), server_default='false'),
        sa.Column('opportunity_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_notif_user_read', 'in_app_notifications', ['user_id', 'is_read', 'created_at'])


def downgrade() -> None:
    op.drop_index('idx_notif_user_read', table_name='in_app_notifications')
    op.drop_table('in_app_notifications')
