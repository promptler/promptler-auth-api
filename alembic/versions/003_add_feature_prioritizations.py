"""Add feature_prioritizations table

Revision ID: 003
Revises: 002
Create Date: 2025-12-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create feature_prioritizations table
    op.create_table(
        'feature_prioritizations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('apple_user_id', sa.String(length=255), nullable=False),
        sa.Column('feature_code', sa.String(length=100), nullable=False),
        sa.Column('counter', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['apple_user_id'], ['users.apple_user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('apple_user_id', 'feature_code', name='uq_user_feature')
    )

    # Create indexes on feature_prioritizations table
    op.create_index('idx_feature_code', 'feature_prioritizations', ['feature_code'], unique=False)
    op.create_index('idx_feature_updated', 'feature_prioritizations', ['updated_at'], unique=False)
    op.create_index(op.f('ix_feature_prioritizations_apple_user_id'), 'feature_prioritizations', ['apple_user_id'], unique=False)


def downgrade() -> None:
    # Drop feature_prioritizations table
    op.drop_index(op.f('ix_feature_prioritizations_apple_user_id'), table_name='feature_prioritizations')
    op.drop_index('idx_feature_updated', table_name='feature_prioritizations')
    op.drop_index('idx_feature_code', table_name='feature_prioritizations')
    op.drop_table('feature_prioritizations')
