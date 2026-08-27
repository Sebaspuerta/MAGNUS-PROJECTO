"""sync clients table with model
Revision ID: 2c36d39be883
Revises: badc98a52d9b
Create Date: 2026-07-14 22:55:53.560488
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2c36d39be883'
down_revision = 'badc98a52d9b'
branch_labels = None
depends_on = None


"""sync clients table with model

Revision ID: <no tocar, ya generado>
Revises: <no tocar, ya generado>
Create Date: <no tocar, ya generado>

"""
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # batch_alter_table: en Postgres/MySQL emite los mismos ALTER TABLE de
    # siempre (recreate="auto" no reconstruye la tabla si el dialecto soporta
    # ALTER nativo); en SQLite, que no soporta renombrar columnas ni quitar un
    # server_default fuera de batch mode, hace la reconstrucción necesaria.
    with op.batch_alter_table("clients") as batch_op:
        # 1. Renombrar "name" -> "full_name" (conserva los datos existentes)
        batch_op.alter_column(
            "name",
            new_column_name="full_name",
            existing_type=sa.String(length=120),
            existing_nullable=False,
        )

        # 2. Agregar columnas que el modelo espera y faltan en la BD real
        batch_op.add_column(sa.Column("document_number", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("birth_date", sa.Date(), nullable=True))
        batch_op.add_column(
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )

        # Quitamos el server_default una vez poblado: el default real lo maneja el ORM
        batch_op.alter_column("is_active", server_default=None)

    # NOTA: la columna "address" se deja intacta a propósito (no está en el modelo,
    # pero borrarla eliminaría datos si alguna vez se usó).


def downgrade() -> None:
    with op.batch_alter_table("clients") as batch_op:
        batch_op.drop_column("is_active")
        batch_op.drop_column("birth_date")
        batch_op.drop_column("document_number")

        batch_op.alter_column(
            "full_name",
            new_column_name="name",
            existing_type=sa.String(length=120),
            existing_nullable=False,
        )
