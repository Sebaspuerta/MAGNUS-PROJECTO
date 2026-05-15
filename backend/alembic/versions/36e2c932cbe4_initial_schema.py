"""initial schema
Revision ID: 36e2c932cbe4
Revises: 
Create Date: 2026-05-14 21:47:22.875287
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '36e2c932cbe4'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(length=50), nullable=False, unique=True, index=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False)
    )

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("module", sa.String(length=80), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False, unique=True, index=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.UniqueConstraint("module", "action", name="uq_permission_module_action")
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("username", sa.String(length=50), nullable=False, unique=True, index=True),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True)
    )

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id"), nullable=False),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permission")
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("module", sa.String(length=80), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False)
    )

    op.create_table(
        "barbers",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True)
    )

    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True)
    )

    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(length=120), nullable=False, index=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("uses_internal_consumables", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True)
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(length=120), nullable=False, index=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("product_type", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("purchase_cost", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("sale_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("current_stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("minimum_stock", sa.Integer(), nullable=True),
        sa.Column("expiration_date", sa.Date(), nullable=True),
        sa.Column("supplier", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True)
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("movement_type", sa.String(length=40), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("previous_stock", sa.Integer(), nullable=False),
        sa.Column("new_stock", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("reference_type", sa.String(length=80), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False)
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=True),
        sa.Column("barber_id", sa.Integer(), sa.ForeignKey("barbers.id"), nullable=True),
        sa.Column("payment_status", sa.String(length=30), nullable=False, server_default="pendiente"),
        sa.Column("amount_paid", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("is_fiado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="abierta"),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("discount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True)
    )

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("item_type", sa.String(length=30), nullable=False),
        sa.Column("service_id", sa.Integer(), sa.ForeignKey("services.id"), nullable=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=False)
    )

    op.create_table(
        "cash_registers",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("opened_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("opened_at", sa.DateTime(), nullable=False),
        sa.Column("opening_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("closed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("closing_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_closed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notes", sa.Text(), nullable=True)
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("cash_register_id", sa.Integer(), sa.ForeignKey("cash_registers.id"), nullable=True),
        sa.Column("payment_method", sa.String(length=80), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=False)
    )

    op.create_table(
        "cash_movements",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("cash_register_id", sa.Integer(), sa.ForeignKey("cash_registers.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("movement_type", sa.String(length=80), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_method", sa.String(length=80), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reference_type", sa.String(length=80), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False)
    )

    op.create_table(
        "accounts_receivable",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("balance", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pendiente"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True)
    )

    op.create_table(
        "accounts_receivable_payments",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("accounts_receivable_id", sa.Integer(), sa.ForeignKey("accounts_receivable.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_method", sa.String(length=80), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("payment_date", sa.DateTime(), nullable=False)
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("alert_type", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("reference_type", sa.String(length=80), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False)
    )

    op.create_table(
        "system_config",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("key", sa.String(length=120), nullable=False, unique=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True)
    )

    op.create_table(
        "service_consumables",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("service_id", sa.Integer(), sa.ForeignKey("services.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False)
    )


def downgrade() -> None:
    op.drop_table("service_consumables")
    op.drop_table("system_config")
    op.drop_table("alerts")
    op.drop_table("accounts_receivable_payments")
    op.drop_table("accounts_receivable")
    op.drop_table("cash_movements")
    op.drop_table("cash_registers")
    op.drop_table("payments")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("inventory_movements")
    op.drop_table("products")
    op.drop_table("services")
    op.drop_table("clients")
    op.drop_table("barbers")
    op.drop_table("audit_logs")
    op.drop_table("role_permissions")
    op.drop_table("users")
    op.drop_table("permissions")
    op.drop_table("roles")
