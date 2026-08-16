"""add photo_filename to products

Revision ID: f1a2b3c4d5e6
Revises: a7f3c9e1d2b4
Create Date: 2026-08-09 09:00:00.000000

Agrega la columna photo_filename (ruta relativa dentro de backend/static, p.ej.
"product_photos/12.png") para asociar una foto miniatura a cada producto.

La migración es idempotente: si la columna ya existe no hace nada.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'a7f3c9e1d2b4'
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "products" not in inspector.get_table_names():
        return
    if _has_column(inspector, "products", "photo_filename"):
        return

    op.add_column(
        "products",
        sa.Column("photo_filename", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "products" not in inspector.get_table_names():
        return
    if not _has_column(inspector, "products", "photo_filename"):
        return

    op.drop_column("products", "photo_filename")
