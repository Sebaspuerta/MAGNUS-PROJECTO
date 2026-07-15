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
    # 1. Renombrar "name" -> "full_name" (conserva los datos existentes)
    op.alter_column(
        "clients",
        "name",
        new_column_name="full_name",
        existing_type=sa.String(length=120),
        existing_nullable=False,
    )

    # 2. Agregar columnas que el modelo espera y faltan en la BD real
    op.add_column("clients", sa.Column("document_number", sa.String(length=30), nullable=True))
    op.add_column("clients", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column(
        "clients",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # Quitamos el server_default una vez poblado: el default real lo maneja el ORM
    op.alter_column("clients", "is_active", server_default=None)

    # NOTA: la columna "address" se deja intacta a propósito (no está en el modelo,
    # pero borrarla eliminaría datos si alguna vez se usó).


def downgrade() -> None:
    op.drop_column("clients", "is_active")
    op.drop_column("clients", "birth_date")
    op.drop_column("clients", "document_number")

    op.alter_column(
        "clients",
        "full_name",
        new_column_name="name",
        existing_type=sa.String(length=120),
        existing_nullable=False,
    )
