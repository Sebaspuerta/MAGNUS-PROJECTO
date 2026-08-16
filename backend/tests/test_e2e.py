#!/usr/bin/env python3
"""
Magnus Barber — Suite de pruebas E2E
=====================================================
Prueba los endpoints reales del backend vía HTTP.

ANTES DE EJECUTAR
-----------------
1. Arranca el servidor:    uvicorn app.main:app --reload
2. (Recomendado) Apunta el servidor a una base de datos de PRUEBA, no la de
   producción.  Copia .env en .env.test, cambia DATABASE_URL a otra BD
   (ej. magnus_test) y arranca el server con esa config.
   Si no tienes BD separada, el script limpia todo lo que crea al finalizar.

EJECUTAR
--------
    cd MAGNUS-PROJECTO
    python backend/tests/test_e2e.py

DEPENDENCIAS
------------
    pip install requests
"""

# ── CONFIGURACIÓN ─────────────────────────────────────────────────────────────
BASE_URL          = "http://127.0.0.1:8000"
ADMIN_USER        = "admin"
ADMIN_PASS        = "admin123"
VOLUME_COUNT      = 2000        # productos a insertar en Bloque 6
VOLUME_WARN_SECS  = 2.0         # advertencia si GET tarda más de esto
# ─────────────────────────────────────────────────────────────────────────────

import sys
import time
from datetime import datetime

try:
    import requests
except ImportError:
    print("ERROR: módulo 'requests' no instalado.  Ejecuta:  pip install requests")
    sys.exit(1)

TS = int(time.time())   # sufijo único → evita colisiones con datos existentes

# ── ESTADO GLOBAL ─────────────────────────────────────────────────────────────
_results: list[tuple[str, bool, str]] = []
_ctx: dict = {}
_cleanup: dict = {
    "barberos":         [],
    "clientes":         [],
    "servicios":        [],
    "productos":        [],
    "volume_productos": [],
    "comandas_abiertas":[],
}


# ── UTILIDADES ────────────────────────────────────────────────────────────────
def _rec(name: str, passed: bool, detail: str = "") -> bool:
    sym  = "✓ PASS" if passed else "✗ FAIL"
    suf  = f"  → {detail}" if detail else ""
    print(f"  {sym}  {name}{suf}")
    _results.append((name, passed, detail))
    return passed


def _warn(msg: str):
    print(f"  ⚠ WARN  {msg}")


def _hdr() -> dict:
    tok = _ctx.get("token")
    return {"Authorization": f"Bearer {tok}"} if tok else {}


def _detail(r) -> str:
    if r is None:
        return "sin respuesta (¿servidor caído?)"
    try:
        body = r.json()
    except Exception:
        body = r.text[:300]
    return f"HTTP {r.status_code} · {body}"


def _get(path: str, params: dict = None):
    try:
        return requests.get(
            BASE_URL + path, headers=_hdr(), params=params, timeout=30
        )
    except Exception as exc:
        print(f"    [red] GET {path} — {exc}")
        return None


def _post(path: str, body: dict, auth: bool = True):
    try:
        h = _hdr() if auth else {}
        return requests.post(
            BASE_URL + path, json=body, headers=h, timeout=30
        )
    except Exception as exc:
        print(f"    [red] POST {path} — {exc}")
        return None


def _patch(path: str, body: dict = None, auth: bool = True):
    try:
        h = _hdr() if auth else {}
        return requests.patch(
            BASE_URL + path, json=body if body is not None else {}, headers=h, timeout=30
        )
    except Exception as exc:
        print(f"    [red] PATCH {path} — {exc}")
        return None


