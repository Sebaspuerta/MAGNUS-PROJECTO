"""categories.name unique only among non-deleted rows

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-17 20:00:00.000000

categories.name tenía un UNIQUE de tabla completa (categories_name_key), que
sigue aplicando incluso sobre filas con is_deleted=True. El borrado lógico de
una categoría preserva su fila y su nombre original (para que el historial
de ventas que la mencione lo siga mostrando con el sufijo "(categoría
eliminada del sistema)"), pero eso significaba que crear una categoría nueva
reutilizando ese mismo nombre fallaba con un IntegrityError sin manejar
(500 genérico) — aunque la categoría "activa" con ese nombre ya no existiera.
category_service.create_category() ya asumía (en su chequeo de duplicados)
que el nombre solo debía ser único entre categorías vivas; esta migración
alinea la restricción real de la base de datos con esa intención.

Reemplaza el UNIQUE de tabla completa por un índice único PARCIAL, solo sobre
filas con is_deleted = false.

Idempotente: puede correrse varias veces sin fallar si ya se aplicó.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None

_OLD_CONSTRAINT = "categories_name_key"
_NEW_INDEX = "ix_categories_name_active_unique"


def _has_constraint(inspector, table_name: str, constraint_name: str) -> bool:
    return any(uc["name"] == constraint_name for uc in inspector.get_unique_constraints(table_name))


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(ix["name"] == index_name for ix in inspector.get_indexes(table_name))


def _categories_table(meta: sa.MetaData, *, name_unique: bool) -> sa.Table:
    # Misma forma que dejó b2c3d4e5f6a7_add_categories_and_product_category_id,
    # usada como target de copy_from en el rebuild de tabla que exige SQLite
    # para quitar/poner el UNIQUE inline de "name" (ver nota en upgrade()).
    return sa.Table(
        "categories", meta,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False, unique=name_unique),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "categories" not in inspector.get_table_names():
        return

    if conn.dialect.name == "sqlite":
        # SQLite refleja el UNIQUE inline de "name" (creado por
        # Column(unique=True) en la migración anterior) sin nombre — no hay
        # drop_constraint posible por nombre, ni ALTER TABLE DROP CONSTRAINT.
        # Hay que reconstruir la tabla completa sin esa restricción (patrón
        # estándar de Alembic batch mode para SQLite).
        has_unique_column = any(
            uc["column_names"] == ["name"]
            for uc in inspector.get_unique_constraints("categories")
        )
        if has_unique_column:
            target = _categories_table(sa.MetaData(), name_unique=False)
            with op.batch_alter_table("categories", recreate="always", copy_from=target):
                pass
            inspector = sa.inspect(conn)
    else:
        if _has_constraint(inspector, "categories", _OLD_CONSTRAINT):
            op.drop_constraint(_OLD_CONSTRAINT, "categories", type_="unique")
        inspector = sa.inspect(conn)

    if not _has_index(inspector, "categories", _NEW_INDEX):
        op.create_index(
            _NEW_INDEX,
            "categories",
            ["name"],
            unique=True,
            postgresql_where=sa.text("is_deleted = false"),
            sqlite_where=sa.text("is_deleted = 0"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "categories" not in inspector.get_table_names():
        return

    if _has_index(inspector, "categories", _NEW_INDEX):
        op.drop_index(_NEW_INDEX, table_name="categories")

    inspector = sa.inspect(conn)

    if conn.dialect.name == "sqlite":
        has_unique_column = any(
            uc["column_names"] == ["name"]
            for uc in inspector.get_unique_constraints("categories")
        )
        if not has_unique_column:
            target = _categories_table(sa.MetaData(), name_unique=True)
            with op.batch_alter_table("categories", recreate="always", copy_from=target):
                pass
    else:
        if not _has_constraint(inspector, "categories", _OLD_CONSTRAINT):
            op.create_unique_constraint(_OLD_CONSTRAINT, "categories", ["name"])
