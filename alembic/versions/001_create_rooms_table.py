"""create rooms table

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("room_number", sa.String(length=10), nullable=False),
        sa.Column("room_type", sa.String(), nullable=False),
        sa.Column(
            "price_per_night", sa.Numeric(precision=8, scale=2), nullable=False
        ),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="disponible",
        ),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("floor", sa.Integer(), nullable=True),
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
        sa.UniqueConstraint("room_number"),
        sa.CheckConstraint(
            "room_type IN ('individual', 'doble', 'suite')",
            name="ck_rooms_room_type",
        ),
        sa.CheckConstraint(
            "price_per_night > 0 AND price_per_night <= 999999.99",
            name="ck_rooms_price_per_night",
        ),
        sa.CheckConstraint(
            "capacity >= 1 AND capacity <= 20",
            name="ck_rooms_capacity",
        ),
        sa.CheckConstraint(
            "status IN ('disponible', 'ocupada', 'mantenimiento')",
            name="ck_rooms_status",
        ),
    )

    # Create indexes
    op.create_index("ix_rooms_room_number", "rooms", ["room_number"])
    op.create_index("ix_rooms_status", "rooms", ["status"])


def downgrade() -> None:
    op.drop_index("ix_rooms_status", table_name="rooms")
    op.drop_index("ix_rooms_room_number", table_name="rooms")
    op.drop_table("rooms")
