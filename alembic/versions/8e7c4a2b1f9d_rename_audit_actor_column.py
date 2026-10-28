"""Rename audit log actor column.

Revision ID: 8e7c4a2b1f9d
Revises: 56001847b103
Create Date: 2026-10-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e7c4a2b1f9d'
down_revision: Union[str, Sequence[str], None] = '56001847b103'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('ix_audit_logs_action_user_id', table_name='audit_logs')
    op.alter_column(
        'audit_logs',
        'action_user_id',
        new_column_name='actor_user_id',
        existing_type=sa.Integer(),
        existing_nullable=True,
    )
    op.create_index(
        'ix_audit_logs_actor_user_id',
        'audit_logs',
        ['actor_user_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_audit_logs_actor_user_id', table_name='audit_logs')
    op.alter_column(
        'audit_logs',
        'actor_user_id',
        new_column_name='action_user_id',
        existing_type=sa.Integer(),
        existing_nullable=True,
    )
    op.create_index(
        'ix_audit_logs_action_user_id',
        'audit_logs',
        ['action_user_id'],
        unique=False,
    )
