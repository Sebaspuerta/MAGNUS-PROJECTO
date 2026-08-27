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
    # Todo dentro de un solo batch_alter_table: en Postgres/MySQL esto emite
    # los mismos ALTER TABLE de siempre (recreate="auto" no reconstruye la
    # tabla si el dialecto soporta ALTER nativo); en SQLite, que no soporta
    # ALTER de constraints ni renombrar columnas fuera de batch mode, hace la
    # reconstrucción copy-and-move necesaria en un solo paso.
    with op.batch_alter_table("barbers") as batch_op:
        # 1. Renombrar "name" -> "full_name" (conserva los datos existentes)
        batch_op.alter_column(
            "name",
            new_column_name="full_name",
            existing_type=sa.String(length=120),
            existing_nullable=False,
        )

        # 2. Agregar las columnas que el modelo espera y que faltan en la BD real
        batch_op.add_column(sa.Column("alias", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("quick_pin_hash", sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column(
                "commission_type",
                sa.String(length=30),
                nullable=False,
                server_default="porcentaje",
            ),
        )
        batch_op.add_column(
            sa.Column(
                "commission_value",
                sa.Numeric(10, 2),
                nullable=False,
                server_default="0",
            ),
        )
        batch_op.add_column(sa.Column("notes", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))

        batch_op.create_foreign_key(
            "fk_barbers_user_id_users",
            "users",
            ["user_id"],
            ["id"],
        )
        batch_op.create_unique_constraint("uq_barbers_user_id", ["user_id"])

        # Quitamos el server_default una vez poblado: el default real lo maneja el modelo/ORM
        batch_op.alter_column("commission_type", server_default=None)
        batch_op.alter_column("commission_value", server_default=None)

    # NOTA: la columna "email" se deja intacta a propósito (no está en el modelo,
    # pero borrarla eliminaría datos si alguna vez se usó). Si confirmas que
    # nunca tuvo datos útiles, puedes eliminarla más adelante en otra migración.


def downgrade() -> None:
    with op.batch_alter_table("barbers") as batch_op:
        batch_op.drop_constraint("uq_barbers_user_id", type_="unique")
        batch_op.drop_constraint("fk_barbers_user_id_users", type_="foreignkey")
        batch_op.drop_column("user_id")
        batch_op.drop_column("notes")
        batch_op.drop_column("commission_value")
        batch_op.drop_column("commission_type")
        batch_op.drop_column("quick_pin_hash")
        batch_op.drop_column("alias")

        batch_op.alter_column(
            "full_name",
            new_column_name="name",
            existing_type=sa.String(length=120),
            existing_nullable=False,
        )
