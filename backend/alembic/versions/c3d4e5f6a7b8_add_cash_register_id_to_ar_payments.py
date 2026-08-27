"""add cash_register_id to accounts_receivable_payments

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-15 10:00:00.000000

Agrega accounts_receivable_payments.cash_register_id (FK opcional a
cash_registers.id) para poder vincular un abono de fiado con la caja que
estaba abierta al momento de registrarlo. Nullable: no todo abono se
registra con una caja abierta.

La migración es idempotente: si la columna ya existe no hace nada.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "accounts_receivable_payments" not in inspector.get_table_names():
        return
    if _has_column(inspector, "accounts_receivable_payments", "cash_register_id"):
        return

    # batch_alter_table: agregar una columna con FK es una operación de "add
    # constraint" para Alembic, y SQLite no soporta ALTER de constraints
    # fuera de batch mode (en Postgres, recreate="auto" emite el mismo
    # ALTER TABLE ADD COLUMN de siempre, sin reconstruir nada).
    with op.batch_alter_table("accounts_receivable_payments") as batch_op:
        batch_op.add_column(
            sa.Column(
                "cash_register_id",
                sa.Integer(),
                sa.ForeignKey(
                    "cash_registers.id",
                    name="fk_ar_payments_cash_register_id_cash_registers",
                ),
                nullable=True,
            ),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "accounts_receivable_payments" not in inspector.get_table_names():
        return
    if not _has_column(inspector, "accounts_receivable_payments", "cash_register_id"):
        return

    with op.batch_alter_table("accounts_receivable_payments") as batch_op:
        batch_op.drop_column("cash_register_id")