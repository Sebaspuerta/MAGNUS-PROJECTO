"""
Servicio para generar un reporte Excel (.xlsx) con toda la información
de la base de datos de MAGNUS BARBER, con una portada tipo dashboard
(KPIs + gráficos nativos) que replica la identidad visual de la marca.
"""

from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy import func
from sqlalchemy.orm import Session
from openpyxl.chart.layout import Layout, ManualLayout
from app.models.security import Role, Permission, User, AuditLog
from app.models.barber import Barber
from app.models.client import Client
from app.models.service import Service
from app.models.service_consumable import ServiceConsumable
from app.models.inventory import Product, InventoryMovement
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.cash_register import CashRegister
from app.models.cash_movement import CashMovement
from app.models.accounts_receivable import AccountsReceivable, AccountsReceivablePayment
from app.models.alerts import Alert
from app.models.system_config import SystemConfig
from app.utils.deleted_labels import DELETED_BARBER_SUFFIX, DELETED_PRODUCT_SUFFIX


SENSITIVE_FIELDS = {"password_hash", "quick_pin_hash", "code_hash"}

TABLES: list[tuple[type, str]] = [
    (Role, "Roles"),
    (Permission, "Permisos"),
    (User, "Usuarios"),
    (Barber, "Barberos"),
    (Client, "Clientes"),
    (Service, "Servicios"),
    (ServiceConsumable, "Consumibles Servicio"),
    (Product, "Productos"),
    (InventoryMovement, "Mov. Inventario"),
    (Order, "Ordenes"),
    (OrderItem, "Items de Orden"),
    (Payment, "Pagos"),
    (CashRegister, "Cajas"),
    (CashMovement, "Mov. de Caja"),
    (AccountsReceivable, "Cuentas x Cobrar"),
    (AccountsReceivablePayment, "Pagos Ctas x Cobrar"),
    (Alert, "Alertas"),
    (AuditLog, "Auditoria"),
    (SystemConfig, "Configuracion"),
]

# ---------------------------------------------------------------------------
# IDENTIDAD VISUAL — ajusta si algo no coincide con tu marca
# ---------------------------------------------------------------------------
BRAND_NAME = "MAGNUS BARBER SHOP"
BRAND_SUBTITLE = "Reporte General de Base de Datos"
BRAND_LOCATION = "Cartagena, Colombia"
FOOTER_COMPANY = "Desarrollado por AVANZATECH S.A.S"
FOOTER_TAGLINE = "Soluciones Tecnologicas que Impulsan tu Negocio"
FOOTER_SOFTWARE = "Software MAGNUS BARBER SYSTEM v1.0"

BLACK = "0B0B0C"
WHITE = "FFFFFF"
RED = "E24B4A"
BLUE = "378ADD"
GRAY_TEXT = "6B7280"
LIGHT_GRAY_FILL = "F5F5F4"
DARK_TEXT = "1A1A1A"

KPI_COLORS = [RED, BLUE, "888780", RED, BLUE, "27500A"]
CARD_ACCENTS = [RED, BLUE, "888780", "0C447C", "993C1D", "27500A"]

HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=11)
HEADER_FILL = PatternFill(start_color=BLACK, end_color=BLACK, fill_type="solid")
THIN_BORDER = Border(*(Side(style="thin", color="DDDDDD") for _ in range(4)))
CURRENCY_FMT = '"$" #,##0'


