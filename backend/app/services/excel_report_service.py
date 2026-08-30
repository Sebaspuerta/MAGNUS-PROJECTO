"""
Reporte de Control de Inventario y Contaduria para MAGNUS BARBER SHOP.

Genera un Excel con 8 hojas de cifras YA CALCULADAS (nunca una tabla cruda de
la base de datos): Panorama General, Estado de Resultados, Inventario,
Ventas, Comisiones por Barbero, Cuentas por Cobrar, Movimientos de
Inventario y Cierres de Caja.

Regla no negociable: el costo de cada linea de venta se consulta en Python
directo del producto (por product_id, nunca por nombre) y se escribe como
numero fijo — nunca una formula INDEX/MATCH buscando el producto en otra
hoja. Si el producto se renombra o se elimina despues, esa formula fallaria
en silencio y el costo se veria como $0, inflando la utilidad sin que nadie
lo note.

Las formulas SI se usan para agregados (SUM/SUMIFS/COUNTIFS) que referencian
otras hojas de este mismo reporte, porque esas hojas se generan frescas en
la misma corrida — no hay riesgo de que el texto que buscan (barbero, tipo,
estado) haya quedado desactualizado.
"""

from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill, Side, Border
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy.orm import Session

from app.config import settings
from app.models.accounts_receivable import AccountsReceivable
from app.models.barber import Barber
from app.models.cash_movement import CashMovement  # noqa: F401 - referenciado por CashRegister.movements
from app.models.cash_register import CashRegister
from app.models.category import Category
from app.models.client import Client
from app.models.inventory import InventoryMovement, Product
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.accounts_receivable import AccountsReceivablePayment
from app.models.security import User
from app.models.service import Service
from app.models.service_consumable import ServiceConsumable  # noqa: F401 - referenciado por Product/Service
from app.services.reports_service import _resolve_range
from app.utils.deleted_labels import DELETED_PRODUCT_SUFFIX, barber_label, product_label, service_label

_BUSINESS_TZ = ZoneInfo(settings.business_tz)


# ---------------------------------------------------------------------------
# IDENTIDAD VISUAL — marca MAGNUS BARBER SHOP
# ---------------------------------------------------------------------------
BLACK = "141414"
RED = "D92526"
BLUE = "2B22E1"
WHITE = "FFFFFF"
GRAY_TEXT = "6B7280"
LIGHT_FILL = "F5F5F5"
DARK_TEXT = "1A1A1A"

GREEN_FILL = PatternFill(start_color="D9F2D9", end_color="D9F2D9", fill_type="solid")
GREEN_FONT = Font(name="Arial", color="1F7A1F", bold=True)
AMBER_FILL = PatternFill(start_color="FCEBC9", end_color="FCEBC9", fill_type="solid")
AMBER_FONT = Font(name="Arial", color="8A5A00", bold=True)
RED_FILL = PatternFill(start_color="F7D3D3", end_color="F7D3D3", fill_type="solid")
RED_FONT = Font(name="Arial", color="A11212", bold=True)

HEADER_FONT = Font(name="Arial", bold=True, color=WHITE, size=10)
HEADER_FILL = PatternFill(start_color=BLACK, end_color=BLACK, fill_type="solid")
TITLE_FONT = Font(name="Arial", bold=True, color=DARK_TEXT, size=17)
SUBTITLE_FONT = Font(name="Arial", italic=True, color=GRAY_TEXT, size=10)
SECTION_FONT = Font(name="Arial", bold=True, color=DARK_TEXT, size=12)
CELL_BORDER = Border(bottom=Side(style="thin", color="E5E5E5"))

CURRENCY_FMT = '"$" #,##0'
PERCENT_FMT = '0.0%'
INT_FMT = '#,##0'
DATE_FMT = 'dd/mm/yyyy'
DATETIME_FMT = 'dd/mm/yyyy hh:mm'

BANNER_TITLE_ROW = 1
BANNER_SUBTITLE_ROW = 2
BANNER_ACCENT_ROW = 3
HEADER_ROW = 5
DATA_START_ROW = 6

FOOTER_COMPANY = "Desarrollado por AVANZATECH S.A.S"
FOOTER_TAGLINE = "Soluciones Tecnologicas que Impulsan tu Negocio"
FOOTER_SOFTWARE = "Software MAGNUS BARBER SYSTEM"


# ---------------------------------------------------------------------------
# Utilidades generales
# ---------------------------------------------------------------------------
def _find_asset(*filenames: str) -> Path | None:
    here = Path(__file__).resolve()
    for parents_up in (3, 2):
        base = here.parents[parents_up] / "frontend" / "img"
        for filename in filenames:
            candidate = base / filename
            if candidate.is_file():
                return candidate
    return None


