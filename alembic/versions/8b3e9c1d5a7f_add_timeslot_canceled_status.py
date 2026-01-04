"""add timeslot canceled status and constraints

Revision ID: 8b3e9c1d5a7f
Revises: 26b27b54e86b
Create Date: 2026-01-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8b3e9c1d5a7f"
down_revision: Union[str, Sequence[str], None] = "26b27b54e86b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE timeslotstatus ADD VALUE IF NOT EXISTS 'CANCELED'")

    op.execute(
        "ALTER TABLE timeslots DROP CONSTRAINT IF EXISTS timeslot_no_overlap_per_room"
    )
    op.execute(
        "ALTER TABLE timeslots ADD CONSTRAINT timeslot_no_overlap_available_per_room "
        "EXCLUDE USING gist (room_id WITH =, "
        "tstzrange(start_datetime, end_datetime, '[)') WITH &&) "
        "WHERE (status != 'CANCELED')"
    )

    op.drop_constraint("uq_timeslot_unique_range", "timeslots", type_="unique")
    op.create_index(
        "uq_timeslot_unique_range_active",
        "timeslots",
        ["room_id", "start_datetime", "end_datetime"],
        unique=True,
        postgresql_where=sa.text("status != 'CANCELED'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_index("uq_timeslot_unique_range_active", table_name="timeslots")
    op.create_unique_constraint(
        "uq_timeslot_unique_range",
        "timeslots",
        ["room_id", "start_datetime", "end_datetime"],
    )

    op.execute(
        "ALTER TABLE timeslots DROP CONSTRAINT IF EXISTS timeslot_no_overlap_available_per_room"
    )
    op.execute(
        "ALTER TABLE timeslots ADD CONSTRAINT timeslot_no_overlap_per_room "
        "EXCLUDE USING gist (room_id WITH =, "
        "tstzrange(start_datetime, end_datetime, '[]') WITH &&)"
    )

    # Enum value removal is not supported in Postgres; leave 'CANCELED' in place.
