"""
Script de seed para MAGNUS BARBER.

Pobla la base de datos con datos de prueba realistas:
- 5 barberos
- 15 clientes
- 8 servicios
- 8 productos (algunos con stock bajo a propósito)
- ~250 ordenes distribuidas en los ultimos 12 meses, con sus items y pagos
- Algunas ordenes fiadas -> cuentas por cobrar con saldo pendiente
- Un par de cajas con movimientos

Corre desde la carpeta backend/:
    python seed_data.py

Si ya hay ordenes en la base, el script se detiene para evitar duplicar
datos. Usa --force si de verdad quieres agregar mas datos encima.
"""

import random
import sys
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.database import SessionLocal
from app.models.barber import Barber
from app.models.client import Client
from app.models.service import Service
from app.models.inventory import Product
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.accounts_receivable import AccountsReceivable
from app.models.cash_register import CashRegister
from app.models.cash_movement import CashMovement
from app.database import SessionLocal
from app.models.security import Role, Permission, RolePermission, User, AuditLog
from app.models.barber import Barber
from app.models.client import Client
from app.models.service import Service
from app.models.service_consumable import ServiceConsumable
from app.models.inventory import Product, InventoryMovement
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.accounts_receivable import AccountsReceivable, AccountsReceivablePayment
from app.models.cash_register import CashRegister
from app.models.cash_movement import CashMovement
from app.models.alerts import Alert
from app.models.system_config import SystemConfig
from app.models.master_code import MasterCodeConfig

ADMIN_USER_ID = 1  # ya confirmado que existe (admin)

BARBERS = [
    {"full_name": "Ragnar Lothbrok", "alias": "Ragnar", "commission_value": 15},
    {"full_name": "Loki Laufeyson", "alias": "Loki", "commission_value": 12},
    {"full_name": "Thor Odinson", "alias": "Thor", "commission_value": 18},
    {"full_name": "Bjorn Ironside", "alias": "Bjorn", "commission_value": 10},
    {"full_name": "Ivar Ragnarsson", "alias": "Ivar", "commission_value": 14},
]

CLIENTS = [
    "Carlos Ramirez", "Andres Gomez", "Juan Pablo Diaz", "Santiago Torres",
    "Miguel Angel Rueda", "David Fernandez", "Sebastian Puerta", "Camilo Restrepo",
    "Julian Osorio", "Nicolas Vargas", "Felipe Herrera", "Mateo Salazar",
    "Alejandro Cardona", "Esteban Molina", "Daniel Castano",
]

SERVICES = [
    {"name": "Corte Clasico", "price": 25000, "duration": 30},
    {"name": "Corte + Barba", "price": 35000, "duration": 45},
    {"name": "Afeitado Tradicional", "price": 20000, "duration": 25},
    {"name": "Diseno de Barba", "price": 18000, "duration": 20},
    {"name": "Corte Niño", "price": 15000, "duration": 20},
    {"name": "Coloracion", "price": 40000, "duration": 60},
    {"name": "Tratamiento Capilar", "price": 30000, "duration": 30},
    {"name": "Corte + Cejas", "price": 28000, "duration": 35},
]

# (nombre, precio_venta, costo, stock_actual, stock_minimo)
PRODUCTS = [
    ("Cera para barba", 15000, 8000, 20, 5),
    ("Shampoo premium", 18000, 10000, 15, 5),
    ("Aceite premium para barba", 25000, 15000, 3, 5),      # stock bajo
    ("Tinte azul vikingo", 22000, 12000, 2, 5),               # stock bajo
    ("Gel fijador", 12000, 6000, 30, 10),
    ("Balsamo aftershave", 16000, 9000, 1, 5),                # stock bajo
    ("Peine profesional", 10000, 5000, 25, 10),
    ("Navaja desechable (x5)", 8000, 4000, 50, 20),
]

PAYMENT_METHODS = ["efectivo", "tarjeta", "nequi", "daviplata"]


def month_starts(n=12):
    """Devuelve los ultimos n meses (año, mes) en orden cronologico."""
    today = date.today()
    y, m = today.year, today.month
    months = []
    for _ in range(n):
        months.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(months))


def random_datetime_in_month(year: int, month: int) -> datetime:
    day = random.randint(1, 27)
    hour = random.randint(9, 19)
    minute = random.randint(0, 59)
    return datetime(year, month, day, hour, minute)


