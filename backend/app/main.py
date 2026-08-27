from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.routes.security_routes import router as security_router
from app.routes.barber_routes import router as barber_router
from app.routes.client_routes import router as client_router
from app.routes.service_routes import router as service_router
from app.routes.order_routes import router as order_router
from app.routes.inventory_routes import router as inventory_router
from app.routes.category_routes import router as category_router
from app.routes.payment_routes import router as payment_router
from app.routes.cash_register_routes import router as cash_register_router
from app.routes.cash_movement_routes import router as cash_movement_router
from app.routes.accounts_receivable_routes import router as accounts_receivable_router
from app.routes.alerts_routes import router as alerts_router
from app.routes.system_config_routes import router as system_config_router
from app.routes.service_consumable_routes import router as service_consumable_router
from app.routes.dashboard_routes import router as dashboard_router
from app.routes.reports_routes import router as reports_router


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend local para MAGNUS BARBER SYSTEM MVP v1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)


BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = BASE_DIR / "backend" / "static"
PRODUCT_PHOTOS_DIR = STATIC_DIR / "product_photos"
PRODUCT_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "system": settings.app_name,
        "version": settings.app_version,
        "mode": settings.app_mode
    }


app.include_router(security_router)
app.include_router(barber_router)
app.include_router(client_router)
app.include_router(service_router)
app.include_router(order_router)
app.include_router(inventory_router)
app.include_router(category_router)
app.include_router(payment_router)
app.include_router(cash_register_router)
app.include_router(cash_movement_router)
app.include_router(accounts_receivable_router)
app.include_router(alerts_router)
app.include_router(system_config_router)
app.include_router(service_consumable_router)
app.include_router(dashboard_router)
app.include_router(reports_router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/LOGIN/login.html")


# IMPORTANTE: este mount debe registrarse ANTES que el de "/" — FastAPI/Starlette
# resuelve los mounts en el orden en que se registran, y el mount de "/" con
# html=True es un catch-all que, si fuera primero, capturaría también las
# rutas de /media.
app.mount(
    "/media",
    StaticFiles(directory=STATIC_DIR),
    name="media"
)

app.mount(
    "/",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="frontend"
)
