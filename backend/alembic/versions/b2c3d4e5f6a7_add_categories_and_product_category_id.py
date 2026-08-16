"""add categories table and products.category_id

Revision ID: b2c3d4e5f6a7
Revises: f1a2b3c4d5e6
Create Date: 2026-08-09 12:00:00.000000

Crea la tabla `categories` y agrega `products.category_id` (FK). Migra los
datos existentes: cada valor distinto no nulo que hoy exista en
products.category se convierte en una fila de categories, y cada producto
queda apuntando a la categoría correspondiente por category_id.

products.category (texto libre) NO se borra ni se dropea — queda en la tabla
como respaldo histórico, sin usarse en el código nuevo.

La migración es idempotente: puede correrse varias veces sin duplicar
categorías ni fallar si ya se aplicó parcialmente.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if not _has_table(inspector, "categories"):
        op.create_table(
            "categories",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("name", sa.String(length=80), nullable=False, unique=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        inspector = sa.inspect(conn)

    if _has_table(inspector, "products") and not _has_column(inspector, "products", "category_id"):
        op.add_column(
            "products",
            sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
        )
        inspector = sa.inspect(conn)

    if not _has_table(inspector, "products"):
        return

    # ── Migración de datos: category (texto) -> categories + category_id ──
    distinct_names = [
        row[0] for row in conn.execute(
            sa.text(
                "SELECT DISTINCT category FROM products "
                "WHERE category IS NOT NULL AND btrim(category) <> ''"
            )
        ).fetchall()
    ]

    for name in distinct_names:
        clean_name = name.strip()

        existing_id = conn.execute(
            sa.text("SELECT id FROM categories WHERE lower(name) = lower(:name)"),
            {"name": clean_name},
        ).scalar()

        if existing_id is None:
            existing_id = conn.execute(
                sa.text(
                    "INSERT INTO categories (name, is_deleted, created_at) "
                    "VALUES (:name, false, now()) RETURNING id"
                ),
                {"name": clean_name},
            ).scalar()

        conn.execute(
            sa.text(
                "UPDATE products SET category_id = :cat_id "
                "WHERE category = :name AND category_id IS NULL"
            ),
            {"cat_id": existing_id, "name": name},
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if _has_table(inspector, "products") and _has_column(inspector, "products", "category_id"):
        op.drop_column("products", "category_id")

    if _has_table(inspector, "categories"):
        op.drop_table("categories")