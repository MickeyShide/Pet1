"""add timeslot status default

Revision ID: 9b5f3c1a2d4e
Revises: fccd94635291
Create Date: 2026-01-05 03:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9b5f3c1a2d4e"
down_revision: Union[str, Sequence[str], None] = "fccd94635291"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        "ALTER TABLE timeslots ALTER COLUMN status "
        "SET DEFAULT 'AVAILABLE'::timeslotstatus"
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("ALTER TABLE timeslots ALTER COLUMN status DROP DEFAULT")
