"""Initial schema for users and device snapshots

Revision ID: 001
Revises:
Create Date: 2024-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('apple_user_id', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('latest_device_profile', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(), nullable=False),
        sa.Column('last_updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('apple_user_id')
    )

    # Create indexes on users table
    op.create_index('idx_user_email', 'users', ['email'], unique=False)
    op.create_index('idx_user_last_updated', 'users', ['last_updated_at'], unique=False)
    op.create_index(op.f('ix_users_apple_user_id'), 'users', ['apple_user_id'], unique=False)

    # Create device_snapshots table
    op.create_table(
        'device_snapshots',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('apple_user_id', sa.String(length=255), nullable=False),
        sa.Column('device_model', sa.String(length=100), nullable=True),
        sa.Column('device_name', sa.String(length=255), nullable=True),
        sa.Column('system_name', sa.String(length=50), nullable=True),
        sa.Column('system_version', sa.String(length=50), nullable=True),
        sa.Column('locale', sa.String(length=10), nullable=True),
        sa.Column('region', sa.String(length=10), nullable=True),
        sa.Column('time_zone', sa.String(length=100), nullable=True),
        sa.Column('app_version', sa.String(length=50), nullable=True),
        sa.Column('app_build', sa.String(length=50), nullable=True),
        sa.Column('raw_profile', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('captured_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['apple_user_id'], ['users.apple_user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes on device_snapshots table
    op.create_index('idx_snapshot_user_captured', 'device_snapshots', ['apple_user_id', 'captured_at'], unique=False)
    op.create_index(op.f('ix_device_snapshots_apple_user_id'), 'device_snapshots', ['apple_user_id'], unique=False)


def downgrade() -> None:
    # Drop device_snapshots table
    op.drop_index(op.f('ix_device_snapshots_apple_user_id'), table_name='device_snapshots')
    op.drop_index('idx_snapshot_user_captured', table_name='device_snapshots')
    op.drop_table('device_snapshots')

    # Drop users table
    op.drop_index(op.f('ix_users_apple_user_id'), table_name='users')
    op.drop_index('idx_user_last_updated', table_name='users')
    op.drop_index('idx_user_email', table_name='users')
    op.drop_table('users')
