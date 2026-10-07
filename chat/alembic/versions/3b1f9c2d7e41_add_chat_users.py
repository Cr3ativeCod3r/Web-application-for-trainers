"""Add chat_users read model

Revision ID: 3b1f9c2d7e41
Revises: ffe36434309f
Create Date: 2026-10-07 20:10:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '3b1f9c2d7e41'
down_revision: Union[str, Sequence[str], None] = 'ffe36434309f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'chat_users',
        sa.Column('user_id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('avatar_url', sa.Text(), nullable=False),
        sa.Column('trainer_username', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('accepts_new_conversations', sa.Boolean(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('version', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('user_id'),
    )


def downgrade() -> None:
    op.drop_table('chat_users')