# ── BLOQUE 1 · AUTENTICACIÓN ─────────────────────────────────────────────────
def bloque1():
    print("\n══════════════════════════════════════════")
    print("  BLOQUE 1 · AUTENTICACIÓN")
    print("══════════════════════════════════════════")

    # 1.1  Login correcto
    r = _post("/api/security/login",
              {"username": ADMIN_USER, "password": ADMIN_PASS},
              auth=False)
    if r and r.status_code == 200:
        tok = r.json().get("access_token")
        if _rec("Login correcto → 200 + access_token", bool(tok)):
            _ctx["token"] = tok
    else:
        _rec("Login correcto → 200 + access_token", False, _detail(r))
        print("\n  !! Sin token — los bloques 2-6 fallarán.")
        print(f"     Revisa ADMIN_USER='{ADMIN_USER}' y ADMIN_PASS='{ADMIN_PASS}'")

    # 1.2  Login con contraseña mala → debe rechazar
    r = _post("/api/security/login",
              {"username": ADMIN_USER, "password": "WRONG_PASS_XYZ_999"},
              auth=False)
    _rec("Login con contraseña mala → rechazado 401",
         r is not None and r.status_code == 401,
         "" if r and r.status_code == 401 else _detail(r))

    # 1.3  Endpoint protegido sin token → debe rechazar
    saved = _ctx.pop("token", None)
    r = _get("/api/security/me")
    _rec("Endpoint protegido sin token → 401/403",
         r is not None and r.status_code in (401, 403),
         "" if r and r.status_code in (401, 403) else _detail(r))
    if saved:
        _ctx["token"] = saved


# ── BLOQUE 2 · DATOS BASE ─────────────────────────────────────────────────────
def bloque2():
    print("\n══════════════════════════════════════════")
    print("  BLOQUE 2 · DATOS BASE")
    print("══════════════════════════════════════════")

    if not _ctx.get("token"):
        print("  (Skipped — sin token)")
        return

    # ── Barbero ──
    r = _post("/api/barbers", {
        "full_name":        f"Barbero E2E {TS}",
        "commission_type":  "porcentaje",
        "commission_value": 30
    })
    if r and r.status_code == 200:
        b = r.json()
        _ctx["barbero_id"] = b["id"]
        _cleanup["barberos"].append(b["id"])
        _rec("Crear barbero → 200", True, f"id={b['id']}")
    else:
        _rec("Crear barbero → 200", False, _detail(r))

    if _ctx.get("barbero_id"):
        r = _get("/api/barbers")
        found = r and r.status_code == 200 and any(
            x["id"] == _ctx["barbero_id"] for x in r.json()
        )
        _rec("Barbero aparece en GET /api/barbers", found,
             "" if found else _detail(r))

    # ── Cliente ──
    r = _post("/api/clients", {
        "full_name": f"Cliente E2E {TS}",
        "phone":     "3001234567"
    })
    if r and r.status_code == 200:
        c = r.json()
        _ctx["cliente_id"] = c["id"]
        _cleanup["clientes"].append(c["id"])
        _rec("Crear cliente → 200", True, f"id={c['id']}")
    else:
        _rec("Crear cliente → 200", False, _detail(r))

    if _ctx.get("cliente_id"):
        r = _get("/api/clients")
        found = r and r.status_code == 200 and any(
            x["id"] == _ctx["cliente_id"] for x in r.json()
        )
        _rec("Cliente aparece en GET /api/clients", found,
             "" if found else _detail(r))

    # ── Servicio ──
    r = _post("/api/services", {
        "name":     f"Servicio E2E {TS}",
        "price":    25000,
        "category": "Corte"
    })
    if r and r.status_code == 200:
        s = r.json()
        _ctx["servicio_id"]    = s["id"]
        _ctx["servicio_price"] = s["price"]
        _cleanup["servicios"].append(s["id"])
        _rec("Crear servicio → 200", True, f"id={s['id']}  precio={s['price']}")
    else:
        _rec("Crear servicio → 200", False, _detail(r))

    if _ctx.get("servicio_id"):
        r = _get("/api/services")
        found = r and r.status_code == 200 and any(
            x["id"] == _ctx["servicio_id"] for x in r.json()
        )
        _rec("Servicio aparece en GET /api/services", found,
             "" if found else _detail(r))

    # ── Producto con stock 20 ──
    r = _post("/api/inventory/products", {
        "name":          f"Producto E2E {TS}",
        "product_type":  "venta",
        "sale_price":    15000,
        "purchase_cost": 8000,
        "current_stock": 20,
        "minimum_stock": 5
    })
    if r and r.status_code == 200:
        p = r.json()
        _ctx["producto_id"]    = p["id"]
        _ctx["producto_stock"] = p["current_stock"]
        _cleanup["productos"].append(p["id"])
        _rec("Crear producto con stock=20 → 200", True,
             f"id={p['id']}  stock={p['current_stock']}")
    else:
        _rec("Crear producto con stock=20 → 200", False, _detail(r))

    if _ctx.get("producto_id"):
        r = _get("/api/inventory/products")
        found = r and r.status_code == 200 and any(
            x["id"] == _ctx["producto_id"] for x in r.json()
        )
        _rec("Producto aparece en GET /api/inventory/products", found,
             "" if found else _detail(r))


