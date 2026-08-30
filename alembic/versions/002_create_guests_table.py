"""create guests table

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "guests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("identification_type", sa.String(), nullable=False),
        sa.Column("identification_number", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint(
            "identification_type",
            "identification_number",
            name="uq_guests_identification",
        ),
        sa.CheckConstraint(
            "identification_type IN "
            "('national_id', 'passport', 'driver_license', 'other')",
            name="ck_guests_identification_type",
        ),
    )

    # Create index
    op.create_index("ix_guests_email", "guests", ["email"])


def downgrade() -> None:
    op.drop_index("ix_guests_email", table_name="guests")
    op.drop_table("guests")
