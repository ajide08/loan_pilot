"""add payment idempotency key

Revision ID: 630a1bf705ad
Revises: 368131f40d3b
Create Date: 2026-10-14 14:11:34.704100

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '630a1bf705ad'
down_revision: Union[str, Sequence[str], None] = '368131f40d3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("repayments"):
        raise RuntimeError("The repayments table does not exist")

    columns = {column["name"] for column in inspector.get_columns("repayments")}
    has_idempotency_key = "idempotency_key" in columns
    has_unique_constraint = any(
        set(constraint.get("column_names") or []) == {"idempotency_key"}
        for constraint in inspector.get_unique_constraints("repayments")
    )

    if not has_idempotency_key or not has_unique_constraint:
        with op.batch_alter_table("repayments") as batch_op:
            if not has_idempotency_key:
                batch_op.add_column(
                    sa.Column("idempotency_key", sa.String(length=100), nullable=True)
                )
            if not has_unique_constraint:
                batch_op.create_unique_constraint(
                    "uq_repayments_idempotency_key",
                    ["idempotency_key"],
                )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("repayments"):
        return

    columns = {column["name"] for column in inspector.get_columns("repayments")}
    if "idempotency_key" not in columns:
        return

    has_unique_constraint = any(
        set(constraint.get("column_names") or []) == {"idempotency_key"}
        for constraint in inspector.get_unique_constraints("repayments")
    )

    with op.batch_alter_table("repayments") as batch_op:
        if has_unique_constraint:
            batch_op.drop_constraint(
                "uq_repayments_idempotency_key",
                type_="unique",
            )
        batch_op.drop_column("idempotency_key")