# ── EDGE CASE PREVIO: comanda sin caja ────────────────────────────────────────
# Se ejecuta ANTES de bloque3 para que aún no haya caja abierta.
def _edge_sin_caja():
    """PASS si el backend rechaza cerrar una comanda cuando no hay caja abierta."""
    print("\n  [Pre-B3] Verificando 'sin caja abierta'...")

    # Comprobar si ya hay alguna caja abierta (podría venir de datos reales)
    r = _get("/api/cash-registers")
    if r and r.status_code == 200:
        if any(not x.get("is_closed") for x in r.json()):
            _warn("'Sin caja' → OMITIDO (ya existe caja abierta en la BD)")
            return

    barbero_id  = _ctx.get("barbero_id")
    servicio_id = _ctx.get("servicio_id")
    if not barbero_id or not servicio_id:
        _warn("'Sin caja' → OMITIDO (sin barbero/servicio del Bloque 2)")
        return

    # Crear comanda y agregarle ítem
    r = _post("/api/orders", {
        "barber_id": barbero_id,
        "is_fiado":  False,
        "discount":  0
    })
    if not (r and r.status_code == 200):
        _rec("Sin caja: crear comanda temporal → 200", False, _detail(r))
        return

    oid = r.json()["id"]
    _cleanup["comandas_abiertas"].append(oid)

    _post(f"/api/orders/{oid}/items", {
        "item_type":  "servicio",
        "service_id": servicio_id,
        "quantity":   1,
        "unit_price": 25000
    })

    # Intentar cerrar sin caja → debe fallar
    r = _patch(f"/api/orders/{oid}/close", {
        "barber_id":      barbero_id,
        "payment_method": "efectivo"
    })
    rechazado = r is not None and r.status_code in (400, 422)
    _rec("Cerrar comanda sin caja abierta → rechazado 400/422",
         rechazado,
         "" if rechazado else _detail(r))


