"""create reservations table

Revision ID: 003
Revises: 002
Create Date: 2024-01-03 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reservations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("guest_id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("check_in_date", sa.Date(), nullable=False),
        sa.Column("check_out_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="confirmed",
        ),
        sa.Column(
            "total_price", sa.Numeric(precision=10, scale=2), nullable=False
        ),
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
        sa.ForeignKeyConstraint(
            ["guest_id"], ["guests.id"], name="fk_reservations_guest_id"
        ),
        sa.ForeignKeyConstraint(
            ["room_id"], ["rooms.id"], name="fk_reservations_room_id"
        ),
        sa.CheckConstraint(
            "status IN ('confirmed', 'cancelled')",
            name="ck_reservations_status",
        ),
        sa.CheckConstraint(
            "check_out_date > check_in_date",
            name="ck_reservations_dates",
        ),
    )

    # Create indexes
    op.create_index(
        "ix_reservations_guest_id", "reservations", ["guest_id"]
    )
    op.create_index("ix_reservations_room_id", "reservations", ["room_id"])
    op.create_index("ix_reservations_status", "reservations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_reservations_status", table_name="reservations")
    op.drop_index("ix_reservations_room_id", table_name="reservations")
    op.drop_index("ix_reservations_guest_id", table_name="reservations")
    op.drop_table("reservations")