# ---------------------------------------------------------------------------
# Utilidades generales
# ---------------------------------------------------------------------------
def _find_logo_path() -> Path | None:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "frontend" / "assets" / "logo.png",
        here.parents[2] / "frontend" / "assets" / "logo.png",
        here.parents[3] / "frontend" / "assets" / "img" / "logo.png",
        here.parents[3] / "frontend" / "img" / "logo.png",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def _find_footer_logo_path() -> Path | None:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "frontend" / "assets" / "avanzatech-logo.png",
        here.parents[2] / "frontend" / "assets" / "avanzatech-logo.png",
        here.parents[3] / "frontend" / "assets" / "img" / "avanzatech-logo.png",
        here.parents[3] / "frontend" / "img" / "avanzatech-logo.png",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def _clean_value(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


def _style_header_row(ws: Worksheet, num_columns: int, row: int = 1) -> None:
    for col_idx in range(1, num_columns + 1):
        cell = ws.cell(row=row, column=col_idx)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER


def _autofit_columns(ws: Worksheet, num_columns: int, max_width: int = 40) -> None:
    for col_idx in range(1, num_columns + 1):
        letter = get_column_letter(col_idx)
        longest = 0
        for cell in ws[letter]:
            if cell.value is not None:
                longest = max(longest, len(str(cell.value)))
        ws.column_dimensions[letter].width = min(max(longest + 2, 10), max_width)


def _write_model_sheet(wb: Workbook, db: Session, model: type, sheet_title: str) -> int:
    ws = wb.create_sheet(title=sheet_title[:31])

    columns = [c for c in model.__table__.columns if c.name not in SENSITIVE_FIELDS]
    headers = [c.name for c in columns]
    ws.append(headers)
    _style_header_row(ws, len(headers))

    rows = db.query(model).all()
    for obj in rows:
        row = [_clean_value(getattr(obj, c.name)) for c in columns]
        ws.append(row)

    for row_cells in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=len(headers)):
        for cell in row_cells:
            cell.border = THIN_BORDER
            if isinstance(cell.value, (datetime, date)):
                cell.number_format = "yyyy-mm-dd hh:mm" if isinstance(cell.value, datetime) else "yyyy-mm-dd"

    ws.freeze_panes = "A2"
    if ws.max_row >= 1 and ws.max_column >= 1:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{ws.max_row}"
    _autofit_columns(ws, len(headers))

    return len(rows)


# ---------------------------------------------------------------------------
# Métricas de negocio para el dashboard
# ---------------------------------------------------------------------------
def _compute_kpis(db: Session) -> dict:
    total_sales = db.query(func.coalesce(func.sum(Payment.amount), 0)).scalar()

    cxc_pendiente = (
        db.query(func.coalesce(func.sum(AccountsReceivable.balance), 0))
        .filter(AccountsReceivable.is_active == True, AccountsReceivable.balance > 0)  # noqa: E712
        .scalar()
    )

    stock_bajo = (
        db.query(func.count(Product.id))
        .filter(Product.minimum_stock.isnot(None))
        .filter(Product.current_stock <= Product.minimum_stock)
        .scalar()
    )

    barbero_top = (
        db.query(Barber.full_name, Barber.is_deleted, func.sum(Order.total))
        .join(Order, Order.barber_id == Barber.id)
        .filter(Order.status == "cerrada")
        .group_by(Barber.id, Barber.full_name, Barber.is_deleted)
        .order_by(func.sum(Order.total).desc())
        .first()
    )

    producto_top = (
        db.query(Product.name, Product.is_deleted, func.sum(OrderItem.quantity))
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(Order.status == "cerrada")
        .group_by(Product.id, Product.name, Product.is_deleted)
        .order_by(func.sum(OrderItem.quantity).desc())
        .first()
    )

    caja_abierta = db.query(CashRegister).filter(CashRegister.is_closed.is_(False)).first()

    barbero_top_nombre = "Sin datos"
    if barbero_top:
        barbero_top_nombre = barbero_top[0] + (DELETED_BARBER_SUFFIX if barbero_top[1] else "")

    producto_top_nombre = "Sin datos"
    if producto_top:
        producto_top_nombre = producto_top[0] + (DELETED_PRODUCT_SUFFIX if producto_top[1] else "")

    return {
        "total_sales": float(total_sales or 0),
        "cxc_pendiente": float(cxc_pendiente or 0),
        "stock_bajo": int(stock_bajo or 0),
        "barbero_top": barbero_top_nombre,
        "barbero_top_monto": float(barbero_top[2]) if barbero_top else 0,
        "producto_top": producto_top_nombre,
        "producto_top_unidades": int(producto_top[2]) if producto_top else 0,
        "estado_caja": "Abierta" if caja_abierta else "Cerrada",
    }


def _fetch_sales_by_barber(db: Session, limit: int = 6) -> list[tuple[str, float]]:
    rows = (
        db.query(Barber.full_name, Barber.is_deleted, func.sum(Order.total))
        .join(Order, Order.barber_id == Barber.id)
        .filter(Order.status == "cerrada")
        .group_by(Barber.id, Barber.full_name, Barber.is_deleted)
        .order_by(func.sum(Order.total).desc())
        .limit(limit)
        .all()
    )
    return [
        (name + (DELETED_BARBER_SUFFIX if is_deleted else ""), float(total or 0))
        for name, is_deleted, total in rows
    ]