# ── BLOQUE 3 · FLUJO CRÍTICO DE COMANDA ──────────────────────────────────────
def bloque3():
    print("\n══════════════════════════════════════════")
    print("  BLOQUE 3 · FLUJO CRÍTICO DE COMANDA")
    print("══════════════════════════════════════════")

    if not _ctx.get("token"):
        print("  (Skipped — sin token)")
        return

    barbero_id  = _ctx.get("barbero_id")
    cliente_id  = _ctx.get("cliente_id")
    servicio_id = _ctx.get("servicio_id")
    producto_id = _ctx.get("producto_id")

    if not barbero_id:
        print("  (Skipped — sin barbero del Bloque 2)")
        return

    # 3.1  Abrir caja (o reutilizar la que ya esté abierta)
    r = _get("/api/cash-registers")
    caja_id = None
    if r and r.status_code == 200:
        for reg in r.json():
            if not reg.get("is_closed"):
                caja_id = reg["id"]
                _rec("Caja abierta reutilizada (pre-existente)", True,
                     f"id={caja_id}")
                break

    if not caja_id:
        r = _post("/api/cash-registers/open", {
            "opening_amount": 50000,
            "notes":          f"Test E2E {TS}"
        })
        if r and r.status_code == 200:
            caja_id = r.json()["id"]
            _ctx["caja_abierta_por_test"] = True
            _rec("Abrir caja opening_amount=50000 → 200", True,
                 f"id={caja_id}")
        else:
            _rec("Abrir caja → 200", False, _detail(r))
            print("  !! Sin caja: resto del Bloque 3 omitido.")
            return

    _ctx["caja_id"] = caja_id

    # 3.2  Crear comanda
    r = _post("/api/orders", {
        "client_id": cliente_id,
        "barber_id": barbero_id,
        "is_fiado":  False,
        "discount":  0
    })
    if not (r and r.status_code == 200):
        _rec("Crear comanda → 200", False, _detail(r))
        return
    comanda = r.json()
    order_id = comanda["id"]
    _ctx["comanda_id"] = order_id
    _cleanup["comandas_abiertas"].append(order_id)
    _rec("Crear comanda → 200 status='abierta'",
         comanda.get("status") == "abierta",
         f"id={order_id}")

    # 3.3  Agregar servicio
    if servicio_id:
        r = _post(f"/api/orders/{order_id}/items", {
            "item_type":  "servicio",
            "service_id": servicio_id,
            "quantity":   1,
            "unit_price": _ctx.get("servicio_price", 25000)
        })
        _rec("Agregar ítem servicio → 200",
             r is not None and r.status_code == 200,
             "" if r and r.status_code == 200 else _detail(r))

    # 3.4  Agregar producto (cantidad 1 → bajará el stock en 1)
    if producto_id:
        r = _post(f"/api/orders/{order_id}/items", {
            "item_type":  "producto",
            "product_id": producto_id,
            "quantity":   1,
            "unit_price": 15000
        })
        _rec("Agregar ítem producto → 200",
             r is not None and r.status_code == 200,
             "" if r and r.status_code == 200 else _detail(r))

    # 3.5  Stock ANTES de cerrar
    stock_antes = None
    if producto_id:
        r = _get(f"/api/inventory/products/{producto_id}")
        if r and r.status_code == 200:
            stock_antes = r.json().get("current_stock")
            print(f"    [info] Stock producto antes de cerrar: {stock_antes}")

    # 3.6  Cerrar comanda (pago en efectivo)
    r = _patch(f"/api/orders/{order_id}/close", {
        "barber_id":        barbero_id,
        "cash_register_id": caja_id,
        "payment_method":   "efectivo"
        # payment_amount omitido → paga el total
    })
    if not (r and r.status_code == 200):
        _rec("Cerrar comanda → 200", False, _detail(r))
        return

    cerrada = r.json()
    # Ya no está "abierta", sacarlo de la lista de pendientes por cancelar
    if order_id in _cleanup["comandas_abiertas"]:
        _cleanup["comandas_abiertas"].remove(order_id)
    _rec("Cerrar comanda → 200",
         cerrada.get("status") == "cerrada",
         f"status={cerrada.get('status')}  payment_status={cerrada.get('payment_status')}")

    # 3.7a  Stock bajó en 1
    if producto_id and stock_antes is not None:
        r = _get(f"/api/inventory/products/{producto_id}")
        if r and r.status_code == 200:
            stock_despues = r.json().get("current_stock")
            ok = (stock_despues == stock_antes - 1)
            _rec(f"Stock bajó de {stock_antes} → {stock_antes - 1}",
                 ok,
                 f"stock actual={stock_despues}" if not ok else "")
        else:
            _rec("Verificar stock post-venta", False, _detail(r))

    # 3.7b  Caja registró movimiento ingreso_venta
    r = _get("/api/cash-movements", {"cash_register_id": caja_id})
    if r and r.status_code == 200:
        movs = r.json()
        ingreso = any(
            m.get("movement_type") == "ingreso_venta"
            and m.get("reference_id") == order_id
            for m in movs
        )
        _rec("Caja registró movimiento ingreso_venta para la comanda",
             ingreso,
             "" if ingreso else f"tipos en caja: {[m.get('movement_type') for m in movs[:5]]}")
    else:
        _rec("GET /api/cash-movements → 200", False, _detail(r))

    # 3.7c  Dashboard: ingresos > 0 y comandas cerradas >= 1
    r = _get("/api/dashboard/summary")
    if r and r.status_code == 200:
        d     = r.json()
        today = d.get("today", {})
        ing   = today.get("received_total", 0)
        cerr  = today.get("orders_closed",  0)
        _rec(f"Dashboard ingresos_hoy={ing} > 0",   ing  > 0)
        _rec(f"Dashboard comandas_cerradas={cerr} ≥ 1", cerr >= 1)
    else:
        _rec("GET /api/dashboard/summary → 200", False, _detail(r))

    # 3.7d  Comanda en estado 'cerrada'
    r = _get(f"/api/orders/{order_id}")
    if r and r.status_code == 200:
        st = r.json().get("status")
        _rec(f"Comanda status='cerrada' (actual: '{st}')", st == "cerrada")
    else:
        _rec("GET comanda post-cierre → 200", False, _detail(r))