def _to_local(dt: datetime | None) -> datetime | None:
    """UTC naive -> hora Colombia, tambien naive (Excel no acepta tz-aware)."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc).astimezone(_BUSINESS_TZ).replace(tzinfo=None)


def _sheet_ref(title: str) -> str:
    return f"'{title}'" if " " in title else title


def _col_range(sheet_title: str, col_letter: str, start_row: int, end_row: int) -> str:
    ref = _sheet_ref(sheet_title)
    return f"{ref}!{col_letter}{start_row}:{col_letter}{end_row}"


def _cell_ref(sheet_title: str, col_letter: str, row: int) -> str:
    return f"{_sheet_ref(sheet_title)}!{col_letter}{row}"


def _autofit_columns(ws: Worksheet, num_columns: int, max_width: int = 38) -> None:
    for col_idx in range(1, num_columns + 1):
        letter = get_column_letter(col_idx)
        longest = 0
        for cell in ws[letter]:
            if cell.value is not None:
                longest = max(longest, len(str(cell.value)))
        ws.column_dimensions[letter].width = min(max(longest + 2, 11), max_width)


def _finalize_sheet(ws: Worksheet, num_cols: int, header_row: int, last_row: int) -> None:
    ws.sheet_view.showGridLines = False
    if last_row >= header_row:
        ws.freeze_panes = ws.cell(row=header_row + 1, column=1).coordinate
        ws.auto_filter.ref = f"A{header_row}:{get_column_letter(num_cols)}{last_row}"
    ws.page_setup.orientation = "landscape"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    _autofit_columns(ws, num_cols)
    # El logo esta anclado en A1: si la columna A queda muy angosta por el
    # autofit (ej. una categoria corta), la imagen se ve apretada/recortada.
    current_a_width = ws.column_dimensions["A"].width or 0
    ws.column_dimensions["A"].width = max(current_a_width, 14)


def _write_banner(
    ws: Worksheet,
    title: str,
    subtitle: str,
    num_cols: int,
    logo_path: Path | None,
) -> None:
    last_letter = get_column_letter(num_cols)
    title_col = "C" if logo_path is not None else "A"

    ws.row_dimensions[BANNER_TITLE_ROW].height = 30
    ws.row_dimensions[BANNER_SUBTITLE_ROW].height = 16
    ws.row_dimensions[BANNER_ACCENT_ROW].height = 4
    ws.row_dimensions[4].height = 8

    if logo_path is not None:
        try:
            img = XLImage(str(logo_path))
            img.height = 42
            img.width = 126
            ws.add_image(img, "A1")
        except Exception:
            pass

    ws.merge_cells(f"{title_col}{BANNER_TITLE_ROW}:{last_letter}{BANNER_TITLE_ROW}")
    title_cell = ws[f"{title_col}{BANNER_TITLE_ROW}"]
    title_cell.value = title
    title_cell.font = TITLE_FONT
    title_cell.alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells(f"{title_col}{BANNER_SUBTITLE_ROW}:{last_letter}{BANNER_SUBTITLE_ROW}")
    subtitle_cell = ws[f"{title_col}{BANNER_SUBTITLE_ROW}"]
    subtitle_cell.value = subtitle
    subtitle_cell.font = SUBTITLE_FONT
    subtitle_cell.alignment = Alignment(horizontal="left", vertical="center")

    mid_col = 1 + num_cols // 2
    mid_letter = get_column_letter(mid_col)
    next_letter = get_column_letter(mid_col + 1) if mid_col + 1 <= num_cols else last_letter
    ws.merge_cells(f"A{BANNER_ACCENT_ROW}:{mid_letter}{BANNER_ACCENT_ROW}")
    ws[f"A{BANNER_ACCENT_ROW}"].fill = PatternFill(start_color=BLUE, end_color=BLUE, fill_type="solid")
    if mid_col + 1 <= num_cols:
        ws.merge_cells(f"{next_letter}{BANNER_ACCENT_ROW}:{last_letter}{BANNER_ACCENT_ROW}")
        ws[f"{next_letter}{BANNER_ACCENT_ROW}"].fill = PatternFill(start_color=RED, end_color=RED, fill_type="solid")


def _write_footer(ws: Worksheet, content_last_row: int, num_cols: int, footer_logo_path: Path | None) -> None:
    # 4 filas en blanco antes del pie para que nunca se mezcle con las tablas.
    footer_row = content_last_row + 5
    last_letter = get_column_letter(num_cols)
    text_col = "C" if footer_logo_path is not None else "A"

    if footer_logo_path is not None:
        try:
            img = XLImage(str(footer_logo_path))
            img.height = 34
            img.width = 34
            ws.add_image(img, f"A{footer_row}")
        except Exception:
            pass

    ws.merge_cells(f"{text_col}{footer_row}:{last_letter}{footer_row}")
    company_cell = ws[f"{text_col}{footer_row}"]
    company_cell.value = FOOTER_COMPANY
    company_cell.font = Font(name="Arial", bold=True, size=10, color=DARK_TEXT)
    company_cell.alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells(f"{text_col}{footer_row + 1}:{last_letter}{footer_row + 1}")
    tagline_cell = ws[f"{text_col}{footer_row + 1}"]
    tagline_cell.value = f"{FOOTER_TAGLINE}  -  (c) {datetime.now().year}  -  {FOOTER_SOFTWARE}"
    tagline_cell.font = Font(name="Arial", size=8, color=GRAY_TEXT)
    tagline_cell.alignment = Alignment(horizontal="left", vertical="center")

    return footer_row + 1


def _write_table_header(ws: Worksheet, headers: list[str], row: int = HEADER_ROW) -> None:
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 26


def _apply_status_conditional_format(ws: Worksheet, col_letter: str, first_row: int, last_row: int) -> None:
    rng = f"{col_letter}{first_row}:{col_letter}{last_row}"
    ws.conditional_formatting.add(
        rng,
        FormulaRule(formula=[f'{col_letter}{first_row}="Disponible"'], fill=GREEN_FILL, font=GREEN_FONT),
    )
    ws.conditional_formatting.add(
        rng,
        FormulaRule(formula=[f'{col_letter}{first_row}="Vigente"'], fill=GREEN_FILL, font=GREEN_FONT),
    )
    ws.conditional_formatting.add(
        rng,
        FormulaRule(formula=[f'{col_letter}{first_row}="Stock Bajo"'], fill=AMBER_FILL, font=AMBER_FONT),
    )
    ws.conditional_formatting.add(
        rng,
        FormulaRule(formula=[f'{col_letter}{first_row}="Atrasado"'], fill=AMBER_FILL, font=AMBER_FONT),
    )
    ws.conditional_formatting.add(
        rng,
        FormulaRule(formula=[f'{col_letter}{first_row}="Agotado"'], fill=RED_FILL, font=RED_FONT),
    )
    ws.conditional_formatting.add(
        rng,
        FormulaRule(formula=[f'{col_letter}{first_row}="Vencido"'], fill=RED_FILL, font=RED_FONT),
    )


def _write_kpi_card(
    ws: Worksheet,
    row: int,
    col_start: int,
    col_span: int,
    label: str,
    value,
    accent_hex: str,
    number_format: str | None = None,
) -> None:
    """Tarjeta KPI: columna dedicada con relleno de acento (nunca borde de
    celda combinada, para que no se rompa en Google Sheets)."""
    accent_col = col_start
    text_start = col_start + 1
    text_end = col_start + col_span - 1

    for r in range(row, row + 3):
        ws.cell(row=r, column=accent_col).fill = PatternFill(start_color=accent_hex, end_color=accent_hex, fill_type="solid")
        for c in range(text_start, text_end + 1):
            ws.cell(row=r, column=c).fill = PatternFill(start_color=LIGHT_FILL, end_color=LIGHT_FILL, fill_type="solid")

    ws.merge_cells(start_row=row, start_column=text_start, end_row=row, end_column=text_end)
    label_cell = ws.cell(row=row, column=text_start, value=label.upper())
    label_cell.font = Font(name="Arial", size=8.5, bold=True, color=GRAY_TEXT)
    label_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)

    ws.merge_cells(start_row=row + 1, start_column=text_start, end_row=row + 1, end_column=text_end)
    value_cell = ws.cell(row=row + 1, column=text_start, value=value)
    value_cell.font = Font(name="Arial", size=15, bold=True, color=DARK_TEXT)
    value_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    if number_format:
        value_cell.number_format = number_format

    ws.row_dimensions[row].height = 16
    ws.row_dimensions[row + 1].height = 22
    ws.row_dimensions[row + 2].height = 8


# ---------------------------------------------------------------------------
# Estado de stock (misma logica que alert_service / dashboard_service)
# ---------------------------------------------------------------------------
def _stock_status_formula(stock_col: str, min_col: str, row: int) -> str:
    return (
        f'=IF({stock_col}{row}<=0,"Agotado",'
        f'IF(AND({min_col}{row}<>"",{stock_col}{row}<={min_col}{row}),"Stock Bajo","Disponible"))'
    )


# ---------------------------------------------------------------------------
# HOJA: Inventario
# ---------------------------------------------------------------------------
def _build_inventario_sheet(wb: Workbook, db: Session, logo_path, footer_logo_path) -> dict:
    ws = wb.create_sheet(title="Inventario")
    headers = [
        "Categoria", "Producto", "Costo Unitario", "Precio Venta",
        "Margen Unitario", "Margen %", "Stock Actual", "Stock Minimo",
        "Valor de Stock", "Estado",
    ]
    num_cols = len(headers)

    _write_banner(ws, "INVENTARIO", f"Catalogo de productos activos - Corte al {datetime.now(_BUSINESS_TZ).strftime('%d/%m/%Y %H:%M')}", num_cols, logo_path)
    _write_table_header(ws, headers)

    products = (
        db.query(Product)
        .filter(Product.is_deleted.is_(False), Product.is_active.is_(True))
        .order_by(Product.name.asc())
        .all()
    )
    categories = {c.id: c for c in db.query(Category).all()}

    row = DATA_START_ROW
    for p in products:
        cat = categories.get(p.category_id)
        cat_name = cat.name if cat else "Sin categoria"
        cost = float(p.purchase_cost or 0)
        price = float(p.sale_price or 0)

        ws.cell(row=row, column=1, value=cat_name)
        ws.cell(row=row, column=2, value=p.name)
        c3 = ws.cell(row=row, column=3, value=cost); c3.number_format = CURRENCY_FMT
        c4 = ws.cell(row=row, column=4, value=price); c4.number_format = CURRENCY_FMT
        c5 = ws.cell(row=row, column=5, value=f"=D{row}-C{row}"); c5.number_format = CURRENCY_FMT
        c6 = ws.cell(row=row, column=6, value=f'=IF(D{row}=0,0,E{row}/D{row})'); c6.number_format = PERCENT_FMT
        c7 = ws.cell(row=row, column=7, value=int(p.current_stock or 0)); c7.number_format = INT_FMT
        min_stock = p.minimum_stock if p.minimum_stock is not None else ""
        c8 = ws.cell(row=row, column=8, value=min_stock)
        if min_stock != "":
            c8.number_format = INT_FMT
        c9 = ws.cell(row=row, column=9, value=f"=C{row}*G{row}"); c9.number_format = CURRENCY_FMT
        ws.cell(row=row, column=10, value=_stock_status_formula("G", "H", row))
        row += 1

    last_row = row - 1 if products else DATA_START_ROW - 1
    if products:
        for r in range(DATA_START_ROW, last_row + 1):
            for c in range(1, num_cols + 1):
                ws.cell(row=r, column=c).border = CELL_BORDER
        _apply_status_conditional_format(ws, "J", DATA_START_ROW, last_row)

    footer_end = _write_footer(ws, max(last_row, DATA_START_ROW), num_cols, footer_logo_path)
    _finalize_sheet(ws, num_cols, HEADER_ROW, last_row if products else DATA_START_ROW)

    return {
        "sheet": "Inventario",
        "first_row": DATA_START_ROW,
        "last_row": last_row if products else DATA_START_ROW,
        "has_data": bool(products),
        "value_col": "I",
        "status_col": "J",
    }


# ---------------------------------------------------------------------------
# HOJA: Ventas
# ---------------------------------------------------------------------------
PAYMENT_STATUS_LABELS = {
    "pendiente": "Pendiente",
    "pagado": "Pagado",
    "parcial": "Parcial",
    "fiado": "Fiado",
}


def _build_ventas_sheet(
    wb: Workbook, db: Session, start_dt: datetime, end_dt: datetime, logo_path, footer_logo_path
) -> dict:
    ws = wb.create_sheet(title="Ventas")
    headers = [
        "Fecha", "N Comanda", "Cliente", "Barbero", "Tipo", "Producto/Servicio",
        "Cantidad", "Precio Unitario", "Total Linea", "Costo Estimado",
        "Utilidad Linea", "Estado de Pago", "Metodo de Pago",
    ]
    num_cols = len(headers)

    period_txt = f"Periodo: {start_dt.date().isoformat()} a {(end_dt - timedelta(seconds=1)).date().isoformat()}"
    _write_banner(ws, "VENTAS", f"Comandas cerradas del periodo  -  {period_txt}", num_cols, logo_path)
    _write_table_header(ws, headers)

    rows_qs = (
        db.query(OrderItem, Order)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(Order.status == "cerrada", Order.closed_at >= start_dt, Order.closed_at < end_dt)
        .order_by(Order.closed_at.asc(), Order.id.asc())
        .all()
    )

    barbers = {b.id: b for b in db.query(Barber).all()}
    clients = {c.id: c for c in db.query(Client).all()}
    products = {p.id: p for p in db.query(Product).all()}
    services = {s.id: s for s in db.query(Service).all()}
    payments_by_order: dict[int, str] = {}
    for order_id, method in db.query(Payment.order_id, Payment.payment_method).all():
        payments_by_order.setdefault(order_id, method)

    row = DATA_START_ROW
    distinct_order_ids: set[int] = set()
    for item, order in rows_qs:
        distinct_order_ids.add(order.id)
        barber = barbers.get(order.barber_id) if order.barber_id else None
        client = clients.get(order.client_id) if order.client_id else None

        if item.item_type == "producto":
            tipo_label = "Producto"
            product = products.get(item.product_id) if item.product_id else None
            name = product_label(product.name, product) if product else (item.description or "Producto eliminado")
            # Costo real consultado por product_id directo de la BD, NUNCA por
            # nombre — se escribe como numero fijo, jamas como formula.
            unit_cost = float(product.purchase_cost or 0) if product else 0.0
            cost = unit_cost * int(item.quantity or 0)
        elif item.item_type == "servicio":
            tipo_label = "Servicio"
            service = services.get(item.service_id) if item.service_id else None
            name = service_label(service.name, service) if service else (item.description or "Servicio eliminado")
            # El costo de un servicio ya se contabiliza aparte, como comision
            # del barbero (ver hoja Comisiones por Barbero).
            cost = 0.0
        else:
            tipo_label = item.item_type
            name = item.description or "Item"
            cost = 0.0

        local_dt = _to_local(order.closed_at)

        c1 = ws.cell(row=row, column=1, value=local_dt); c1.number_format = DATETIME_FMT
        ws.cell(row=row, column=2, value=order.id)
        ws.cell(row=row, column=3, value=client.full_name if client else "Sin cliente")
        ws.cell(row=row, column=4, value=barber_label(barber.full_name, barber) if barber else "Sin barbero")
        ws.cell(row=row, column=5, value=tipo_label)
        ws.cell(row=row, column=6, value=name)
        c7 = ws.cell(row=row, column=7, value=int(item.quantity or 0)); c7.number_format = INT_FMT
        c8 = ws.cell(row=row, column=8, value=float(item.unit_price or 0)); c8.number_format = CURRENCY_FMT
        c9 = ws.cell(row=row, column=9, value=float(item.total_price or 0)); c9.number_format = CURRENCY_FMT
        c10 = ws.cell(row=row, column=10, value=cost); c10.number_format = CURRENCY_FMT
        c11 = ws.cell(row=row, column=11, value=f"=I{row}-J{row}"); c11.number_format = CURRENCY_FMT
        ws.cell(row=row, column=12, value=PAYMENT_STATUS_LABELS.get(order.payment_status, order.payment_status or "-"))
        method = payments_by_order.get(order.id)
        ws.cell(row=row, column=13, value=(method.capitalize() if method else ("Fiado" if order.is_fiado else "-")))
        row += 1

    last_row = row - 1 if rows_qs else DATA_START_ROW - 1
    if rows_qs:
        for r in range(DATA_START_ROW, last_row + 1):
            for c in range(1, num_cols + 1):
                ws.cell(row=r, column=c).border = CELL_BORDER

    footer_end = _write_footer(ws, max(last_row, DATA_START_ROW), num_cols, footer_logo_path)
    _finalize_sheet(ws, num_cols, HEADER_ROW, last_row if rows_qs else DATA_START_ROW)

    return {
        "sheet": "Ventas",
        "first_row": DATA_START_ROW,
        "last_row": last_row if rows_qs else DATA_START_ROW,
        "has_data": bool(rows_qs),
        "total_col": "I",
        "cost_col": "J",
        "barbero_col": "D",
        "tipo_col": "E",
        "estado_pago_col": "L",
        "order_count": len(distinct_order_ids),
    }


# ---------------------------------------------------------------------------
# HOJA: Comisiones por Barbero (solo sobre servicios)
# ---------------------------------------------------------------------------
def _build_comisiones_sheet(
    wb: Workbook, db: Session, ventas_info: dict, start_dt: datetime, end_dt: datetime, logo_path, footer_logo_path
) -> dict:
    ws = wb.create_sheet(title="Comisiones por Barbero")
    headers = [
        "Barbero", "Tipo de Comision", "Valor Configurado",
        "Servicios Vendidos", "Comandas con Servicio",
        "Total Vendido en Servicios", "Comision a Pagar",
    ]
    num_cols = len(headers)

    period_txt = f"Periodo: {start_dt.date().isoformat()} a {(end_dt - timedelta(seconds=1)).date().isoformat()}"
    _write_banner(ws, "COMISIONES POR BARBERO", f"Solo sobre servicios (no sobre venta de productos)  -  {period_txt}", num_cols, logo_path)
    _write_table_header(ws, headers)

    # Barberos con al menos una linea de SERVICIO cerrada en el periodo.
    service_rows = (
        db.query(OrderItem, Order)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            Order.status == "cerrada",
            Order.closed_at >= start_dt,
            Order.closed_at < end_dt,
            OrderItem.item_type == "servicio",
        )
        .all()
    )

    barbers = {b.id: b for b in db.query(Barber).all()}
    by_barber: dict[int, dict] = {}
    for item, order in service_rows:
        if order.barber_id is None:
            continue
        bucket = by_barber.setdefault(order.barber_id, {"orders": set(), "count": 0})
        bucket["orders"].add(order.id)
        bucket["count"] += 1

    barber_ids_sorted = sorted(
        by_barber.keys(),
        key=lambda bid: -len(by_barber[bid]["orders"]),
    )

    ventas_sheet = ventas_info["sheet"]
    total_col = ventas_info["total_col"]
    barbero_col = ventas_info["barbero_col"]
    tipo_col = ventas_info["tipo_col"]
    v_first = ventas_info["first_row"]
    v_last = ventas_info["last_row"]

    row = DATA_START_ROW
    for barber_id in barber_ids_sorted:
        barber = barbers.get(barber_id)
        if barber is None:
            continue
        name = barber_label(barber.full_name, barber)
        commission_type = (barber.commission_type or "").strip().lower()
        is_percent = commission_type in ("porcentaje", "percent", "%")
        commission_value = float(barber.commission_value or 0)
        comandas_con_servicio = len(by_barber[barber_id]["orders"])

        ws.cell(row=row, column=1, value=name)
        ws.cell(row=row, column=2, value="Porcentaje" if is_percent else "Fijo")
        c3 = ws.cell(row=row, column=3, value=commission_value)
        c3.number_format = PERCENT_FMT if is_percent else CURRENCY_FMT
        if is_percent:
            # commission_value se guarda como numero entero (ej. 10 = 10%),
            # asi que para mostrarlo con formato % hay que dividir entre 100.
            c3.value = commission_value / 100.0

        d_formula = f'=COUNTIFS({_col_range(ventas_sheet, barbero_col, v_first, v_last)},A{row},{_col_range(ventas_sheet, tipo_col, v_first, v_last)},"Servicio")'
        ws.cell(row=row, column=4, value=d_formula)

        ws.cell(row=row, column=5, value=comandas_con_servicio)

        f_formula = f'=SUMIFS({_col_range(ventas_sheet, total_col, v_first, v_last)},{_col_range(ventas_sheet, barbero_col, v_first, v_last)},A{row},{_col_range(ventas_sheet, tipo_col, v_first, v_last)},"Servicio")'
        f_cell = ws.cell(row=row, column=6, value=f_formula)
        f_cell.number_format = CURRENCY_FMT

        g_formula = f'=IF(B{row}="Porcentaje",F{row}*C{row},E{row}*C{row})'
        g_cell = ws.cell(row=row, column=7, value=g_formula)
        g_cell.number_format = CURRENCY_FMT

        row += 1

    last_row = row - 1 if barber_ids_sorted else DATA_START_ROW - 1
    if barber_ids_sorted:
        for r in range(DATA_START_ROW, last_row + 1):
            for c in range(1, num_cols + 1):
                ws.cell(row=r, column=c).border = CELL_BORDER

    footer_end = _write_footer(ws, max(last_row, DATA_START_ROW), num_cols, footer_logo_path)
    _finalize_sheet(ws, num_cols, HEADER_ROW, last_row if barber_ids_sorted else DATA_START_ROW)

    return {
        "sheet": "Comisiones por Barbero",
        "first_row": DATA_START_ROW,
        "last_row": last_row if barber_ids_sorted else DATA_START_ROW,
        "has_data": bool(barber_ids_sorted),
        "name_col": "A",
        "total_col": "F",
        "commission_col": "G",
    }


# ---------------------------------------------------------------------------
# HOJA: Cuentas por Cobrar (foto del momento actual, con antiguedad)
# ---------------------------------------------------------------------------
def _build_cuentas_por_cobrar_sheet(wb: Workbook, db: Session, logo_path, footer_logo_path) -> dict:
    ws = wb.create_sheet(title="Cuentas por Cobrar")
    headers = [
        "Cliente", "N Comanda Origen", "Fecha Origen", "Monto Total",
        "Abonado", "Saldo", "Dias Transcurridos", "Estado",
    ]
    num_cols = len(headers)

    _write_banner(ws, "CUENTAS POR COBRAR", f"Fiados vigentes - Corte al {datetime.now(_BUSINESS_TZ).strftime('%d/%m/%Y %H:%M')}", num_cols, logo_path)
    _write_table_header(ws, headers)

    ar_rows = (
        db.query(AccountsReceivable)
        .filter(AccountsReceivable.is_active.is_(True), AccountsReceivable.balance > 0)
        .order_by(AccountsReceivable.balance.desc())
        .all()
    )
    clients = {c.id: c for c in db.query(Client).all()}

    row = DATA_START_ROW
    for ar in ar_rows:
        client = clients.get(ar.client_id)
        origin_dt = _to_local(ar.created_at) if ar.created_at else None

        ws.cell(row=row, column=1, value=client.full_name if client else "Cliente eliminado")
        ws.cell(row=row, column=2, value=ar.order_id if ar.order_id else "-")
        c3 = ws.cell(row=row, column=3, value=origin_dt.date() if origin_dt else None)
        c3.number_format = DATE_FMT
        c4 = ws.cell(row=row, column=4, value=float(ar.total_amount or 0)); c4.number_format = CURRENCY_FMT
        c5 = ws.cell(row=row, column=5, value=float(ar.paid_amount or 0)); c5.number_format = CURRENCY_FMT
        c6 = ws.cell(row=row, column=6, value=float(ar.balance or 0)); c6.number_format = CURRENCY_FMT
        c7 = ws.cell(row=row, column=7, value=f'=IF(C{row}="","",TODAY()-C{row})')
        c7.number_format = INT_FMT
        c8 = ws.cell(
            row=row, column=8,
            value=f'=IF(C{row}="","Sin fecha",IF(G{row}<=30,"Vigente",IF(G{row}<=60,"Atrasado","Vencido")))',
        )
        row += 1

    last_row = row - 1 if ar_rows else DATA_START_ROW - 1
    if ar_rows:
        for r in range(DATA_START_ROW, last_row + 1):
            for c in range(1, num_cols + 1):
                ws.cell(row=r, column=c).border = CELL_BORDER
        _apply_status_conditional_format(ws, "H", DATA_START_ROW, last_row)

    footer_end = _write_footer(ws, max(last_row, DATA_START_ROW), num_cols, footer_logo_path)
    _finalize_sheet(ws, num_cols, HEADER_ROW, last_row if ar_rows else DATA_START_ROW)

    return {
        "sheet": "Cuentas por Cobrar",
        "first_row": DATA_START_ROW,
        "last_row": last_row if ar_rows else DATA_START_ROW,
        "has_data": bool(ar_rows),
        "balance_col": "F",
    }


# ---------------------------------------------------------------------------
# HOJA: Movimientos de Inventario (historial completo del periodo)
# ---------------------------------------------------------------------------
MOVEMENT_TYPE_LABELS = {
    "entrada": "Entrada",
    "salida_venta": "Salida por venta",
    "salida_servicio": "Salida por consumo interno",
    "ajuste": "Ajuste",
}


def _build_movimientos_sheet(
    wb: Workbook, db: Session, start_dt: datetime, end_dt: datetime, logo_path, footer_logo_path
) -> dict:
    ws = wb.create_sheet(title="Movimientos de Inventario")
    headers = [
        "Fecha", "Producto", "Tipo de Movimiento", "Cantidad",
        "Stock Anterior", "Stock Nuevo", "Motivo", "Usuario",
    ]
    num_cols = len(headers)

    period_txt = f"Periodo: {start_dt.date().isoformat()} a {(end_dt - timedelta(seconds=1)).date().isoformat()}"
    _write_banner(ws, "MOVIMIENTOS DE INVENTARIO", f"Historial completo del periodo (entradas, salidas y ajustes)  -  {period_txt}", num_cols, logo_path)
    _write_table_header(ws, headers)

    movements = (
        db.query(InventoryMovement)
        .filter(InventoryMovement.created_at >= start_dt, InventoryMovement.created_at < end_dt)
        .order_by(InventoryMovement.created_at.asc())
        .all()
    )
    products = {p.id: p for p in db.query(Product).all()}
    users = {u.id: u for u in db.query(User).all()}

    row = DATA_START_ROW
    for mv in movements:
        product = products.get(mv.product_id)
        user = users.get(mv.created_by_user_id)
        local_dt = _to_local(mv.created_at)

        c1 = ws.cell(row=row, column=1, value=local_dt); c1.number_format = DATETIME_FMT
        ws.cell(row=row, column=2, value=product_label(product.name, product) if product else "Producto eliminado")
        ws.cell(row=row, column=3, value=MOVEMENT_TYPE_LABELS.get(mv.movement_type, mv.movement_type))
        c4 = ws.cell(row=row, column=4, value=int(mv.quantity or 0)); c4.number_format = INT_FMT
        c5 = ws.cell(row=row, column=5, value=int(mv.previous_stock or 0)); c5.number_format = INT_FMT
        c6 = ws.cell(row=row, column=6, value=int(mv.new_stock or 0)); c6.number_format = INT_FMT
        ws.cell(row=row, column=7, value=mv.reason or "-")
        ws.cell(row=row, column=8, value=user.full_name if user else "-")
        row += 1

    last_row = row - 1 if movements else DATA_START_ROW - 1
    if movements:
        for r in range(DATA_START_ROW, last_row + 1):
            for c in range(1, num_cols + 1):
                ws.cell(row=r, column=c).border = CELL_BORDER

    footer_end = _write_footer(ws, max(last_row, DATA_START_ROW), num_cols, footer_logo_path)
    _finalize_sheet(ws, num_cols, HEADER_ROW, last_row if movements else DATA_START_ROW)

    return {"sheet": "Movimientos de Inventario", "has_data": bool(movements)}


# ---------------------------------------------------------------------------
# HOJA: Cierres de Caja (historial del periodo)
# ---------------------------------------------------------------------------
def _build_cierres_caja_sheet(
    wb: Workbook, db: Session, start_dt: datetime, end_dt: datetime, logo_path, footer_logo_path
) -> dict:
    ws = wb.create_sheet(title="Cierres de Caja")
    headers = [
        "Fecha Apertura", "Fecha Cierre", "Abierta Por", "Cerrada Por",
        "Monto Apertura", "Recibido en Efectivo", "Monto Esperado",
        "Monto Contado", "Diferencia",
    ]
    num_cols = len(headers)

    period_txt = f"Periodo: {start_dt.date().isoformat()} a {(end_dt - timedelta(seconds=1)).date().isoformat()}"
    _write_banner(ws, "CIERRES DE CAJA", f"Historial de cierres del periodo  -  {period_txt}", num_cols, logo_path)
    _write_table_header(ws, headers)

    registers = (
        db.query(CashRegister)
        .filter(CashRegister.is_closed.is_(True), CashRegister.closed_at >= start_dt, CashRegister.closed_at < end_dt)
        .order_by(CashRegister.closed_at.asc())
        .all()
    )
    users = {u.id: u for u in db.query(User).all()}

    row = DATA_START_ROW
    for reg in registers:
        received_orders = (
            db.query(Payment)
            .filter(Payment.cash_register_id == reg.id, Payment.payment_method == "efectivo")
            .with_entities(Payment.amount)
            .all()
        )
        received_ar = (
            db.query(AccountsReceivablePayment)
            .filter(
                AccountsReceivablePayment.cash_register_id == reg.id,
                AccountsReceivablePayment.payment_method == "efectivo",
            )
            .with_entities(AccountsReceivablePayment.amount)
            .all()
        )
        received = sum(float(a[0] or 0) for a in received_orders) + sum(float(a[0] or 0) for a in received_ar)
        opening = float(reg.opening_amount or 0)
        expected = opening + received
        counted = float(reg.closing_amount or 0)

        opened_by = users.get(reg.opened_by_user_id)
        closed_by = users.get(reg.closed_by_user_id) if reg.closed_by_user_id else None

        c1 = ws.cell(row=row, column=1, value=_to_local(reg.opened_at)); c1.number_format = DATETIME_FMT
        c2 = ws.cell(row=row, column=2, value=_to_local(reg.closed_at)); c2.number_format = DATETIME_FMT
        ws.cell(row=row, column=3, value=opened_by.full_name if opened_by else "-")
        ws.cell(row=row, column=4, value=closed_by.full_name if closed_by else "-")
        c5 = ws.cell(row=row, column=5, value=opening); c5.number_format = CURRENCY_FMT
        c6 = ws.cell(row=row, column=6, value=received); c6.number_format = CURRENCY_FMT
        c7 = ws.cell(row=row, column=7, value=f"=E{row}+F{row}"); c7.number_format = CURRENCY_FMT
        c8 = ws.cell(row=row, column=8, value=counted); c8.number_format = CURRENCY_FMT
        c9 = ws.cell(row=row, column=9, value=f"=H{row}-G{row}"); c9.number_format = CURRENCY_FMT
        row += 1

    last_row = row - 1 if registers else DATA_START_ROW - 1
    if registers:
        for r in range(DATA_START_ROW, last_row + 1):
            for c in range(1, num_cols + 1):
                ws.cell(row=r, column=c).border = CELL_BORDER

    footer_end = _write_footer(ws, max(last_row, DATA_START_ROW), num_cols, footer_logo_path)
    _finalize_sheet(ws, num_cols, HEADER_ROW, last_row if registers else DATA_START_ROW)

    return {"sheet": "Cierres de Caja", "has_data": bool(registers)}


# ---------------------------------------------------------------------------
# HOJA: Estado de Resultados
# ---------------------------------------------------------------------------
def _build_estado_resultados_sheet(
    wb: Workbook,
    ventas_info: dict,
    inventario_info: dict,
    start_date: date,
    end_date: date,
    logo_path,
    footer_logo_path,
) -> dict:
    ws = wb.create_sheet(title="Estado de Resultados")
    num_cols = 8
    _write_banner(
        ws, "ESTADO DE RESULTADOS",
        f"Ventas Brutas -> Utilidad Operacional  -  Periodo: {start_date.isoformat()} a {end_date.isoformat()}",
        num_cols, logo_path,
    )

    # Los headers se fusionan sobre su columna + la columna de aire siguiente
    # (C, E, G) para que la caja negra no se quede angosta y el texto no se
    # salga de su propia celda (ej. "% SOBRE VENTAS" no cabe en una sola
    # columna con fuente en negrita).
    for start_col, end_col, label in ((2, 3, "CONCEPTO"), (4, 5, "VALOR"), (6, 7, "% SOBRE VENTAS")):
        ws.merge_cells(start_row=HEADER_ROW, start_column=start_col, end_row=HEADER_ROW, end_column=end_col)
        cell = ws.cell(row=HEADER_ROW, column=start_col, value=label)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="left" if start_col == 2 else "center", vertical="center")
        for c in range(start_col, end_col + 1):
            ws.cell(row=HEADER_ROW, column=c).fill = HEADER_FILL
    ws.row_dimensions[HEADER_ROW].height = 22

    ventas_sheet = ventas_info["sheet"]
    v_first, v_last = ventas_info["first_row"], ventas_info["last_row"]
    total_range = _col_range(ventas_sheet, ventas_info["total_col"], v_first, v_last)
    cost_range = _col_range(ventas_sheet, ventas_info["cost_col"], v_first, v_last)
    estado_pago_range = _col_range(ventas_sheet, ventas_info["estado_pago_col"], v_first, v_last)

    row = DATA_START_ROW

    def _ledger_row(label: str, value_formula, pct_formula, bold: bool = False):
        nonlocal row
        lbl = ws.cell(row=row, column=2, value=label)
        lbl.font = Font(name="Arial", bold=bold, color=DARK_TEXT, size=11)
        val = ws.cell(row=row, column=4, value=value_formula)
        val.number_format = CURRENCY_FMT
        val.font = Font(name="Arial", bold=bold, color=DARK_TEXT, size=11)
        if pct_formula is not None:
            pct = ws.cell(row=row, column=6, value=pct_formula)
            pct.number_format = PERCENT_FMT
        current = row
        row += 1
        return current

    ventas_row = _ledger_row("Ventas Brutas", f"=SUM({total_range})", None, bold=True)
    ws.cell(row=ventas_row, column=6, value=f'=IF(D{ventas_row}=0,0,D{ventas_row}/D{ventas_row})').number_format = PERCENT_FMT

    costo_row = _ledger_row("Costo de Ventas", f"=SUM({cost_range})", f"=IF(D{ventas_row}=0,0,D{row}/D{ventas_row})")
    utilidad_bruta_row = _ledger_row(
        "Utilidad Bruta", f"=D{ventas_row}-D{costo_row}", f"=IF(D{ventas_row}=0,0,D{row}/D{ventas_row})", bold=True
    )

    gastos_row = _ledger_row("Gastos Operativos", 0, f"=IF(D{ventas_row}=0,0,D{row}/D{ventas_row})")
    ws.cell(row=gastos_row, column=4).number_format = CURRENCY_FMT
    nota_gastos_row = row
    ws.merge_cells(start_row=nota_gastos_row, start_column=2, end_row=nota_gastos_row, end_column=6)
    nota_cell = ws.cell(
        row=nota_gastos_row, column=2,
        value="Nota: el sistema aun no registra gastos operativos por separado (arriendo, servicios, nomina, etc.); este valor queda en $0 hasta que exista ese modulo.",
    )
    nota_cell.font = Font(name="Arial", italic=True, size=8.5, color=GRAY_TEXT)
    row += 1

    utilidad_operacional_row = _ledger_row(
        "Utilidad Operacional", f"=D{utilidad_bruta_row}-D{gastos_row}",
        f"=IF(D{ventas_row}=0,0,D{row}/D{ventas_row})", bold=True,
    )

    row += 1  # blank spacer

    credito_row = row
    ws.cell(row=row, column=2, value="% Ventas a Credito (Fiado + Parcial)").font = Font(name="Arial", color=DARK_TEXT, size=11)
    credito_formula = (
        f'=IF(D{ventas_row}=0,0,'
        f'(SUMIF({estado_pago_range},"Fiado",{total_range})+SUMIF({estado_pago_range},"Parcial",{total_range}))'
        f'/D{ventas_row})'
    )
    credito_cell = ws.cell(row=row, column=4, value=credito_formula)
    credito_cell.number_format = PERCENT_FMT
    row += 1

    numero_comandas_row = row
    ws.cell(row=row, column=2, value="Numero de Comandas del Periodo").font = Font(name="Arial", color=DARK_TEXT, size=11)
    # Conteo de comandas distintas: calculado en Python (dato simple y
    # exacto), no una formula fragil de conteo-distinto.
    ws.cell(row=row, column=4, value=ventas_info.get("order_count", 0)).number_format = INT_FMT
    row += 1

    ticket_row = row
    ws.cell(row=row, column=2, value="Ticket Promedio").font = Font(name="Arial", color=DARK_TEXT, size=11)
    ticket_cell = ws.cell(row=row, column=4, value=f'=IF(D{numero_comandas_row}=0,0,D{ventas_row}/D{numero_comandas_row})')
    ticket_cell.number_format = CURRENCY_FMT
    row += 2

    # ---- Rotacion de inventario ----
    ws.cell(row=row, column=2, value="ROTACION DE INVENTARIO (APROXIMADA)").font = SECTION_FONT
    row += 1

    inv_sheet = inventario_info["sheet"]
    inv_value_range = _col_range(inv_sheet, inventario_info["value_col"], inventario_info["first_row"], inventario_info["last_row"])
    inv_valor_row = row
    ws.cell(row=row, column=2, value="Valor Actual de Inventario").font = Font(name="Arial", color=DARK_TEXT, size=11)
    inv_cell = ws.cell(row=row, column=4, value=f"=SUM({inv_value_range})")
    inv_cell.number_format = CURRENCY_FMT
    row += 1

    rotacion_row = row
    ws.cell(row=row, column=2, value="Rotacion de Inventario (veces)").font = Font(name="Arial", color=DARK_TEXT, size=11)
    rotacion_cell = ws.cell(row=row, column=4, value=f'=IF(D{inv_valor_row}=0,0,D{costo_row}/D{inv_valor_row})')
    rotacion_cell.number_format = '0.00"x"'
    row += 1

    dias_periodo = max((end_date - start_date).days + 1, 1)
    dias_rotar_row = row
    ws.cell(row=row, column=2, value="Dias para Rotar (aprox.)").font = Font(name="Arial", color=DARK_TEXT, size=11)
    dias_cell = ws.cell(row=row, column=4, value=f'=IF(D{rotacion_row}=0,0,{dias_periodo}/D{rotacion_row})')
    dias_cell.number_format = '0" dias"'
    row += 1

    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=6)
    rot_nota = ws.cell(
        row=row, column=2,
        value="Nota: la rotacion compara el costo de productos vendidos en el periodo contra el valor de inventario ACTUAL (no el promedio del periodo), y no incluye el consumo interno de productos usados como insumo en servicios. Es una referencia aproximada, no un calculo contable exacto.",
    )
    rot_nota.font = Font(name="Arial", italic=True, size=8.5, color=GRAY_TEXT)
    rot_nota.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[row].height = 28
    last_row = row

    footer_end = _write_footer(ws, last_row, num_cols, footer_logo_path)
    _finalize_sheet(ws, num_cols, HEADER_ROW, last_row)
    ws.column_dimensions["B"].width = 34
    ws.column_dimensions["D"].width = 18
    ws.column_dimensions["F"].width = 16

    return {
        "sheet": "Estado de Resultados",
        "ventas_row": ventas_row,
        "costo_row": costo_row,
        "utilidad_bruta_row": utilidad_bruta_row,
        "utilidad_operacional_row": utilidad_operacional_row,
        "credito_row": credito_row,
        "ticket_row": ticket_row,
        "rotacion_row": rotacion_row,
    }


# ---------------------------------------------------------------------------
# HOJA: Panorama General
# ---------------------------------------------------------------------------
def _build_panorama_sheet(
    ws: Worksheet,
    db: Session,
    estado_resultados_info: dict,
    inventario_info: dict,
    ventas_info: dict,
    comisiones_info: dict,
    ar_info: dict,
    start_date: date,
    end_date: date,
    generated_by: str | None,
    logo_path,
    footer_logo_path,
) -> None:
    num_cols = 17

    _write_banner(
        ws, "MAGNUS BARBER SHOP - PANORAMA GENERAL",
        f"Reporte de control de inventario y contaduria  -  Periodo: {start_date.isoformat()} a {end_date.isoformat()}  -  Generado por: {generated_by or 'Sistema'} el {datetime.now(_BUSINESS_TZ).strftime('%d/%m/%Y %H:%M')}",
        num_cols, logo_path,
    )

    for col_idx in range(1, num_cols + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 9.5

    er = estado_resultados_info["sheet"]
    inv_sheet = inventario_info["sheet"]
    ventas_sheet = ventas_info["sheet"]
    com_sheet = comisiones_info["sheet"]
    ar_sheet = ar_info["sheet"]

    inv_value_range = _col_range(inv_sheet, inventario_info["value_col"], inventario_info["first_row"], inventario_info["last_row"])
    inv_status_range = _col_range(inv_sheet, inventario_info["status_col"], inventario_info["first_row"], inventario_info["last_row"])
    com_total_range = _col_range(com_sheet, comisiones_info["commission_col"], comisiones_info["first_row"], comisiones_info["last_row"])
    ar_balance_range = _col_range(ar_sheet, ar_info["balance_col"], ar_info["first_row"], ar_info["last_row"])

    # Producto mas vendido: literal calculado en Python (evita reintroducir
    # el patron fragil de INDEX/MATCH por nombre que este reporte prohibe
    # para costos; aqui es solo un dato descriptivo, no una cifra de plata).
    top_product_text = _compute_top_product_text(db, start_date, end_date)

    kpis = [
        ("Ventas Brutas del Periodo", f"={_cell_ref(er, 'D', estado_resultados_info['ventas_row'])}", CURRENCY_FMT, BLUE),
        ("Utilidad Bruta del Periodo", f"={_cell_ref(er, 'D', estado_resultados_info['utilidad_bruta_row'])}", CURRENCY_FMT, RED),
        ("Margen Bruto", f"={_cell_ref(er, 'F', estado_resultados_info['utilidad_bruta_row'])}", PERCENT_FMT, BLACK),
        ("Utilidad Operacional", f"={_cell_ref(er, 'D', estado_resultados_info['utilidad_operacional_row'])}", CURRENCY_FMT, BLUE),
        ("Valor Actual de Inventario", f"=SUM({inv_value_range})", CURRENCY_FMT, RED),
        ("Productos en Alerta", f'=COUNTIF({inv_status_range},"Stock Bajo")+COUNTIF({inv_status_range},"Agotado")', INT_FMT, BLACK),
        ("Comisiones a Pagar del Periodo", f"=SUM({com_total_range})", CURRENCY_FMT, BLUE),
        ("Saldo Total por Cobrar", f"=SUM({ar_balance_range})", CURRENCY_FMT, RED),
        ("% Ventas a Credito", f"={_cell_ref(er, 'D', estado_resultados_info['credito_row'])}", PERCENT_FMT, BLACK),
        ("Ticket Promedio", f"={_cell_ref(er, 'D', estado_resultados_info['ticket_row'])}", CURRENCY_FMT, BLUE),
        (
            "Barbero Destacado",
            f'=IFERROR(INDEX({_col_range(com_sheet, comisiones_info["name_col"], comisiones_info["first_row"], comisiones_info["last_row"])},'
            f'MATCH(MAX({com_total_range}),{com_total_range},0)),"Sin datos")',
            None, RED,
        ),
        ("Producto Mas Vendido", top_product_text, None, BLACK),
    ]

    card_span = 5
    col_positions = [1, 6, 11]
    kpi_section_row = 5
    ws.merge_cells(start_row=kpi_section_row, start_column=1, end_row=kpi_section_row, end_column=num_cols)
    ws.cell(row=kpi_section_row, column=1, value="INDICADORES DEL PERIODO").font = SECTION_FONT

    start_row = kpi_section_row + 2
    for i, (label, value, fmt, accent) in enumerate(kpis):
        r = start_row + (i // 3) * 4
        c = col_positions[i % 3]
        _write_kpi_card(ws, r, c, card_span, label, value, accent, fmt)

    last_kpi_row = start_row + ((len(kpis) - 1) // 3) * 4 + 3

    # ---- Conclusiones de gestion ----
    concl_title_row = last_kpi_row + 2
    ws.merge_cells(start_row=concl_title_row, start_column=1, end_row=concl_title_row, end_column=num_cols)
    ws.cell(row=concl_title_row, column=1, value="CONCLUSIONES DE GESTION").font = SECTION_FONT

    margen_cell = _cell_ref(er, "F", estado_resultados_info["utilidad_bruta_row"])
    credito_cell = _cell_ref(er, "D", estado_resultados_info["credito_row"])

    conclusiones = [
        (
            f'="El margen bruto del periodo es "&TEXT({margen_cell},"0.0%")&". "&'
            f'IF({margen_cell}>=0.4,"Es un margen saludable para el negocio.",'
            f'IF({margen_cell}>=0.2,"Es un margen aceptable, con espacio para mejorar precios o costos.",'
            f'"Es un margen bajo y conviene revisar precios de venta o costos de compra."))'
        ),
        (
            f'="El nivel de ventas a credito (fiado y parcial) es "&TEXT({credito_cell},"0.0%")&" de las ventas del periodo. "&'
            f'IF({credito_cell}<=0.15,"Es un nivel manejable.",'
            f'IF({credito_cell}<=0.30,"Es un nivel moderado, vale la pena hacerle seguimiento cercano.",'
            f'"Es un nivel alto que puede afectar el flujo de caja del negocio."))'
        ),
        (
            f'=IF(COUNTIF({inv_status_range},"Agotado")>0,'
            f'"Hay "&COUNTIF({inv_status_range},"Agotado")&" producto(s) agotado(s) que requieren reposicion urgente.",'
            f'IF(COUNTIF({inv_status_range},"Stock Bajo")>0,'
            f'"Hay "&COUNTIF({inv_status_range},"Stock Bajo")&" producto(s) con stock bajo, conviene reabastecer pronto.",'
            f'"El inventario esta en niveles saludables, sin alertas de stock."))'
        ),
        (
            f'=IF({_cell_ref(er, "D", estado_resultados_info["ventas_row"])}=0,'
            f'"No hay ventas registradas en el periodo para comparar contra el saldo por cobrar.",'
            f'IF((SUM({ar_balance_range})/{_cell_ref(er, "D", estado_resultados_info["ventas_row"])})>0.5,'
            f'"El saldo por cobrar es alto en relacion con las ventas del periodo, conviene priorizar el cobro de cartera.",'
            f'IF((SUM({ar_balance_range})/{_cell_ref(er, "D", estado_resultados_info["ventas_row"])})>0.2,'
            f'"El saldo por cobrar es moderado en relacion con las ventas del periodo.",'
            f'"El saldo por cobrar esta en un nivel bajo y controlado.")))'
        ),
    ]

    row = concl_title_row + 2
    for text_formula in conclusiones:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=num_cols)
        cell = ws.cell(row=row, column=1, value=text_formula)
        cell.font = Font(name="Arial", size=10.5, color=DARK_TEXT)
        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True, indent=1)
        ws.row_dimensions[row].height = 30
        row += 1

    last_row = row - 1

    footer_end = _write_footer(ws, last_row, num_cols, footer_logo_path)
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "landscape"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_options.horizontalCentered = True


def _compute_top_product_text(db: Session, start_date: date, end_date: date) -> str:
    from sqlalchemy import func

    start_dt_date, end_dt_date, start_dt, end_dt = _resolve_range(start_date, end_date)
    row = (
        db.query(Product.name, Product.is_deleted, func.sum(OrderItem.quantity))
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            Order.status == "cerrada",
            Order.closed_at >= start_dt,
            Order.closed_at < end_dt,
            OrderItem.item_type == "producto",
        )
        .group_by(Product.id, Product.name, Product.is_deleted)
        .order_by(func.sum(OrderItem.quantity).desc())
        .first()
    )
    if not row:
        return "Sin datos en el periodo"
    name, is_deleted, qty = row
    label = f"{name}{DELETED_PRODUCT_SUFFIX}" if is_deleted else name
    return f"{label} ({int(qty or 0)} und.)"


# ---------------------------------------------------------------------------
# ORQUESTADOR
# ---------------------------------------------------------------------------
def generate_business_report_excel(
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None,
    generated_by: str | None = None,
) -> BytesIO:
    start_date, end_date, start_dt, end_dt = _resolve_range(start_date, end_date)

    logo_path = _find_asset("logo_magnus_modo_claro.png", "logo_magnus.png")
    footer_logo_path = _find_asset("avanzatech-logo.png")

    wb = Workbook()
    wb.remove(wb.active)  # se crea el activo real mas abajo, en orden correcto

    # Inventario y Ventas primero: las demas hojas referencian sus rangos.
    inventario_info = _build_inventario_sheet(wb, db, logo_path, footer_logo_path)
    ventas_info = _build_ventas_sheet(wb, db, start_dt, end_dt, logo_path, footer_logo_path)
    comisiones_info = _build_comisiones_sheet(wb, db, ventas_info, start_dt, end_dt, logo_path, footer_logo_path)
    ar_info = _build_cuentas_por_cobrar_sheet(wb, db, logo_path, footer_logo_path)
    _build_movimientos_sheet(wb, db, start_dt, end_dt, logo_path, footer_logo_path)
    _build_cierres_caja_sheet(wb, db, start_dt, end_dt, logo_path, footer_logo_path)
    estado_resultados_info = _build_estado_resultados_sheet(
        wb, ventas_info, inventario_info, start_date, end_date, logo_path, footer_logo_path
    )

    panorama_ws = wb.create_sheet(title="Panorama General", index=0)
    wb.active = 0
    _build_panorama_sheet(
        panorama_ws, db, estado_resultados_info, inventario_info, ventas_info, comisiones_info, ar_info,
        start_date, end_date, generated_by, logo_path, footer_logo_path,
    )

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
