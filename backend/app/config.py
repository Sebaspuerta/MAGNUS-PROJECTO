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

    database_url: str = os.getenv("DATABASE_URL", "")
    secret_key: str = os.getenv("SECRET_KEY", "CLAVE_LOCAL_MAGNUS")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))


settings = Settings()

if not settings.database_url:
    raise RuntimeError(
        "No se encontró DATABASE_URL en el archivo .env. "
        "Verifica que el archivo .env esté en la raíz del proyecto."
    )