def _fetch_sales_by_month(db: Session, months: int = 12) -> list[tuple[str, float]]:
    month_col = func.date_trunc("month", Order.closed_at).label("mes")
    rows = (
        db.query(month_col, func.sum(Order.total))
        .filter(Order.status == "cerrada")
        .group_by(month_col)
        .order_by(month_col)
        .all()
    )
    rows = rows[-months:]
    return [(mes.strftime("%b %Y"), float(total or 0)) for mes, total in rows]


def _fetch_payment_methods(db: Session) -> list[tuple[str, float]]:
    rows = (
        db.query(Payment.payment_method, func.sum(Payment.amount))
        .group_by(Payment.payment_method)
        .order_by(func.sum(Payment.amount).desc())
        .all()
    )
    return [(method or "Sin especificar", float(total or 0)) for method, total in rows]


def _fetch_top_products(db: Session, limit: int = 6) -> list[tuple[str, float]]:
    rows = (
        db.query(Product.name, Product.is_deleted, func.sum(OrderItem.total_price))
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(Order.status == "cerrada")
        .group_by(Product.id, Product.name, Product.is_deleted)
        .order_by(func.sum(OrderItem.total_price).desc())
        .limit(limit)
        .all()
    )
    return [
        (name + (DELETED_PRODUCT_SUFFIX if is_deleted else ""), float(total or 0))
        for name, is_deleted, total in rows
    ]


# ---------------------------------------------------------------------------
# Construcción visual del dashboard
# ---------------------------------------------------------------------------
def _write_kpi_card(
    ws: Worksheet,
    row: int,
    col_start: int,
    col_span: int,
    label: str,
    value_text: str,
    accent_hex: str,
) -> None:
    end_col = col_start + col_span - 1

    ws.merge_cells(start_row=row, start_column=col_start, end_row=row, end_column=end_col)
    label_cell = ws.cell(row=row, column=col_start, value=label.upper())
    label_cell.font = Font(name="Arial", size=9, bold=True, color=GRAY_TEXT)
    label_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)

    ws.merge_cells(start_row=row + 1, start_column=col_start, end_row=row + 1, end_column=end_col)
    value_cell = ws.cell(row=row + 1, column=col_start, value=value_text)
    value_cell.font = Font(name="Arial", size=17, bold=True, color=accent_hex)
    value_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)

    ws.merge_cells(start_row=row + 2, start_column=col_start, end_row=row + 2, end_column=end_col)
    for c in range(col_start, end_col + 1):
        ws.cell(row=row + 2, column=c).border = Border(bottom=Side(style="thin", color=accent_hex))


def _write_hidden_series(ws: Worksheet, top_row: int, col: int, title: str, data: list[tuple[str, float]]):
    """Escribe una serie de datos en un área auxiliar para alimentar un gráfico nativo."""
    ws.cell(row=top_row, column=col, value=title)
    ws.cell(row=top_row + 1, column=col, value="Categoria")
    ws.cell(row=top_row + 1, column=col + 1, value="Valor")
    for i, (label, value) in enumerate(data):
        ws.cell(row=top_row + 2 + i, column=col, value=label)
        value_cell = ws.cell(row=top_row + 2 + i, column=col + 1, value=value)
        value_cell.number_format = '"$" #,##0'
    return top_row + 2, top_row + 2 + len(data) - 1


def _build_bar_chart(
    ws: Worksheet,
    title: str,
    data_col: int,
    start_row: int,
    end_row: int,
    sheet_ref: str,
    x_title: str = "",
    y_title: str = "Ventas ($)",
) -> BarChart:
    chart = BarChart()
    chart.type = "col"
    chart.title = title
    chart.plotVisOnly = False
    chart.y_axis.majorGridlines = None
    chart.style = 10
    chart.legend = None
    chart.width = 13
    chart.height = 8

    chart.x_axis.title = x_title
    chart.y_axis.title = y_title
    chart.x_axis.delete = False
    chart.y_axis.delete = False
    chart.y_axis.numFmt = '"$"#,##0'

    cats = Reference(ws, min_col=data_col, min_row=start_row, max_row=end_row)
    vals = Reference(ws, min_col=data_col + 1, min_row=start_row - 1, max_row=end_row)
    chart.add_data(vals, titles_from_data=True)
    chart.set_categories(cats)

    return chart

