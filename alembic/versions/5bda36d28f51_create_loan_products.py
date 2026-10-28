
"""initial migration

Revision ID: 5bda36d28f51
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "5bda36d28f51"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=225), nullable=False),
        sa.Column("password_hash", sa.String(length=225), nullable=False),
        sa.Column("full_name", sa.String(length=225), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("email"),
    )


def downgrade() -> None:
    op.drop_table("users")
