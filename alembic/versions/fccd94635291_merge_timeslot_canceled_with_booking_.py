"""merge timeslot canceled with booking duration

Revision ID: fccd94635291
Revises: 8b3e9c1d5a7f, b7c2f0d1f9a1
Create Date: 2026-01-04 12:43:41.634139

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fccd94635291'
down_revision: Union[str, Sequence[str], None] = ('8b3e9c1d5a7f', 'b7c2f0d1f9a1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
