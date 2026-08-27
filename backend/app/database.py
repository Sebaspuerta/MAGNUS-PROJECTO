from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings


_is_sqlite = make_url(settings.database_url).get_backend_name() == "sqlite"

_connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
    connect_args=_connect_args
)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):
        # SQLite trae las foreign keys DESACTIVADAS por defecto: sin este
        # PRAGMA en cada conexión nueva, las relaciones entre órdenes,
        # productos, categorías, etc. dejarían de protegerse silenciosamente.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        # WAL: mejor concurrencia entre pestañas del navegador abiertas al
        # mismo tiempo sobre el mismo archivo .db.
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
