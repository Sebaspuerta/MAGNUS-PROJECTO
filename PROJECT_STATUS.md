# MAGNUS BARBER SYSTEM — ESTADO ACTUAL DEL PROYECTO

## 0. Propósito de este archivo

Este archivo documenta el estado real del proyecto MAGNUS BARBER SYSTEM a la fecha. Reemplaza la versión anterior, que quedó congelada en una etapa muy temprana (antes de comandas reales, caja, fiados, categorías, soft-delete, dashboard real y la migración a SQLite).

La intención sigue siendo la misma: que cualquier persona que entre al repositorio pueda entender qué existe, cómo está construido, qué reglas de negocio no son obvias leyendo el código superficialmente, y qué falta para cerrar la v1.0.

---

# 1. Contexto general

MAGNUS BARBER SYSTEM es un software de gestión integral para una barbería, pensado para correr **localmente en un solo PC físico**, sin depender de un servidor de base de datos externo ni de conexión a Internet.

Módulos: usuarios y roles, barberos, clientes, categorías, servicios, comandas, inventario, cuentas por cobrar, alertas, caja, reportes y dashboard.

El objetivo final es que el negocio lo use como una aplicación de escritorio normal: doble clic al ícono, iniciar sesión, usar el sistema — sin terminales ni configuración técnica.

---

# 2. Stack técnico

Backend:
- Python + FastAPI
- SQLAlchemy 2.0 (estilo `Mapped`/`mapped_column`)
- **SQLite** como motor de base de datos (migrado desde PostgreSQL — ver sección 3)
- Alembic para migraciones de esquema
- JWT (python-jose) + bcrypt para autenticación
- Swagger/Redoc automáticos en `/api/docs` y `/api/redoc`

Frontend:
- HTML5 + CSS3 + JavaScript vanilla (sin framework, sin build step)
- Servido directamente por FastAPI vía `StaticFiles`
- Un módulo = una carpeta en `frontend/` con su `.html`, `.css` y `.js` (ej. `frontend/INVENTARIOS/Inventario.js`)

Futuro empaquetado (pendiente, ver sección 9):
- PyInstaller para generar el ejecutable
- Inno Setup para el instalador de Windows

Estructura de `backend/app/`: `models/`, `schemas/`, `services/`, `routes/`, `utils/` — cada módulo respeta esa separación (modelo → schema Pydantic → lógica de negocio en el service → endpoints en routes).

---

# 3. Motor de base de datos: SQLite (migrado desde PostgreSQL)

El proyecto usaba PostgreSQL. Se migró a **SQLite** para poder empaquetar el sistema como instalador de Windows sin depender de un servidor de base de datos externo (uso confirmado: un solo PC físico, sin acceso concurrente por red).

Puntos clave de la migración (`backend/app/database.py`, `backend/app/config.py`):

- `DATABASE_URL` por defecto apunta a `sqlite:///./magnus_barberia.db` (ruta relativa a donde se ejecuta el proceso). Sigue siendo posible usar PostgreSQL en desarrollo definiendo `DATABASE_URL` distinto en `.env` — la detección del dialecto en `database.py` es condicional, no un reemplazo hardcodeado.
- SQLite trae las foreign keys **desactivadas por defecto**. `database.py` registra un listener en el evento `connect` del engine que ejecuta `PRAGMA foreign_keys=ON` en cada conexión nueva — sin esto, la integridad referencial (órdenes, productos, categorías, etc.) dejaría de protegerse silenciosamente.
- También se activa `PRAGMA journal_mode=WAL` por conexión, para mejor concurrencia si hay varias pestañas del navegador abiertas sobre el mismo archivo.
- Todas las migraciones de Alembic fueron revisadas y corregidas para ser compatibles con SQLite (no solo con Postgres): `date_trunc()`, `btrim()`, `now()`, índices parciales (`postgresql_where`) y operaciones de `ALTER TABLE`/constraints que SQLite no soporta fuera de *batch mode* (renombrar columnas, agregar FK, quitar `UNIQUE`) ahora usan `op.batch_alter_table(...)`, que en Postgres sigue emitiendo los mismos `ALTER TABLE` de siempre.
- `reset_full_data.py` (script de mantenimiento de un solo uso, no expuesto como endpoint) usa `DELETE FROM` tabla por tabla en vez de `TRUNCATE ... RESTART IDENTITY CASCADE`, y resetea `sqlite_sequence` como equivalente de `RESTART IDENTITY`.
- El paquete final debe arrancar con una base de datos **vacía**: no se migran datos reales de la instancia de PostgreSQL anterior. `backend/app/create_tables.py` (`python -m app.create_tables`) crea el esquema completo desde los modelos vía `Base.metadata.create_all()`.

---

# 4. Autenticación, roles y permisos

## Roles oficiales (4, definidos en `security_service.py`)

- Administrador — acceso total.
- Barbero — atención, clientes y comandas operativas.
- Cajero — pagos, caja, cierres y cuentas por cobrar.
- Consultor — solo consulta (dashboard, reportes, históricos).

