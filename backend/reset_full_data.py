"""
Script de mantenimiento de UN SOLO USO para MAGNUS BARBER.

Deja la base de datos lista para arrancar en producción real: borra TODOS los
datos operativos/de prueba (comandas, pagos, caja, cuentas por cobrar,
inventario, movimientos, servicios, categorías, clientes y auditoría) y
conserva EXACTAMENTE IGUAL todo lo demás: usuarios, barberos, roles,
permisos, permisos-por-rol, configuración del sistema y el código maestro.

Esto NO es una migración de Alembic (no toca el esquema, solo borra filas) y
NO se expone como endpoint de la API bajo ninguna circunstancia — es
exclusivamente un script de consola para correr manualmente, una sola vez,
antes de salir a producción.

Verificación de foreign keys (backend/app/models/*.py) hecha antes de escribir
este script: ninguna de las tablas protegidas (users, barbers, roles,
permissions, role_permissions, system_config, master_code_config) tiene una
columna FK que apunte a ninguna de las tablas listadas en TABLES_TO_TRUNCATE.
Todas las FKs que sí apuntan hacia esas tablas nacen desde otra tabla que
también está en la lista (ej. order_items.order_id -> orders.id, ambas se
truncan juntas). Por lo tanto TRUNCATE ... CASCADE no puede alcanzar ninguna
tabla protegida.

Corre desde la carpeta backend/:
    python reset_full_data.py

Pide confirmación explícita escribiendo "BORRAR TODO" (exacto) antes de tocar
absolutamente nada. Cualquier otra respuesta cancela sin modificar la base.
"""

import sys

from sqlalchemy import text

from app.database import SessionLocal


# Tablas que se truncan por completo (datos operativos / de prueba).
TABLES_TO_TRUNCATE = [
    "order_items",
    "orders",
    "payments",
    "accounts_receivable_payments",
    "accounts_receivable",
    "cash_movements",
    "cash_registers",
    "inventory_movements",
    "service_consumables",
    "alerts",
    "products",
    "categories",
    "services",
    "clients",
    "audit_logs",
]

# Tablas que deben quedar 100% intactas: mismos IDs, mismos datos.
PROTECTED_TABLES = [
    "users",
    "barbers",
    "roles",
    "permissions",
    "role_permissions",
    "system_config",
    "master_code_config",
]

# Barberos clave que deben seguir existiendo tal cual después del reset.
KEY_BARBER_NAMES = ["mateo", "cholo", "estiven"]

CONFIRM_PHRASE = "BORRAR TODO"


def _count(db, table_name: str) -> int:
    return db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()


def _print_table_counts(db, tables, label):
    print(f"\n{label}")
    for t in tables:
        print(f"    {t:35s} {_count(db, t)}")


def _snapshot_barbers(db):
    rows = db.execute(
        text("SELECT id, full_name, user_id, is_active, is_deleted FROM barbers ORDER BY id")
    ).fetchall()
    return [tuple(r) for r in rows]


def _snapshot_users(db):
    rows = db.execute(
        text("SELECT id, username, full_name, role_id, is_active FROM users ORDER BY id")
    ).fetchall()
    return [tuple(r) for r in rows]


def _print_barbers(barbers):
    for bid, full_name, user_id, is_active, is_deleted in barbers:
        estado = "activo" if is_active else "inactivo"
        if is_deleted:
            estado += " · ELIMINADO"
        print(f"    #{bid:<5} {full_name:<30} {estado}")


def _print_users(users):
    for uid, username, full_name, role_id, is_active in users:
        estado = "activo" if is_active else "inactivo"
        print(f"    #{uid:<5} {username:<20} {full_name:<28} {estado}")