def _build_pie_chart(ws: Worksheet, title: str, data_col: int, start_row: int, end_row: int) -> PieChart:
    chart = PieChart()
    chart.title = title
    chart.style = 10
    chart.plotVisOnly = False
    chart.width = 13
    chart.height = 8

    cats = Reference(ws, min_col=data_col, min_row=start_row, max_row=end_row)
    vals = Reference(ws, min_col=data_col + 1, min_row=start_row - 1, max_row=end_row)
    chart.add_data(vals, titles_from_data=True)
    chart.set_categories(cats)

    chart.dataLabels = DataLabelList()
    chart.dataLabels.showSerName = False
    chart.dataLabels.showLegendKey = False
    chart.dataLabels.showCatName = True
    chart.dataLabels.showVal = True
    chart.dataLabels.showPercent = False
    chart.dataLabels.numFmt = '"$"#,##0'
    chart.dataLabels.dLblPos = "bestFit"

    chart.legend = None  # ya no hace falta, el nombre va en cada porción

    return chart


def _build_line_chart(
    ws: Worksheet,
    title: str,
    data_col: int,
    start_row: int,
    end_row: int,
    x_title: str = "Mes",
    y_title: str = "Ventas ($)",
) -> LineChart:
    chart = LineChart()
    chart.title = title
    chart.style = 10
    chart.legend = None
    chart.y_axis.majorGridlines = None
    chart.plotVisOnly = False
    chart.width = 13
    chart.height = 8

    chart.x_axis.title = x_title
    chart.y_axis.title = y_title
    chart.x_axis.delete = False
    chart.y_axis.delete = False
    chart.y_axis.numFmt = '"$"#,##0'

    cats = Reference(ws, min_col=data_col, min_row=start_row, max_row=end_row)
    vals = Reference(ws, min_col=data_col + 1, min_row=start_row - 1, max_row=end_row)
    chart.add_data(vals, titles_from_data=True)
    chart.set_categories(cats)

    return chart


