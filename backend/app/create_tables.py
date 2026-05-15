from app.database import Base, engine
from app.models.security import AuditLog, Permission, Role, RolePermission, User
from app.models.barber import Barber
from app.models.client import Client
from app.models.service import Service
from app.models.order import Order, OrderItem
from app.models.inventory import InventoryMovement, Product
from app.models.payment import Payment
from app.models.cash_register import CashRegister
from app.models.cash_movement import CashMovement
from app.models.accounts_receivable import AccountsReceivable, AccountsReceivablePayment
from app.models.alerts import Alert
from app.models.system_config import SystemConfig
from app.models.service_consumable import ServiceConsumable


def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Tablas creadas correctamente en PostgreSQL.")


if __name__ == "__main__":
    create_tables()