# ── BLOQUE 4 · FIADO ──────────────────────────────────────────────────────────
def bloque4():
    print("\n══════════════════════════════════════════")
    print("  BLOQUE 4 · FIADO (CUENTAS POR COBRAR)")
    print("══════════════════════════════════════════")

    if not _ctx.get("token"):
        print("  (Skipped — sin token)")
        return

    barbero_id  = _ctx.get("barbero_id")
    cliente_id  = _ctx.get("cliente_id")
    servicio_id = _ctx.get("servicio_id")

    if not (barbero_id and cliente_id and servicio_id):
        print("  (Skipped — faltan datos del Bloque 2)")
        return

    # 4.1  Comanda fiada
    r = _post("/api/orders", {
        "client_id": cliente_id,
        "barber_id": barbero_id,
        "is_fiado":  True,
        "discount":  0
    })
    if not (r and r.status_code == 200):
        _rec("Crear comanda fiada → 200", False, _detail(r))
        return

    fiado     = r.json()
    fiado_id  = fiado["id"]
    _cleanup["comandas_abiertas"].append(fiado_id)
    _rec("Crear comanda is_fiado=True → 200",
         fiado.get("is_fiado") is True,
         f"id={fiado_id}")

    # 4.2  Agregar servicio
    r = _post(f"/api/orders/{fiado_id}/items", {
        "item_type":  "servicio",
        "service_id": servicio_id,
        "quantity":   1,
        "unit_price": _ctx.get("servicio_price", 25000)
    })
    _rec("Agregar ítem servicio a comanda fiada → 200",
         r is not None and r.status_code == 200,
         "" if r and r.status_code == 200 else _detail(r))

    # 4.3  Cerrar fiada (sin caja, sin payment_method)
    r = _patch(f"/api/orders/{fiado_id}/close", {
        "barber_id": barbero_id
    })
    if not (r and r.status_code == 200):
        _rec("Cerrar comanda fiada → 200", False, _detail(r))
        return

    cerrada = r.json()
    if fiado_id in _cleanup["comandas_abiertas"]:
        _cleanup["comandas_abiertas"].remove(fiado_id)
    _rec("Comanda fiada cerrada: status='cerrada' payment_status='fiado'",
         cerrada.get("status") == "cerrada" and cerrada.get("payment_status") == "fiado",
         f"status={cerrada.get('status')} pay={cerrada.get('payment_status')}")

    # 4.4  Aparece en accounts-receivable con saldo > 0
    r = _get("/api/accounts-receivable", {"client_id": cliente_id})
    ar_id = None
    if r and r.status_code == 200:
        match = [a for a in r.json() if a.get("order_id") == fiado_id]
        if match:
            ar_id   = match[0]["id"]
            balance = match[0].get("balance", 0)
            _rec(f"Fiado aparece en AR con balance={balance} > 0", balance > 0)
        else:
            _rec("Fiado aparece en /api/accounts-receivable", False,
                 "no encontrada en la lista")
    else:
        _rec("GET /api/accounts-receivable → 200", False, _detail(r))

    # 4.5  Registrar abono y verificar que el saldo baja
    if ar_id:
        r_ar       = _get(f"/api/accounts-receivable/{ar_id}")
        saldo_antes = (
            r_ar.json().get("balance", 0)
            if r_ar and r_ar.status_code == 200 else None
        )

        r = _post(f"/api/accounts-receivable/{ar_id}/payments", {
            "amount":         10000,
            "payment_method": "efectivo",
            "note":           f"Abono test {TS}"
        })
        if r and r.status_code == 200:
            saldo_despues = r.json().get("balance", 0)
            _rec(
                f"Abono registrado: saldo {saldo_antes} → {saldo_despues}",
                saldo_antes is not None and saldo_despues < saldo_antes
            )
        else:
            _rec("Registrar abono → 200", False, _detail(r))


