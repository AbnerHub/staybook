"""extend reservation status check constraint (checked_in, checked_out)

Revision ID: 004
Revises: 003
Create Date: 2024-01-04 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT = "ck_reservations_status"
_NEW_CONDITION = (
    "status IN ('confirmed', 'checked_in', 'checked_out', 'cancelled')"
)
_OLD_CONDITION = "status IN ('confirmed', 'cancelled')"


def upgrade() -> None:
    # batch_alter_table works on PostgreSQL (native ALTER) and SQLite (copy).
    with op.batch_alter_table("reservations") as batch_op:
        batch_op.drop_constraint(_CONSTRAINT, type_="check")
        batch_op.create_check_constraint(_CONSTRAINT, _NEW_CONDITION)


def downgrade() -> None:
    with op.batch_alter_table("reservations") as batch_op:
        batch_op.drop_constraint(_CONSTRAINT, type_="check")
        batch_op.create_check_constraint(_CONSTRAINT, _OLD_CONDITION)
