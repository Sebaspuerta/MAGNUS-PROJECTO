"""add_master_code_config
Revision ID: dc7db228bd8d
Revises: 36e2c932cbe4
Create Date: 2026-07-05 12:59:38.475107
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'dc7db228bd8d'
down_revision = '36e2c932cbe4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "master_code_config",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("code_hash", sa.String(length=255), nullable=True),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("master_code_config")
