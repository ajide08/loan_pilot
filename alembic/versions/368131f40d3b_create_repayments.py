"""create repayments

Revision ID: 368131f40d3b
Revises: 3625e4f298e3
Create Date: 2026-10-12 18:14:43.276284

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '368131f40d3b'
down_revision: Union[str, Sequence[str], None] = '3625e4f298e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("repayments"):
        op.create_table(
            "repayments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("loan_id", sa.Integer(), nullable=False),
            sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("reference", sa.String(length=100), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["loan_id"], ["loans.id"], name="fk_repayments_loan_id_loans"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("reference", name="uq_repayments_reference"),
        )
        return

    expected_columns = {"id", "loan_id", "amount", "status", "reference", "created_at"}
    existing_columns = {column["name"] for column in inspector.get_columns("repayments")}
    missing_columns = expected_columns - existing_columns
    if missing_columns:
        raise RuntimeError(
            "The existing repayments table is missing columns required by this migration: "
            + ", ".join(sorted(missing_columns))
        )

    has_reference_unique = any(
        set(constraint.get("column_names") or []) == {"reference"}
        for constraint in inspector.get_unique_constraints("repayments")
    )
    has_loan_foreign_key = any(
        foreign_key.get("constrained_columns") == ["loan_id"]
        and foreign_key.get("referred_table") == "loans"
        and foreign_key.get("referred_columns") == ["id"]
        for foreign_key in inspector.get_foreign_keys("repayments")
    )

    if not has_reference_unique or not has_loan_foreign_key:
        with op.batch_alter_table("repayments") as batch_op:
            if not has_reference_unique:
                batch_op.create_unique_constraint(
                    "uq_repayments_reference", ["reference"]
                )
            if not has_loan_foreign_key:
                batch_op.create_foreign_key(
                    "fk_repayments_loan_id_loans",
                    "loans",
                    ["loan_id"],
                    ["id"],
                )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("repayments")