# ── BLOQUE 5 · CASOS DE BORDE ─────────────────────────────────────────────────
def bloque5():
    print("\n══════════════════════════════════════════")
    print("  BLOQUE 5 · CASOS DE BORDE")
    print("══════════════════════════════════════════")

    if not _ctx.get("token"):
        print("  (Skipped — sin token)")
        return

    # 5.1  Producto sale_price negativo → Pydantic Field(ge=0) → 422
    r = _post("/api/inventory/products", {
        "name":          f"PrecioNeg {TS}",
        "product_type":  "venta",
        "sale_price":    -500,
        "current_stock": 0
    })
    _rec("Producto sale_price negativo → rechazado 422",
         r is not None and r.status_code == 422,
         "" if r and r.status_code == 422 else _detail(r))

    # 5.2  Producto current_stock negativo → 422
    r = _post("/api/inventory/products", {
        "name":          f"StockNeg {TS}",
        "product_type":  "venta",
        "sale_price":    1000,
        "current_stock": -5
    })
    _rec("Producto current_stock negativo → rechazado 422",
         r is not None and r.status_code == 422,
         "" if r and r.status_code == 422 else _detail(r))

    # 5.3  Barbero sin full_name (campo obligatorio ausente) → 422
    r = _post("/api/barbers", {
        "commission_type":  "porcentaje",
        "commission_value": 0
    })
    _rec("Barbero sin full_name → rechazado 422",
         r is not None and r.status_code == 422,
         "" if r and r.status_code == 422 else _detail(r))

    # 5.4  Cerrar dos veces la misma comanda → segunda falla
    comanda_id = _ctx.get("comanda_id")
    barbero_id = _ctx.get("barbero_id")
    if comanda_id and barbero_id:
        r = _patch(f"/api/orders/{comanda_id}/close", {
            "barber_id":      barbero_id,
            "payment_method": "efectivo"
        })
        rechazado = r is not None and r.status_code in (400, 422)
        _rec("Cerrar comanda ya cerrada → rechazado 400/422",
             rechazado,
             "" if rechazado else _detail(r))
    else:
        _warn("Doble cierre → OMITIDO (sin comanda del Bloque 3)")

    # 5.5  Cancelar una comanda ya cerrada → rechazada, sin efectos colaterales
    producto_id = _ctx.get("producto_id")
    caja_id     = _ctx.get("caja_id")
    if comanda_id and caja_id:
        r_antes = _get(f"/api/orders/{comanda_id}")
        estado_antes = r_antes.json() if r_antes and r_antes.status_code == 200 else None

        stock_antes = None
        if producto_id:
            r = _get(f"/api/inventory/products/{producto_id}")
            if r and r.status_code == 200:
                stock_antes = r.json().get("current_stock")

        r = _get("/api/cash-movements", {"cash_register_id": caja_id})
        movs_antes = len(r.json()) if r and r.status_code == 200 else None

        r = _patch(f"/api/orders/{comanda_id}/cancel")
        rechazado = r is not None and r.status_code == 400
        _rec("Cancelar comanda ya cerrada → rechazado 400",
             rechazado,
             "" if rechazado else _detail(r))

        r_despues = _get(f"/api/orders/{comanda_id}")
        estado_despues = r_despues.json() if r_despues and r_despues.status_code == 200 else None
        _rec("Comanda sigue 'cerrada' tras intento de cancelación fallido",
             estado_antes is not None and estado_despues is not None
             and estado_despues.get("status") == "cerrada"
             and estado_despues.get("status") == estado_antes.get("status")
             and estado_despues.get("payment_status") == estado_antes.get("payment_status"),
             f"antes={estado_antes and estado_antes.get('status')}  después={estado_despues and estado_despues.get('status')}")

        if producto_id and stock_antes is not None:
            r = _get(f"/api/inventory/products/{producto_id}")
            stock_despues = r.json().get("current_stock") if r and r.status_code == 200 else None
            _rec(f"Stock de producto sin cambios tras cancelación fallida ({stock_antes})",
                 stock_despues == stock_antes,
                 f"stock actual={stock_despues}" if stock_despues != stock_antes else "")

        if movs_antes is not None:
            r = _get("/api/cash-movements", {"cash_register_id": caja_id})
            movs_despues = len(r.json()) if r and r.status_code == 200 else None
            _rec(f"Movimientos de caja sin cambios tras cancelación fallida ({movs_antes})",
                 movs_despues == movs_antes,
                 f"movimientos actuales={movs_despues}" if movs_despues != movs_antes else "")
    else:
        _warn("Cancelar comanda cerrada → OMITIDO (sin comanda/caja del Bloque 3)")

    # 5.6  Cancelar una comanda abierta → sigue funcionando normal
    cliente_id = _ctx.get("cliente_id")
    if barbero_id:
        r = _post("/api/orders", {
            "client_id": cliente_id,
            "barber_id": barbero_id,
            "is_fiado":  False,
            "discount":  0
        })
        if r and r.status_code == 200:
            abierta_id = r.json()["id"]
            _rec("Crear comanda para prueba de cancelación → 200 status='abierta'",
                 r.json().get("status") == "abierta",
                 f"id={abierta_id}")

            r = _patch(f"/api/orders/{abierta_id}/cancel")
            _rec("Cancelar comanda abierta → 200 status='cancelada'",
                 r is not None and r.status_code == 200
                 and r.json().get("status") == "cancelada",
                 "" if r and r.status_code == 200 else _detail(r))
        else:
            _rec("Crear comanda para prueba de cancelación → 200", False, _detail(r))
    else:
        _warn("Cancelar comanda abierta → OMITIDO (sin barbero del Bloque 2)")