def _build_summary_sheet(
    wb: Workbook,
    table_counts: list[tuple[str, int]],
    kpis: dict,
    sales_by_barber: list[tuple[str, float]],
    sales_by_month: list[tuple[str, float]],
    payment_methods: list[tuple[str, float]],
    top_products: list[tuple[str, float]],
    logo_path: Path | None,
    footer_logo_path: Path | None,
    generated_by: str | None,
) -> None:
    ws = wb.active
    ws.title = "Resumen"
    ws.sheet_view.showGridLines = False

    total_cols = 19  # A..S
    for col_idx in range(1, total_cols + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 10

    last_col_letter = get_column_letter(total_cols)

    # ---------------- BANNER SUPERIOR ----------------
    BANNER_ROWS = 7
    for r in range(1, BANNER_ROWS + 1):
        ws.row_dimensions[r].height = 22
        for col_idx in range(1, total_cols + 1):
            ws.cell(row=r, column=col_idx).fill = PatternFill(start_color=BLACK, end_color=BLACK, fill_type="solid")

    if logo_path is not None:
        try:
            img = XLImage(str(logo_path))
            img.height = 140
            img.width = 140
            ws.add_image(img, "A1")
        except Exception:
            pass

    ws.merge_cells(f"D2:{last_col_letter}2")
    title_cell = ws["D2"]
    title_cell.value = BRAND_NAME
    title_cell.font = Font(name="Arial", bold=True, size=24, color=WHITE)
    title_cell.alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells(f"D3:{last_col_letter}3")
    subtitle_cell = ws["D3"]
    subtitle_cell.value = f"{BRAND_SUBTITLE}  -  {BRAND_LOCATION}"
    subtitle_cell.font = Font(name="Arial", bold=True, size=12, color="D1D1D1")
    subtitle_cell.alignment = Alignment(horizontal="left", vertical="center")

    # línea roja/azul de marca (mitad y mitad del ancho útil)
    mid_col = 4 + (total_cols - 4) // 2
    mid_col_letter = get_column_letter(mid_col)
    next_col_letter = get_column_letter(mid_col + 1)
    ws.merge_cells(f"D4:{mid_col_letter}4")
    ws["D4"].fill = PatternFill(start_color=BLUE, end_color=BLUE, fill_type="solid")
    ws.merge_cells(f"{next_col_letter}4:{last_col_letter}4")
    ws[f"{next_col_letter}4"].fill = PatternFill(start_color=RED, end_color=RED, fill_type="solid")
    ws.row_dimensions[4].height = 5

    ws.merge_cells(f"D6:{last_col_letter}6")
    period_cell = ws["D6"]
    period_cell.value = f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    period_cell.font = Font(name="Arial", bold=True, size=12, color=WHITE)
    period_cell.alignment = Alignment(horizontal="left", vertical="center")

    # ---------------- FRANJA DE METADATA ----------------
    meta_row = BANNER_ROWS + 1
    ws.merge_cells(start_row=meta_row, start_column=1, end_row=meta_row, end_column=total_cols)
    meta_cell = ws.cell(row=meta_row, column=1)
    total_registros = sum(count for _, count in table_counts)
    meta_cell.value = (
        f"Generado por: {generated_by or 'Sistema'}   |   "
        f"Tablas incluidas: {len(table_counts)}   |   "
        f"Registros totales: {total_registros}   |   Moneda: COP ($)"
    )
    meta_cell.font = Font(name="Arial", size=10, italic=True, color=GRAY_TEXT)
    meta_cell.fill = PatternFill(start_color=LIGHT_GRAY_FILL, end_color=LIGHT_GRAY_FILL, fill_type="solid")
    meta_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[meta_row].height = 20

    # ---------------- KPIs ----------------
    kpi_section_row = meta_row + 2
    ws.merge_cells(start_row=kpi_section_row, start_column=1, end_row=kpi_section_row, end_column=total_cols)
    ws.cell(row=kpi_section_row, column=1, value="PANORAMA GENERAL").font = Font(
        name="Arial", bold=True, size=13, color=DARK_TEXT
    )

    kpi_values = [
        ("Ventas totales", f"$ {kpis['total_sales']:,.0f}".replace(",", ".")),
        ("Cuentas por cobrar", f"$ {kpis['cxc_pendiente']:,.0f}".replace(",", ".")),
        ("Productos stock bajo", str(kpis["stock_bajo"])),
        ("Barbero con más ventas", kpis["barbero_top"]),
        ("Producto más vendido", kpis["producto_top"]),
        ("Estado de caja", kpis["estado_caja"]),
    ]

    # 3 tarjetas por fila, cada una ocupa 5 columnas, con 1 columna de aire
    # entre tarjetas y 1 columna de margen a cada lado -> queda centrado.
    card_span = 5
    col_positions = [2, 8, 14]

    kpi_row_1 = kpi_section_row + 2
    kpi_row_2 = kpi_row_1 + 5

    for i, (label, value_text) in enumerate(kpi_values):
        row = kpi_row_1 if i < 3 else kpi_row_2
        col = col_positions[i % 3]
        _write_kpi_card(ws, row, col, card_span, label, value_text, KPI_COLORS[i])

    # ---------------- GRÁFICOS ----------------
    charts_title_row = kpi_row_2 + 5
    ws.merge_cells(start_row=charts_title_row, start_column=1, end_row=charts_title_row, end_column=total_cols)
    ws.cell(row=charts_title_row, column=1, value="ANALISIS VISUAL").font = Font(
        name="Arial", bold=True, size=13, color=DARK_TEXT
    )

    ws_data = wb.create_sheet(title="DatosDashboard")
    ws_data.sheet_view.showGridLines = False
    ws_data.sheet_properties.tabColor = "CCCCCC"

    s1_start, s1_end = _write_hidden_series(ws_data, 1, 1, "Ventas por barbero", sales_by_barber)
    s2_start, s2_end = _write_hidden_series(ws_data, 1, 4, "Ventas por mes", sales_by_month)
    s3_start, s3_end = _write_hidden_series(ws_data, 1, 7, "Metodos de pago", payment_methods)
    s4_start, s4_end = _write_hidden_series(ws_data, 1, 10, "Top productos", top_products)

    chart_row = charts_title_row + 2

    bar1 = _build_bar_chart(ws_data, "Ventas por barbero", 1, s1_start, s1_end, "DatosDashboard", x_title="Barbero", y_title="Ventas ($)")
    ws.add_chart(bar1, f"B{chart_row}")

    line1 = _build_line_chart(ws_data, "Ventas por mes", 4, s2_start, s2_end, x_title="Mes", y_title="Ventas ($)")
    ws.add_chart(line1, f"L{chart_row}")

    chart_row_2 = chart_row + 21

    pie1 = _build_pie_chart(ws_data, "Metodos de pago", 7, s3_start, s3_end)
    ws.add_chart(pie1, f"B{chart_row_2}")

    bar2 = _build_bar_chart(ws_data, "Top productos vendidos", 10, s4_start, s4_end, "DatosDashboard", x_title="Producto", y_title="Ventas ($)")
    ws.add_chart(bar2, f"L{chart_row_2}")

    # ---------------- DETALLE DE TABLAS (conteo por tabla) ----------------
    detail_row = chart_row_2 + 21
    ws.merge_cells(start_row=detail_row, start_column=1, end_row=detail_row, end_column=total_cols)
    ws.cell(row=detail_row, column=1, value="DETALLE DE TABLAS").font = Font(
        name="Arial", bold=True, size=13, color=DARK_TEXT
    )

    cards_start_row = detail_row + 2
    row_offset = 0
    for i, (name, count) in enumerate(table_counts):
        card_col = col_positions[i % 3]
        card_row = cards_start_row + row_offset
        accent = CARD_ACCENTS[i % len(CARD_ACCENTS)]
        _write_kpi_card(ws, card_row, card_col, card_span, name, str(count), accent)
        if i % 3 == 2:
            row_offset += 5

    last_row = cards_start_row + row_offset + 5

    # ---------------- PIE DE PÁGINA ----------------
    footer_row = last_row + 2
    ws.row_dimensions[footer_row].height = 32
    ws.row_dimensions[footer_row + 1].height = 16

    if footer_logo_path is not None:
        try:
            footer_img = XLImage(str(footer_logo_path))
            footer_img.height = 48
            footer_img.width = 48
            ws.add_image(footer_img, f"A{footer_row}")
        except Exception:
            pass

    text_start_col = 3
    ws.merge_cells(start_row=footer_row, start_column=text_start_col, end_row=footer_row, end_column=total_cols)
    footer_cell = ws.cell(row=footer_row, column=text_start_col, value=FOOTER_COMPANY)
    footer_cell.font = Font(name="Arial", bold=True, size=11, color=DARK_TEXT)
    footer_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)

    ws.merge_cells(start_row=footer_row + 1, start_column=text_start_col, end_row=footer_row + 1, end_column=total_cols)
    tagline_cell = ws.cell(
        row=footer_row + 1,
        column=text_start_col,
        value=f"{FOOTER_TAGLINE}   -   (c) {datetime.now().year}   -   {FOOTER_SOFTWARE}",
    )
    tagline_cell.font = Font(name="Arial", size=9, color=GRAY_TEXT)
    tagline_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)

    # ---------------- CENTRADO AL IMPRIMIR ----------------
    ws.print_options.horizontalCentered = True
    ws.print_area = f"A1:{last_col_letter}{footer_row + 2}"


def generate_full_database_excel(db: Session, generated_by: str | None = None) -> BytesIO:
    wb = Workbook()
    logo_path = _find_logo_path()
    footer_logo_path = _find_footer_logo_path()

    table_counts: list[tuple[str, int]] = []
    for model, sheet_name in TABLES:
        count = _write_model_sheet(wb, db, model, sheet_name)
        table_counts.append((sheet_name, count))

    kpis = _compute_kpis(db)
    sales_by_barber = _fetch_sales_by_barber(db)
    sales_by_month = _fetch_sales_by_month(db)
    payment_methods = _fetch_payment_methods(db)
    top_products = _fetch_top_products(db)

    print(f"[DEBUG] sales_by_barber: {sales_by_barber}")
    print(f"[DEBUG] sales_by_month: {sales_by_month}")
    print(f"[DEBUG] payment_methods: {payment_methods}")
    print(f"[DEBUG] top_products: {top_products}")

    _build_summary_sheet(
        wb,
        table_counts,
        kpis,
        sales_by_barber,
        sales_by_month,
        payment_methods,
        top_products,
        logo_path,
        footer_logo_path,
        generated_by,
    )
    wb.move_sheet("Resumen", offset=-(len(wb.sheetnames) - 1))

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer