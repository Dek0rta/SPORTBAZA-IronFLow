"""Iron Flow v2 — Add formula, QR check-in and Records Vault

Revision ID: 001
Revises:
Create Date: 2026-02-28 00:00:00.000000

Changes:
  - tournaments: add scoring_formula column (default: 'total')
  - participants: add qr_token column (UUID, unique, nullable)
  - participants: add checked_in column (boolean, default false)
  - Create platform_records table for all-time records vault
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── tournaments: scoring formula ──────────────────────────────────────────
    op.add_column(
        "tournaments",
        sa.Column(
            "scoring_formula",
            sa.String(20),
            nullable=False,
            server_default="total",
        ),
    )

    # ── participants: QR check-in ──────────────────────────────────────────────
    op.add_column(
        "participants",
        sa.Column("qr_token", sa.String(36), nullable=True, unique=True),
    )
    op.add_column(
        "participants",
        sa.Column(
            "checked_in",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # ── Create platform_records table ─────────────────────────────────────────
    op.create_table(
        "platform_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("lift_type", sa.String(20), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("formula_score", sa.Float(), nullable=True),
        sa.Column("formula_type", sa.String(20), nullable=True),
        sa.Column("gender", sa.String(5), nullable=False),
        sa.Column("age_category", sa.String(20), nullable=False),
        sa.Column("weight_category_name", sa.String(50), nullable=False),
        sa.Column("athlete_name", sa.String(255), nullable=False),
        sa.Column(
            "tournament_id",
            sa.Integer(),
            sa.ForeignKey("tournaments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("tournament_name", sa.String(255), nullable=False),
        sa.Column(
            "participant_id",
            sa.Integer(),
            sa.ForeignKey("participants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "set_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Composite index for fast record lookup by category
    op.create_index(
        "ix_records_category",
        "platform_records",
        ["lift_type", "gender", "age_category", "weight_category_name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_records_category", table_name="platform_records")
    op.drop_table("platform_records")
    op.drop_column("participants", "checked_in")
    op.drop_column("participants", "qr_token")
    op.drop_column("tournaments", "scoring_formula")