# ── BLOQUE 6 · VOLUMEN ────────────────────────────────────────────────────────
def bloque6():
    print("\n══════════════════════════════════════════")
    print(f"  BLOQUE 6 · VOLUMEN ({VOLUME_COUNT} productos)")
    print("══════════════════════════════════════════")

    if not _ctx.get("token"):
        print("  (Skipped — sin token)")
        return

    # 6.1  Inserción masiva
    print(f"  Insertando {VOLUME_COUNT} productos (esto puede tardar ~60-90 s)...")
    t0       = time.time()
    vol_ids  = []
    errores  = 0

    for i in range(VOLUME_COUNT):
        r = _post("/api/inventory/products", {
            "name":          f"VolTest_{TS}_{i:04d}",
            "product_type":  "venta",
            "sale_price":    1000,
            "current_stock": 0
        })
        if r and r.status_code == 200:
            vol_ids.append(r.json()["id"])
        else:
            errores += 1

    t_ins = time.time() - t0
    _cleanup["volume_productos"].extend(vol_ids)
    insertados = len(vol_ids)

    _rec(
        f"Insertar {VOLUME_COUNT} productos → {insertados} OK / {errores} errores",
        errores == 0,
        f"tiempo={t_ins:.1f}s  ({VOLUME_COUNT / max(t_ins, 0.001):.0f} req/s)"
    )
    print(f"    Tiempo de inserción: {t_ins:.2f}s")

    # 6.2  GET de la lista con volumen acumulado
    print(f"  Consultando lista con ~{insertados} productos nuevos...")
    t1 = time.time()
    r  = _get("/api/inventory/products", {"include_inactive": False})
    t_q = time.time() - t1

    if r and r.status_code == 200:
        total = len(r.json())
        print(f"    GET devolvió {total} registros en {t_q:.3f}s")
        if t_q > VOLUME_WARN_SECS:
            _warn(f"GET /api/inventory/products tardó {t_q:.2f}s (umbral={VOLUME_WARN_SECS}s)")
        else:
            _rec(f"GET lista con volumen respondió en {t_q:.3f}s ≤ {VOLUME_WARN_SECS}s",
                 True)
    else:
        _rec("GET /api/inventory/products con volumen → 200", False, _detail(r))

    # 6.3  Limpieza de los productos de volumen
    print(f"  Desactivando {insertados} productos de volumen (limpieza)...")
    t2    = time.time()
    ok_c  = 0
    for pid in vol_ids:
        r = _patch(f"/api/inventory/products/{pid}/deactivate")
        if r and r.status_code == 200:
            ok_c += 1
    t_c = time.time() - t2

    _rec(
        f"Limpieza volumen: {ok_c}/{insertados} desactivados",
        ok_c == insertados,
        f"tiempo={t_c:.1f}s"
    )
    _cleanup["volume_productos"].clear()  # ya limpiados


