"""add room booking duration constraints

Revision ID: b7c2f0d1f9a1
Revises: 26b27b54e86b
Create Date: 2026-01-04 02:40:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b7c2f0d1f9a1"
down_revision: Union[str, Sequence[str], None] = "26b27b54e86b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        "ck_rooms_min_booking_duration_minutes_positive",
        "rooms",
        "min_booking_duration_minutes > 0",
    )
    op.create_check_constraint(
        "ck_rooms_booking_step_minutes_positive",
        "rooms",
        "booking_step_minutes > 0",
    )
    op.create_check_constraint(
        "ck_rooms_booking_step_lte_min_duration",
        "rooms",
        "booking_step_minutes <= min_booking_duration_minutes",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_rooms_booking_step_lte_min_duration",
        "rooms",
        type_="check",
    )
    op.drop_constraint(
        "ck_rooms_booking_step_minutes_positive",
        "rooms",
        type_="check",
    )
    op.drop_constraint(
        "ck_rooms_min_booking_duration_minutes_positive",
        "rooms",
        type_="check",
    )
