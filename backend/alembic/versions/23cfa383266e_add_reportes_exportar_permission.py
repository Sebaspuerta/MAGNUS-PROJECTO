"""add reportes exportar permission
Revision ID: 23cfa383266e
Revises: dc7db228bd8d
Create Date: 2026-07-14 22:15:06.196343
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision = '23cfa383266e'
down_revision = 'dc7db228bd8d'
branch_labels = None
depends_on = None


permissions_table = table(
    "permissions",
    column("id", sa.Integer),
    column("module", sa.String),
    column("action", sa.String),
    column("code", sa.String),
    column("description", sa.String),
)

role_permissions_table = table(
    "role_permissions",
    column("id", sa.Integer),
    column("role_id", sa.Integer),
    column("permission_id", sa.Integer),
)


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Crear el permiso solo si no existe ya (puede haberlo creado un seeder al arrancar la app)
    existing_id = conn.execute(
        sa.text("SELECT id FROM permissions WHERE code = 'reportes.exportar'")
    ).scalar_one_or_none()

    if existing_id is None:
        conn.execute(
            permissions_table.insert().values(
                module="reportes",
                action="exportar",
                code="reportes.exportar",
                description="Exportar reportes de la base de datos a Excel",
            )
        )
        new_permission_id = conn.execute(
            sa.text("SELECT id FROM permissions WHERE code = 'reportes.exportar'")
        ).scalar_one()
    else:
        new_permission_id = existing_id

    # 2. Dárselo a todo rol que ya tenga reportes.ver, si no lo tiene todavía
    role_ids = conn.execute(
        sa.text(
            """
            SELECT rp.role_id
            FROM role_permissions rp
            JOIN permissions p ON p.id = rp.permission_id
            WHERE p.code = 'reportes.ver'
            """
        )
    ).scalars().all()

    for role_id in role_ids:
        already_has_it = conn.execute(
            sa.text(
                """
                SELECT 1 FROM role_permissions
                WHERE role_id = :role_id AND permission_id = :permission_id
                """
            ),
            {"role_id": role_id, "permission_id": new_permission_id},
        ).scalar_one_or_none()

        if already_has_it is None:
            conn.execute(
                role_permissions_table.insert().values(
                    role_id=role_id,
                    permission_id=new_permission_id,
                )
            )


def downgrade() -> None:
    conn = op.get_bind()
    permission_id = conn.execute(
        sa.text("SELECT id FROM permissions WHERE code = 'reportes.exportar'")
    ).scalar_one_or_none()

    if permission_id is not None:
        conn.execute(
            sa.text("DELETE FROM role_permissions WHERE permission_id = :pid"),
            {"pid": permission_id},
        )
        conn.execute(
            sa.text("DELETE FROM permissions WHERE id = :pid"),
            {"pid": permission_id},
        )
