"""Add monetization_events table

Revision ID: 004
Revises: 003
Create Date: 2026-04-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create monetization_events table
    op.create_table(
        'monetization_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('apple_user_id', sa.String(length=255), nullable=True),
        sa.Column('device_id', sa.String(length=255), nullable=True),
        sa.Column('event_name', sa.String(length=100), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('app_version', sa.String(length=50), nullable=True),
        sa.Column('app_build', sa.String(length=50), nullable=True),
        sa.Column('captured_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['apple_user_id'],
            ['users.apple_user_id'],
            ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_monetization_user', 'monetization_events', ['apple_user_id'], unique=False)
    op.create_index('idx_monetization_device', 'monetization_events', ['device_id'], unique=False)
    op.create_index('idx_monetization_event_name', 'monetization_events', ['event_name'], unique=False)
    op.create_index('idx_monetization_event_captured', 'monetization_events', ['event_name', 'captured_at'], unique=False)
    op.create_index('idx_monetization_user_captured', 'monetization_events', ['apple_user_id', 'captured_at'], unique=False)
    op.create_index('idx_monetization_captured', 'monetization_events', ['captured_at'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_monetization_captured', table_name='monetization_events')
    op.drop_index('idx_monetization_user_captured', table_name='monetization_events')
    op.drop_index('idx_monetization_event_captured', table_name='monetization_events')
    op.drop_index('idx_monetization_event_name', table_name='monetization_events')
    op.drop_index('idx_monetization_device', table_name='monetization_events')
    op.drop_index('idx_monetization_user', table_name='monetization_events')
    # Drop table
    op.drop_table('monetization_events')
