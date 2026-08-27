from app.config import settings
from app.database import SessionLocal
from app.services.security_service import seed_initial_security


def run_seed():
    db = SessionLocal()
    try:
        seed_initial_security(db)
        print("Seed inicial ejecutado correctamente.")
        print(f"Usuario inicial: {settings.admin_username}")
        print("Contraseña inicial: definida en ADMIN_PASSWORD")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
