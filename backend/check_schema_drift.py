"""
Compara cada modelo de app/models contra las columnas reales de la BD
y reporta diferencias, sin modificar nada.
"""
from sqlalchemy import inspect

from app.database import engine
from app.models.security import Role, Permission, RolePermission, User, AuditLog
from app.models.barber import Barber
from app.models.client import Client
from app.models.service import Service
from app.models.service_consumable import ServiceConsumable
from app.models.inventory import Product, InventoryMovement
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.cash_register import CashRegister
from app.models.cash_movement import CashMovement
from app.models.accounts_receivable import AccountsReceivable, AccountsReceivablePayment
from app.models.alerts import Alert
from app.models.system_config import SystemConfig
from app.models.master_code import MasterCodeConfig


MODELS = [
    Role, Permission, RolePermission, User, AuditLog,
    Barber, Client, Service, ServiceConsumable,
    Product, InventoryMovement, Order, OrderItem, Payment,
    CashRegister, CashMovement, AccountsReceivable, AccountsReceivablePayment,
    Alert, SystemConfig, MasterCodeConfig,
]


def main():
    inspector = inspect(engine)
    real_tables = set(inspector.get_table_names())

    any_drift = False

    for model in MODELS:
        table_name = model.__tablename__

        if table_name not in real_tables:
            print(f"❌ TABLA FALTANTE: '{table_name}' no existe en la BD (modelo {model.__name__})")
            any_drift = True
            continue

        real_columns = {c["name"] for c in inspector.get_columns(table_name)}
        model_columns = {c.name for c in model.__table__.columns}

        missing_in_db = model_columns - real_columns
        extra_in_db = real_columns - model_columns

        if missing_in_db or extra_in_db:
            any_drift = True
            print(f"\n⚠️  {table_name} (modelo {model.__name__})")
            if missing_in_db:
                print(f"   Faltan en la BD (están en el modelo): {sorted(missing_in_db)}")
            if extra_in_db:
                print(f"   Sobran en la BD (no están en el modelo): {sorted(extra_in_db)}")

    if not any_drift:
        print("✅ Todas las tablas coinciden con sus modelos.")


if __name__ == "__main__":
    main()