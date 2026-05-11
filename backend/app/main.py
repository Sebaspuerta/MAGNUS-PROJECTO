from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.routes.security_routes import router as security_router
from app.routes.barber_routes import router as barber_router
from app.routes.client_routes import router as client_router
from app.routes.service_routes import router as service_router
from app.routes.order_routes import router as order_router
from app.routes.inventory_routes import router as inventory_router


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


app.mount(
    "/",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="frontend"
)
