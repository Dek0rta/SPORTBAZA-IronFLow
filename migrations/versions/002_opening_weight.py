"""Add opening_weight to participants

Revision ID: 002
Revises: 001
Create Date: 2026-03-07 00:00:00.000000

Changes:
  - participants: add opening_weight column (float, nullable)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "participants",
        sa.Column("opening_weight", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("participants", "opening_weight")
