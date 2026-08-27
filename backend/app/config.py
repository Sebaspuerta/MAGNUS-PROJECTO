from pathlib import Path
import os
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE, encoding="utf-8-sig")


class Settings:
    app_name: str = os.getenv("APP_NAME", "MAGNUS BARBER SYSTEM")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    app_mode: str = os.getenv("APP_MODE", "local")

    # Por defecto SQLite: ruta relativa a la carpeta desde la que se arranca el
    # ejecutable empaquetado (no una ruta absoluta de desarrollo). Para seguir
    # usando PostgreSQL en desarrollo, basta con definir DATABASE_URL en .env.
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./magnus_barberia.db")
    secret_key: str = os.getenv("SECRET_KEY", "CLAVE_LOCAL_MAGNUS")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str | None = os.getenv("ADMIN_PASSWORD")
    admin_full_name: str = os.getenv("ADMIN_FULL_NAME", "Administrador MAGNUS")

    business_tz: str = os.getenv("BUSINESS_TZ", "America/Bogota")


settings = Settings()

if not settings.database_url:
    raise RuntimeError(
        "No se encontró DATABASE_URL en el archivo .env. "
        "Verifica que el archivo .env esté en la raíz del proyecto."
    )
