"""add is_deleted to products, services and barbers

Revision ID: a7f3c9e1d2b4
Revises: 2c36d39be883
Create Date: 2026-08-08 10:12:00.000000

Marca de borrado lógico. "Eliminar" un producto/servicio/barbero nunca borra la
fila: se marca is_deleted=True (e is_active=False) para que el historial de
ventas y los movimientos de inventario queden intactos.

La migración es idempotente: si la columna ya existe (por ejemplo, porque la
base se creó con create_tables.py a partir de los modelos), no hace nada.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a7f3c9e1d2b4'
down_revision = '2c36d39be883'
branch_labels = None
depends_on = None


TARGET_TABLES = ("products", "services", "barbers")


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())

    for table_name in TARGET_TABLES:
        if table_name not in existing_tables:
            continue
        if _has_column(inspector, table_name, "is_deleted"):
            continue

        op.add_column(
            table_name,
            sa.Column(
                "is_deleted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())

    for table_name in reversed(TARGET_TABLES):
        if table_name not in existing_tables:
            continue
        if not _has_column(inspector, table_name, "is_deleted"):
            continue

        op.drop_column(table_name, "is_deleted")