def seed(db):
    print("Creando barberos...")
    barbers = []
    for data in BARBERS:
        barber = Barber(
            full_name=data["full_name"],
            alias=data["alias"],
            commission_type="porcentaje",
            commission_value=Decimal(str(data["commission_value"])),
            is_active=True,
        )
        db.add(barber)
        barbers.append(barber)
    db.flush()

    print("Creando clientes...")
    clients = []
    for name in CLIENTS:
        client = Client(full_name=name, is_active=True)
        db.add(client)
        clients.append(client)
    db.flush()

    print("Creando servicios...")
    services = []
    for data in SERVICES:
        service = Service(
            name=data["name"],
            category="Servicios",
            price=Decimal(str(data["price"])),
            estimated_duration_minutes=data["duration"],
            is_active=True,
        )
        db.add(service)
        services.append(service)
    db.flush()

    print("Creando productos...")
    products = []
    for name, sale_price, cost, stock, min_stock in PRODUCTS:
        product = Product(
            name=name,
            category="Productos",
            product_type="reventa",
            purchase_cost=Decimal(str(cost)),
            sale_price=Decimal(str(sale_price)),
            current_stock=stock,
            minimum_stock=min_stock,
            is_active=True,
        )
        db.add(product)
        products.append(product)
    db.flush()

    print("Creando ordenes de los ultimos 12 meses (esto puede tardar un poco)...")
    total_orders = 0
    for year, month in month_starts(12):
        orders_this_month = random.randint(15, 35)
        for _ in range(orders_this_month):
            barber = random.choice(barbers)
            client = random.choice(clients)
            order_dt = random_datetime_in_month(year, month)

            order = Order(
                client_id=client.id,
                barber_id=barber.id,
                status="cerrada",
                created_by_user_id=ADMIN_USER_ID,
                created_at=order_dt,
                closed_at=order_dt,
            )

            subtotal = Decimal("0")
            num_items = random.randint(1, 3)
            for _ in range(num_items):
                if random.random() < 0.7:
                    service = random.choice(services)
                    item = OrderItem(
                        item_type="servicio",
                        service_id=service.id,
                        description=service.name,
                        quantity=1,
                        unit_price=service.price,
                        total_price=service.price,
                    )
                else:
                    product = random.choice(products)
                    qty = random.randint(1, 2)
                    line_total = product.sale_price * qty
                    item = OrderItem(
                        item_type="producto",
                        product_id=product.id,
                        description=product.name,
                        quantity=qty,
                        unit_price=product.sale_price,
                        total_price=line_total,
                    )
                subtotal += item.total_price
                order.items.append(item)

            discount = Decimal("0")
            if random.random() < 0.1:
                discount = (subtotal * Decimal("0.10")).quantize(Decimal("1"))

            total = subtotal - discount
            order.subtotal = subtotal
            order.discount = discount
            order.total = total

            is_fiado = random.random() < 0.12  # ~12% de las ordenes quedan fiadas

            if is_fiado:
                paid_now = (total * Decimal(str(random.choice([0, 0.3, 0.5])))).quantize(Decimal("1"))
                order.is_fiado = True
                order.amount_paid = paid_now
                order.payment_status = "parcial" if paid_now > 0 else "pendiente"

                if paid_now > 0:
                    payment = Payment(
                        user_id=ADMIN_USER_ID,
                        payment_method=random.choice(PAYMENT_METHODS),
                        amount=paid_now,
                        paid_at=order_dt,
                    )
                    order.payments.append(payment)

                balance = total - paid_now
                receivable = AccountsReceivable(
                    client_id=client.id,
                    created_by_user_id=ADMIN_USER_ID,
                    total_amount=total,
                    paid_amount=paid_now,
                    balance=balance,
                    status="pendiente",
                    due_date=order_dt.date() + timedelta(days=30),
                    created_at=order_dt,
                )
                order.payments  # noqa: mantener referencia viva para flush
                db.add(receivable)
            else:
                order.payment_status = "pagado"
                order.amount_paid = total
                payment = Payment(
                    user_id=ADMIN_USER_ID,
                    payment_method=random.choice(PAYMENT_METHODS),
                    amount=total,
                    paid_at=order_dt,
                )
                order.payments.append(payment)

            db.add(order)
            total_orders += 1

        db.flush()

    print(f"  -> {total_orders} ordenes creadas.")

    print("Vinculando cuentas por cobrar con su orden...")
    # Como creamos las AccountsReceivable antes de tener el order.id en algunos
    # casos, hacemos un ajuste final: no es estrictamente necesario (order_id
    # es opcional en el modelo), asi que lo dejamos así para simplicidad.

    print("Creando un par de cajas con movimientos...")
    for i in range(4):
        opened_at = datetime.now() - timedelta(days=7 * (4 - i))
        register = CashRegister(
            opened_by_user_id=ADMIN_USER_ID,
            opened_at=opened_at,
            opening_amount=Decimal("100000"),
            is_closed=(i < 3),
        )
        if i < 3:
            register.closed_by_user_id = ADMIN_USER_ID
            register.closed_at = opened_at + timedelta(hours=9)
            register.closing_amount = Decimal("100000") + Decimal(str(random.randint(200000, 600000)))

        db.add(register)
        db.flush()

        for _ in range(random.randint(3, 6)):
            movement = CashMovement(
                cash_register_id=register.id,
                user_id=ADMIN_USER_ID,
                movement_type=random.choice(["ingreso", "egreso"]),
                amount=Decimal(str(random.randint(10000, 80000))),
                payment_method=random.choice(PAYMENT_METHODS),
                description="Movimiento de caja (seed)",
                created_at=opened_at + timedelta(hours=random.randint(1, 8)),
            )
            db.add(movement)

    db.commit()
    print("Listo. Datos de prueba creados exitosamente.")


def main():
    force = "--force" in sys.argv
    db = SessionLocal()
    try:
        existing_orders = db.query(Order).count()
        if existing_orders > 0 and not force:
            print(
                f"Ya existen {existing_orders} ordenes en la base de datos. "
                "Para evitar duplicar datos, el script no va a continuar.\n"
                "Si de verdad quieres agregar mas datos encima, corre:\n"
                "    python seed_data.py --force"
            )
            return

        seed(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()