Permisos granulares por módulo/acción (`Permission.code`, ej. `"inventario.eliminar"`), verificados con `require_permission("modulo.accion")` en cada ruta protegida.

## Permisos de "dueño" — `mateo` y `admin` tienen el mismo poder

Ciertas acciones son exclusivas del dueño del negocio: crear/eliminar categorías, eliminar (soft-delete) productos, servicios y barberos. Se verifican con `require_owner()` en `app/utils/security.py`.

`mateo` y `admin` se consideran **la misma autoridad** para esas acciones — ambos usernames están en `OWNER_USERNAMES = {"mateo", "admin"}`, y `require_owner` acepta cualquiera de los dos (comparación case-insensitive). En el frontend, los botones exclusivos de dueño (`+ Categorías`, eliminar producto/servicio/barbero) se muestran a ambos usuarios con el mismo chequeo.

Aun así, el audit log sigue registrando `user_id`, así que **cada acción queda diferenciada**: se puede saber si la hizo `mateo` o `admin`, aunque tengan el mismo poder.

**No confundir con `is_owner_barber()`** (en `barber_service.py`): esa función identifica una fila específica de la tabla `barbers` (el barbero Mateo, para que nunca se pueda eliminar como barbero operativo) usando la constante singular `OWNER_USERNAME = "mateo"`. Es una lógica completamente distinta — no incluye a "admin" porque no existe un "barbero admin" que proteger.

---

# 5. Regla de negocio central: soft-delete, nunca se borra historial

Ningún registro operativo importante se borra físicamente. "Eliminar" un producto, servicio, barbero o categoría marca `is_deleted=True` (y normalmente `is_active=False`), pero la fila permanece en la base de datos.

Por qué: el historial de ventas, comandas cerradas y movimientos de inventario referencian esos registros por ID. Si se borraran físicamente, ese historial quedaría roto o con referencias huérfanas.

Cómo se ve reflejado:
- Los registros eliminados nunca vuelven en listados normales (`get_live_*` / filtros por `is_deleted`), pero siguen existiendo para joins de historial.
- En reportes y Excel, un nombre que pertenece a un registro eliminado se muestra con un sufijo como `(producto eliminado del sistema)` (ver `app/utils/deleted_labels.py`).
- `categories.name` tiene un **índice único parcial** (`WHERE is_deleted = false` / `= 0` en SQLite) en vez de un `UNIQUE` de tabla completa: permite reutilizar el nombre de una categoría eliminada en una categoría nueva, sin perder el nombre original en el historial.
- El barbero Mateo (identificado por `is_owner_barber()`) nunca se puede eliminar como barbero, sin importar quién esté logueado.

---

# 6. Módulos — estado actual

Todos los módulos base tienen backend y frontend conectados y en uso real (no maquetas con datos quemados).

## Seguridad y Control de Acceso
Login JWT, bloqueo temporal tras intentos fallidos, roles + permisos granulares, auditoría de acciones críticas.

## Barberos
CRUD completo, vínculo opcional con usuario del sistema, PIN rápido, comisión (porcentaje o fijo), soft-delete, protección especial del barbero Mateo.

## Clientes
CRUD, búsqueda/selección rápida desde Comandas, historial de fiados.

## Categorías
Módulo nuevo desde la migración anterior: CRUD de categorías de producto, exclusivo del dueño (ver sección 4), con soft-delete + nombre reutilizable tras eliminar.

## Catálogo de Servicios
CRUD, consumibles internos asociados (`service_consumables`), soft-delete.

## Comandas
Flujo completo: crear (cliente y barbero opcionales, con auto-selección de barbero y buscador de cliente en la UI), agregar/editar/quitar ítems, cerrar (transacción atómica: descuenta inventario, registra pago o fiado, mueve caja, marca comisión), cancelar. Incluye aviso de comandas potencialmente duplicadas y flujo de "comanda rápida".

## Inventario
Productos con foto (subida a `backend/static/product_photos`, servida en `/media`), entradas/ajustes de stock, movimientos con motivo y usuario responsable, alertas de stock bajo, categorías.

## Cuentas por Cobrar (fiados)
Se crean automáticamente al cerrar una comanda como fiado. Abonos parciales, saldo, estado. La lógica de "efectivo esperado en caja" y "abonos visibles como ingreso" fue corregida recientemente para que un abono a un fiado sí impacte caja e ingresos del día correctamente.

## Alertas
Stock bajo, productos agotados, próximos a vencer — consumidas por Dashboard.

## Caja
Apertura, movimientos (ingreso/egreso), cierre — incluye poder cerrar la caja **desde el Dashboard** sin salir del módulo.

## Reportes
Ventas por período (día/semana/quincena/mes vía selector), ventas por barbero, top productos, cuentas por cobrar, cierres de caja. Todos con la conversión de zona horaria Colombia aplicada correctamente (los timestamps se guardan en UTC naive; agrupar "por día" o "por mes" se hace convirtiendo a `America/Bogota` antes de agrupar, nunca agrupando la fecha UTC cruda).