def main():
    db = SessionLocal()
    try:
        print("=" * 72)
        print("  MAGNUS BARBER — RESET COMPLETO DE DATOS OPERATIVOS")
        print("=" * 72)
        print(
            "\nEste script deja la base lista para producción real: borra TODOS los\n"
            "datos operativos/de prueba y conserva intactos usuarios, barberos,\n"
            "roles, permisos y configuración del sistema."
        )

        # ── FASE 1: conteo actual, solo lectura ──────────────────────────
        _print_table_counts(db, TABLES_TO_TRUNCATE, "Se va a BORRAR (TRUNCATE) el contenido de estas tablas:")
        _print_table_counts(db, PROTECTED_TABLES, "\nSe va a CONSERVAR intacto el contenido de estas tablas:")

        barbers_before = _snapshot_barbers(db)
        users_before = _snapshot_users(db)

        print("\nBarberos actuales (deben seguir existiendo exactamente igual después):")
        _print_barbers(barbers_before)

        print(f"\nUsuarios actuales ({len(users_before)}) — todos deben poder seguir entrando igual:")
        _print_users(users_before)

        # ── FASE 2: confirmación explícita ───────────────────────────────
        print("\n" + "-" * 72)
        print("NO se ha tocado nada todavía.")
        print(f'Para continuar y BORRAR los datos operativos, escribe exactamente:  {CONFIRM_PHRASE}')
        print("Cualquier otra cosa cancela sin modificar la base de datos.")
        print("-" * 72)

        try:
            answer = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nCancelado. No se modificó absolutamente nada.")
            return

        if answer != CONFIRM_PHRASE:
            print("\nCancelado. No se modificó absolutamente nada.")
            return

        # ── FASE 3: TRUNCATE en una sola transacción ─────────────────────
        print("\nEjecutando TRUNCATE dentro de una transacción...")
        table_list = ", ".join(TABLES_TO_TRUNCATE)
        db.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"))
        db.commit()
        print("TRUNCATE aplicado y confirmado (COMMIT).")

    except Exception as exc:
        db.rollback()
        print("\n" + "!" * 72)
        print("  ERROR: algo falló durante el reset. Se hizo ROLLBACK completo.")
        print(f"  Detalle: {exc}")
        print("  La base de datos NO fue modificada.")
        print("!" * 72)
        db.close()
        sys.exit(1)

    # ── FASE 4: verificación posterior (fuera del try de la transacción,
    #    ya con los cambios confirmados) ──────────────────────────────────
    try:
        print("\n" + "=" * 72)
        print("  VERIFICACIÓN POST-RESET")
        print("=" * 72)

        all_zero = True
        print("\nConteo de tablas truncadas (deben quedar todas en 0):")
        for t in TABLES_TO_TRUNCATE:
            c = _count(db, t)
            ok = c == 0
            all_zero = all_zero and ok
            print(f"    {t:35s} {c:<6} [{'OK' if ok else 'FALLO'}]")

        barbers_after = _snapshot_barbers(db)
        users_after = _snapshot_users(db)

        barbers_ok = barbers_after == barbers_before
        users_ok = users_after == users_before

        print(
            f"\nBarberos: antes={len(barbers_before)}  después={len(barbers_after)}  "
            f"[{'OK, sin cambios' if barbers_ok else 'FALLO: la tabla cambió'}]"
        )
        if not barbers_ok:
            print("  Estado actual de barbers:")
            _print_barbers(barbers_after)

        print(
            f"Usuarios: antes={len(users_before)}  después={len(users_after)}  "
            f"[{'OK, sin cambios' if users_ok else 'FALLO: la tabla cambió'}]"
        )
        if not users_ok:
            print("  Estado actual de users:")
            _print_users(users_after)

        by_lower_name = {name.lower(): (bid, is_active, is_deleted)
                          for bid, name, _uid, is_active, is_deleted in barbers_after}

        print("\nBarberos clave (deben seguir existiendo, sin cambios respecto a antes):")
        key_barbers_ok = True
        for key in KEY_BARBER_NAMES:
            match = by_lower_name.get(key)
            if not match:
                key_barbers_ok = False
                print(f"    {key.capitalize():<10} FALTA — no se encontró un barbero con ese nombre")
                continue
            bid, is_active, is_deleted = match
            if is_deleted:
                key_barbers_ok = False
            estado = "activo" if is_active else "inactivo"
            print(f"    {key.capitalize():<10} presente (#{bid}), {estado}"
                  f"{' · ELIMINADO — revisar' if is_deleted else ''}")

        if all_zero and barbers_ok and users_ok and key_barbers_ok:
            print("\n" + "=" * 72)
            print("  RESET COMPLETADO CORRECTAMENTE.")
            print("  Datos operativos borrados. Usuarios y barberos intactos.")
            print("  La base de datos está lista para arrancar en producción.")
            print("=" * 72)
        else:
            print("\n" + "!" * 72)
            print("  ATENCIÓN: el TRUNCATE se ejecutó, pero alguna verificación")
            print("  posterior no pasó. Revisa el detalle de arriba con cuidado.")
            print("!" * 72)
            sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()