# ── LIMPIEZA FINAL ────────────────────────────────────────────────────────────
def cleanup():
    print("\n══════════════════════════════════════════")
    print("  LIMPIEZA FINAL")
    print("══════════════════════════════════════════")

    if not _ctx.get("token"):
        print("  (Sin token — limpieza omitida)")
        return

    # Cancelar comandas que quedaron abiertas
    for oid in list(_cleanup["comandas_abiertas"]):
        r = _get(f"/api/orders/{oid}")
        if r and r.status_code == 200:
            st = r.json().get("status")
            if st in ("abierta", "pendiente"):
                _patch(f"/api/orders/{oid}/cancel")

    # Datos base: desactivar
    for bid in _cleanup["barberos"]:
        _patch(f"/api/barbers/{bid}/deactivate")
    for cid in _cleanup["clientes"]:
        _patch(f"/api/clients/{cid}/deactivate")
    for sid in _cleanup["servicios"]:
        _patch(f"/api/services/{sid}/deactivate")
    for pid in _cleanup["productos"]:
        _patch(f"/api/inventory/products/{pid}/deactivate")

    # Volumen (si bloque6 no los limpió, p.ej. porque falló)
    for pid in _cleanup["volume_productos"]:
        _patch(f"/api/inventory/products/{pid}/deactivate")

    # Cerrar la caja si fue abierta por el test (no cerrar las pre-existentes)
    if _ctx.get("caja_abierta_por_test") and _ctx.get("caja_id"):
        r = _patch(f"/api/cash-registers/{_ctx['caja_id']}/close", {
            "closing_amount": 0,
            "notes":          f"Cierre automático test E2E {TS}"
        })
        if r and r.status_code == 200:
            print(f"  Caja de test id={_ctx['caja_id']} cerrada automáticamente.")

    n_b = len(_cleanup["barberos"])
    n_c = len(_cleanup["clientes"])
    n_s = len(_cleanup["servicios"])
    n_p = len(_cleanup["productos"])
    print(f"  Desactivados: {n_b} barbero(s), {n_c} cliente(s), "
          f"{n_s} servicio(s), {n_p} producto(s).")
    print("  Nota: registros en AR (cuentas fiadas) permanecen en la BD;")
    print("  no hay endpoint DELETE para eliminarlos vía API.")


# ── RESUMEN ───────────────────────────────────────────────────────────────────
def resumen() -> int:
    print("\n" + "═" * 50)
    print("  RESUMEN")
    print("═" * 50)
    total  = len(_results)
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = total - passed
    print(f"  Total: {total}   ✓ PASS: {passed}   ✗ FAIL: {failed}")

    if failed:
        print("\n  Pruebas fallidas:")
        for name, ok, detail in _results:
            if not ok:
                print(f"    ✗ {name}")
                if detail:
                    print(f"        {detail}")

    print("═" * 50)
    return failed


# ── PUNTO DE ENTRADA ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("═" * 50)
    print("  MAGNUS BARBER — Suite de pruebas E2E")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC   TS={TS}")
    print(f"  Servidor: {BASE_URL}")
    print("═" * 50)

    bloque1()
    bloque2()
    _edge_sin_caja()   # debe correr ANTES de que bloque3 abra la caja
    bloque3()
    bloque4()
    bloque5()
    bloque6()
    cleanup()

    sys.exit(0 if resumen() == 0 else 1)