Exportación a Excel: existe un generador (`excel_report_service.py`) que hoy vuelca el contenido completo de la base de datos tabla por tabla. **Pendiente:** reemplazarlo por la plantilla de reporte reforzada de 7 hojas (Panorama General, Inventario, Ventas, Comisiones, Cuentas por Cobrar, Movimientos de Inventario, Cierres de Caja) con marca Magnus y fórmulas reales de Excel — quedó fuera de esta ronda de trabajo, a hacer aparte.

## Dashboard
KPIs reales conectados a base de datos: ventas del día, caja actual, comandas abiertas, deudas pendientes, alertas, barbero líder, producto más vendido, stock bajo.

---

# 7. La raíz del sitio ("/")

`http://127.0.0.1:8000/` responde con un `RedirectResponse` (307) a `/LOGIN/login.html` (`app/main.py`). No existe ya un `frontend/index.html` suelto — se eliminó el archivo de la raíz de `frontend/` que antes hacía esto con un `<meta http-equiv="refresh">`, para no depender de un truco client-side.

`app/main.py` monta, en este orden:
1. Rutas de la API (`/api/...`).
2. La ruta explícita `GET /` (el redirect) — se resuelve antes que los mounts de archivos estáticos.
3. `/media` → `backend/static` (fotos de producto).
4. `/` → `StaticFiles(directory=frontend/, html=True)` — catch-all para servir cada módulo (`/DASHBOARD/Dashboard.html`, `/INVENTARIOS/Inventario.html`, etc.).

---

# 8. Archivos eliminados en esta limpieza

Sin uso real en el sistema, confirmado por búsqueda en todo el código vivo antes de borrar:

- `reporte_prueba.xlsx` — export de ejemplo del volcado completo de tablas (no la plantilla aprobada de 7 hojas).
- `backend/tmp_schema_check.py` — script suelto de inspección manual de esquema.
- `backend/SECURITY_AND_ERD_PLAN.md` — plan de seguridad ya implementado, documentado ahora en este mismo archivo (sección 4).
- `frontend/login_luxury.html` — versión de login descartada, sin referencias.
- `frontend/magnus_dashboard_viking.html` — maqueta de dashboard descartada, sin referencias.
- `frontend/index.html` — ver sección 7.

---

# 9. Pendiente

1. **Excel reforzado**: reemplazar `excel_report_service.py` por la plantilla aprobada de 7 hojas (Panorama General, Inventario, Ventas, Comisiones por Barbero, Cuentas por Cobrar, Movimientos de Inventario, Cierres de Caja) con logo Magnus, colores de marca, créditos AvanzaTech y fórmulas reales de Excel conectadas a datos reales — a hacer en una sesión aparte.
2. **Empaquetado como instalador de Windows**:
   - Generar el ejecutable con PyInstaller.
   - Instalador con Inno Setup.
   - Acceso directo con ícono.
   - Confirmar que el ejecutable arranca con `magnus_barberia.db` vacío (ya soportado por SQLite + `create_tables.py`, falta el empaquetado en sí).

---

# 10. Ejecución en desarrollo

```
cd backend
python run_dev.py
```

Frontend: `http://127.0.0.1:8000` (redirige a login)
Swagger: `http://127.0.0.1:8000/api/docs`
Health check: `http://127.0.0.1:8000/api/health`

Crear/actualizar esquema desde los modelos:
```
python -m app.create_tables
```

Migraciones Alembic (recomendado sobre `create_tables.py` cuando ya existe un `.db` con datos):
```
alembic upgrade head
```

Seed inicial (usuario admin + roles):
```
python -m app.seed
```

## Suite de pruebas E2E

`backend/tests/test_e2e.py` es un script (no pytest) que golpea un servidor real corriendo en `http://127.0.0.1:8000` vía HTTP. **Nunca correrlo contra la base de datos de producción** (`magnus_barberia.db` real): apunta `DATABASE_URL` a un archivo SQLite temporal antes de levantar el servidor, corre la suite, y borra el archivo temporal al terminar. Cubre autenticación, CRUD base, el flujo completo de comanda (incluida caja y fiado), casos de borde y una prueba de volumen (2000 productos).

---

# 11. Reglas importantes para continuar

- No meter lógica de negocio en `main.py` — solo arma la app, incluye routers y sirve el frontend.
- Cada módulo respeta `models` → `schemas` → `services` → `routes`.
- Nunca borrar físicamente registros operativos: usar `is_deleted`/`is_active` (ver sección 5).
- No mezclar `OWNER_USERNAME` (singular, protege al barbero Mateo) con `OWNER_USERNAMES` (plural, permisos de dueño para mateo/admin) — son lógicas distintas, ver sección 4.
- No correr `test_e2e.py` contra la base de datos real.
- No subir `.env` real al repositorio (ya está en `.gitignore`).
