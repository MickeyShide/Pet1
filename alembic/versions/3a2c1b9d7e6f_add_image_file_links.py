"""add image file links

Revision ID: 3a2c1b9d7e6f
Revises: b0adc0330707
Create Date: 2026-01-07 00:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3a2c1b9d7e6f"
down_revision: Union[str, Sequence[str], None] = "b0adc0330707"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.add_column("files", sa.Column("public_url", sa.String(), nullable=True))

    op.add_column("images", sa.Column("file_id", sa.Integer(), nullable=False))
    op.add_column("images", sa.Column("room_id", sa.Integer(), nullable=True))
    op.add_column("images", sa.Column("location_id", sa.Integer(), nullable=True))

    op.create_foreign_key(
        "fk_images_file_id",
        "images",
        "files",
        ["file_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_images_room_id",
        "images",
        "rooms",
        ["room_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_images_location_id",
        "images",
        "locations",
        ["location_id"],
        ["id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_constraint("fk_images_location_id", "images", type_="foreignkey")
    op.drop_constraint("fk_images_room_id", "images", type_="foreignkey")
    op.drop_constraint("fk_images_file_id", "images", type_="foreignkey")

    op.drop_column("images", "location_id")
    op.drop_column("images", "room_id")
    op.drop_column("images", "file_id")

    op.drop_column("files", "public_url")
