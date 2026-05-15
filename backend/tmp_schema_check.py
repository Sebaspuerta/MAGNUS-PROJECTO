from app.database import engine
from sqlalchemy import inspect

insp = inspect(engine)
tables = [
    'orders',
    'order_items',
    'cash_registers',
    'payments',
    'cash_movements',
    'accounts_receivable',
    'accounts_receivable_payments',
    'alerts',
    'system_config',
    'service_consumables'
]

for table in tables:
    if insp.has_table(table):
        cols = [col['name'] for col in insp.get_columns(table)]
        print(table, cols)
    else:
        print(table, 'MISSING')
