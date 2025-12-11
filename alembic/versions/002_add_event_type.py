"""Add event_type column to device_snapshots

Revision ID: 002
Revises: 001
Create Date: 2025-12-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add event_type column with default value 'sign_in'
    op.add_column(
        'device_snapshots',
        sa.Column('event_type', sa.String(length=20), nullable=False, server_default='sign_in')
    )

    # Create index on event_type and captured_at
    op.create_index('idx_snapshot_event_type', 'device_snapshots', ['event_type', 'captured_at'], unique=False)

    # Create standalone index on event_type for filtering
    op.create_index(op.f('ix_device_snapshots_event_type'), 'device_snapshots', ['event_type'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_device_snapshots_event_type'), table_name='device_snapshots')
    op.drop_index('idx_snapshot_event_type', table_name='device_snapshots')

    # Drop column
    op.drop_column('device_snapshots', 'event_type')
