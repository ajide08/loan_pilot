
"""create loan applications

Revision ID: 63be69b5d902
Revises: 496baac2e2b3
"""

from alembic import op
import sqlalchemy as sa

revision = "63be69b5d902"
down_revision = "496baac2e2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loan_applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("borrower_id", sa.Integer(), nullable=False),
        sa.Column("loan_product_id", sa.Integer(), nullable=False),
        sa.Column("requested_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("requested_term_months", sa.Integer(), nullable=False),
        sa.Column("monthly_income", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["borrower_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["loan_product_id"], ["loan_products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("loan_applications")
