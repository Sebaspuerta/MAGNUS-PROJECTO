# Plan de Seguridad y MER para MAGNUS BARBER SYSTEM v1.0

## 1. Resumen de seguridad implementada

- Se mantiene FastAPI + JWT + bcrypt para autenticación segura.
- Se refuerza la validación de token con expiración y verificación del `sub`.
- Se implementa bloqueo temporal tras 5 intentos fallidos durante el login.
- Se agregan campos importantes al modelo `User`:
  - `email`
  - `must_change_password`
  - `last_login_at`
  - `password_changed_at`
  - `failed_login_attempts`
  - `locked_until`
  - `is_active`
- Se centraliza la protección de rutas con permisos granulares usando `require_permission("modulo.accion")`.
- Se valida el rol activo en cada solicitud autenticada.
- Se conserva la creación inicial de usuario administrador desde variables de entorno:
  - `ADMIN_USERNAME`
  - `ADMIN_PASSWORD`
  - `ADMIN_FULL_NAME`
- Si el administrador inicial se crea desde el seed, se marca `must_change_password=True`.
- Se extiende la auditoría para registrar acciones críticas y mantener logs inmutables.

## 2. Roles y permisos definidos

### Roles oficiales V1.0

- Administrador
- Barbero
- Cajero
- Consultor

### Permisos por módulo

- seguridad.ver, seguridad.crear, seguridad.editar, seguridad.eliminar
- barberos.ver, barberos.crear, barberos.editar, barberos.eliminar
- clientes.ver, clientes.crear, clientes.editar, clientes.eliminar
- servicios.ver, servicios.crear, servicios.editar, servicios.eliminar
- comandas.ver, comandas.crear, comandas.editar, comandas.eliminar, comandas.cerrar
- inventario.ver, inventario.crear, inventario.editar, inventario.eliminar, inventario.ajustar
- cuentas_por_cobrar.ver, cuentas_por_cobrar.crear, cuentas_por_cobrar.editar, cuentas_por_cobrar.abonar
- alertas.ver
- caja.ver, caja.abrir, caja.cerrar, caja.movimiento
- reportes.ver, reportes.exportar
- dashboard.ver
- auditoria.ver

### Asignación por rol

- Administrador: acceso total a todos los permisos.
- Cajero: caja, pagos, cierres, comandas, clientes, cuentas por cobrar, alertas, reportes y dashboard.
- Barbero: dashboard, clientes básicos, servicios, comandas operativas, inventario en lectura y alertas.
- Consultor: solo lectura de dashboard, reportes, clientes, barberos, servicios, inventario, cuentas por cobrar, alertas y caja.

## 3. Entidades del MER implementadas

- roles
- permissions
- role_permissions
- users
- audit_logs
- barbers
- clients
- services
- service_consumables
- products
- inventory_movements
- orders
- order_items
- payments
- cash_registers
- cash_movements
- accounts_receivable
- accounts_receivable_payments
- alerts
- system_config

## 4. Relaciones principales

- `users.role_id -> roles.id`
- `role_permissions.role_id -> roles.id`
- `role_permissions.permission_id -> permissions.id`
- `audit_logs.user_id -> users.id`
- `barbers.user_id -> users.id`
- `orders.client_id -> clients.id`
- `orders.barber_id -> barbers.id`
- `orders.created_by_user_id -> users.id`
- `order_items.order_id -> orders.id`
- `order_items.service_id -> services.id`
- `order_items.product_id -> products.id`
- `inventory_movements.product_id -> products.id`
- `inventory_movements.created_by_user_id -> users.id`
- `service_consumables.service_id -> services.id`
- `service_consumables.product_id -> products.id`
- `payments.order_id -> orders.id`
- `payments.user_id -> users.id`
- `payments.cash_register_id -> cash_registers.id`
- `cash_movements.cash_register_id -> cash_registers.id`
- `cash_movements.user_id -> users.id`
- `accounts_receivable.client_id -> clients.id`
- `accounts_receivable.order_id -> orders.id`
- `accounts_receivable.created_by_user_id -> users.id`
- `accounts_receivable_payments.accounts_receivable_id -> accounts_receivable.id`
- `accounts_receivable_payments.user_id -> users.id`

## 5. Reglas de negocio aplicadas

- La comanda pertenece a un cliente y queda vinculada con barbero/usuario responsable.
- La comanda puede contener servicios y productos con un `order_items` mixto.
- El cierre de comanda deberá construirse como una operación atómica que abarque comanda, inventario, caja, barbero y auditoría.
- Si la comanda queda fiada se debe generar una cuenta por cobrar automática.
- Si se registra un pago parcial, debe quedar saldo pendiente y abono histórico.
- Los productos vendidos descuentan inventario.
- Los servicios con consumibles internos tienen vínculo con productos consumibles.
- Los ajustes manuales de inventario exigen motivo obligatorio.
- Los registros de caja y cierre de caja se mantienen con datos históricos y control de inmutabilidad.
- Los usuarios, barberos, servicios y productos se mantienen con baja lógica (`is_active`) cuando tienen historial.

## 6. Cambios realizados

- Añadido `email`, `must_change_password`, `last_login_at`, `password_changed_at` a `User`.
- Añadido bloqueo de login tras 5 intentos fallidos y bloqueo temporal con auditoría.
- Implementado `require_permission("modulo.accion")` para permisos granulares.
- Protegidas rutas de seguridad, barberos, clientes, servicios, inventario y comandas por permisos específicos.
- Extendido el modelo de `Order` con `payment_status`, `amount_paid` e `is_fiado`.
- Corregido `order_items.product_id` a `ForeignKey("products.id")`.
- Agregados los modelos faltantes para pagos, caja, movimientos de caja, cuentas por cobrar, abonos, alertas y configuración del sistema.
- Actualizado `backend/app/create_tables.py` para incluir las nuevas tablas.
- Creado el entorno Alembic en `backend/alembic` y estampado el estado actual como baseline.
- Documentado el plan de seguridad y el MER en este archivo.

## 7. Pendientes para V2.0 nube

- Implementar migraciones Alembic completas para cambios de esquema.
- Añadir endpoints y servicios de caja, pagos y cuentas por cobrar.
- Añadir auditoría detallada de transacciones financieras y cierre de caja.
- Construir endpoints de reportes y dashboard basados en datos reales.
- Añadir mecanismos de sincronización segura y backup local/cloud.
- Migrar el almacenamiento de secretos a un gestor seguro en nube.
- Implementar seguimiento de sesión y política MFA para acceso remoto.
