from app.database import Base, engine
from app.models.security import AuditLog, Permission, Role, RolePermission, User
from app.models.barber import Barber
from app.models.client import Client
from app.models.service import Service
from app.models.order import Order, OrderItem
from app.models.inventory import InventoryMovement, Product


def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Tablas creadas correctamente en PostgreSQL.")


if __name__ == "__main__":
    create_tables()
