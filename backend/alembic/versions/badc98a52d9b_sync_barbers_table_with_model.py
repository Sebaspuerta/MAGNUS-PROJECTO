"""sync barbers table with model
Revision ID: badc98a52d9b
Revises: 23cfa383266e
Create Date: 2026-07-14 22:46:47.738498
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'badc98a52d9b'
down_revision = '23cfa383266e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Renombrar "name" -> "full_name" (conserva los datos existentes)
    op.alter_column(
        "barbers",
        "name",
        new_column_name="full_name",
        existing_type=sa.String(length=120),
        existing_nullable=False,
    )

    # 2. Agregar las columnas que el modelo espera y que faltan en la BD real
    op.add_column("barbers", sa.Column("alias", sa.String(length=80), nullable=True))
    op.add_column("barbers", sa.Column("quick_pin_hash", sa.String(length=255), nullable=True))
    op.add_column(
        "barbers",
        sa.Column(
            "commission_type",
            sa.String(length=30),
            nullable=False,
            server_default="porcentaje",
        ),
    )
    op.add_column(
        "barbers",
        sa.Column(
            "commission_value",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column("barbers", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("barbers", sa.Column("user_id", sa.Integer(), nullable=True))

    op.create_foreign_key(
        "fk_barbers_user_id_users",
        "barbers",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_unique_constraint("uq_barbers_user_id", "barbers", ["user_id"])

    # Quitamos el server_default una vez poblado: el default real lo maneja el modelo/ORM
    op.alter_column("barbers", "commission_type", server_default=None)
    op.alter_column("barbers", "commission_value", server_default=None)

    # NOTA: la columna "email" se deja intacta a propósito (no está en el modelo,
    # pero borrarla eliminaría datos si alguna vez se usó). Si confirmas que
    # nunca tuvo datos útiles, puedes eliminarla más adelante en otra migración.


def downgrade() -> None:
    op.drop_constraint("uq_barbers_user_id", "barbers", type_="unique")
    op.drop_constraint("fk_barbers_user_id_users", "barbers", type_="foreignkey")
    op.drop_column("barbers", "user_id")
    op.drop_column("barbers", "notes")
    op.drop_column("barbers", "commission_value")
    op.drop_column("barbers", "commission_type")
    op.drop_column("barbers", "quick_pin_hash")
    op.drop_column("barbers", "alias")

    op.alter_column(
        "barbers",
        "full_name",
        new_column_name="name",
        existing_type=sa.String(length=120),
        existing_nullable=False,
    )
