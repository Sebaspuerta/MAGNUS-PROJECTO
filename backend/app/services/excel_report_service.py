"""
Servicio para generar un reporte Excel (.xlsx) con toda la información
de la base de datos de MAGNUS BARBER, con una portada estilizada que
replica la identidad visual de la barbería.
"""

from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy.orm import Session

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
# IDENTIDAD VISUAL — ajusta estas constantes si algo no coincide con tu marca
# ---------------------------------------------------------------------------
BRAND_NAME = "MAGNUS BARBER SHOP"
BRAND_SUBTITLE = "Reporte General de Base de Datos"
BRAND_LOCATION = "Cartagena, Colombia"
FOOTER_COMPANY = "Desarrollado por AVANZATECH S.A.S"
FOOTER_TAGLINE = "Soluciones Tecnologicas que Impulsan tu Negocio"
FOOTER_SOFTWARE = "Software MAGNUS BARBER SYSTEM v1.0"

NAVY = "0E1B3D"
GOLD = "C9A227"
GRAY_TEXT = "6B7280"
LIGHT_GRAY_FILL = "F3F4F6"
DARK_TEXT = "1A1A1A"

CARD_ACCENTS = [GOLD, GOLD, GOLD, NAVY, "B03A2E", "1E8449"]

HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=11)
HEADER_FILL = PatternFill(start_color=NAVY, end_color=NAVY, fill_type="solid")
THIN_BORDER = Border(*(Side(style="thin", color="DDDDDD") for _ in range(4)))


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
    """Logo de AvanzaTech (o el desarrollador) para el pie de página."""
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


def _write_kpi_card(ws: Worksheet, top_row: int, start_col: int, label: str, value, accent_hex: str) -> None:
    """Dibuja una tarjeta de indicador de 2 columnas x 3 filas."""
    end_col = start_col + 1

    # Barra superior de color (acento)
    ws.merge_cells(start_row=top_row, start_column=start_col, end_row=top_row, end_column=end_col)
    accent_cell = ws.cell(row=top_row, column=start_col)
    accent_cell.fill = PatternFill(start_color=accent_hex, end_color=accent_hex, fill_type="solid")
    ws.row_dimensions[top_row].height = 4

    # Fondo gris claro para el cuerpo de la tarjeta (label + valor)
    for r in (top_row + 1, top_row + 2):
        ws.merge_cells(start_row=r, start_column=start_col, end_row=r, end_column=end_col)
        cell = ws.cell(row=r, column=start_col)
        cell.fill = PatternFill(start_color=LIGHT_GRAY_FILL, end_color=LIGHT_GRAY_FILL, fill_type="solid")

    label_cell = ws.cell(row=top_row + 1, column=start_col, value=label.upper())
    label_cell.font = Font(name="Arial", size=8, bold=True, color=GRAY_TEXT)
    label_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)

    value_cell = ws.cell(row=top_row + 2, column=start_col, value=value)
    value_cell.font = Font(name="Arial", size=14, bold=True, color=DARK_TEXT)
    value_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)


def _build_summary_sheet(
    wb: Workbook,
    table_counts: list[tuple[str, int]],
    logo_path: Path | None,
    footer_logo_path: Path | None,
    generated_by: str | None,
) -> None:
    ws = wb.active
    ws.title = "Resumen"
    ws.sheet_view.showGridLines = False

    total_cols = 9  # A..I
    for col_idx in range(1, total_cols + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 13

    # ---------------- BANNER SUPERIOR ----------------
    BANNER_ROWS = 7
    for r in range(1, BANNER_ROWS + 1):
        ws.row_dimensions[r].height = 20
        for col_idx in range(1, total_cols + 1):
            ws.cell(row=r, column=col_idx).fill = PatternFill(
                start_color=NAVY, end_color=NAVY, fill_type="solid"
            )

    if logo_path is not None:
        try:
            img = XLImage(str(logo_path))
            img.height = 120
            img.width = 120
            ws.add_image(img, "A1")
        except Exception:
            pass

    ws.merge_cells("D2:I2")
    title_cell = ws["D2"]
    title_cell.value = BRAND_NAME
    title_cell.font = Font(name="Arial", bold=True, size=20, color="FFFFFF")
    title_cell.alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells("D3:I3")
    subtitle_cell = ws["D3"]
    subtitle_cell.value = f"{BRAND_SUBTITLE}  -  {BRAND_LOCATION}"
    subtitle_cell.font = Font(name="Arial", bold=True, size=10, color=GOLD)
    subtitle_cell.alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells("D5:I5")
    period_cell = ws["D5"]
    period_cell.value = f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    period_cell.font = Font(name="Arial", bold=True, size=11, color="FFFFFF")
    period_cell.alignment = Alignment(horizontal="left", vertical="center")

    # ---------------- FRANJA DE METADATA ----------------
    meta_row = BANNER_ROWS + 1
    ws.merge_cells(start_row=meta_row, start_column=1, end_row=meta_row, end_column=total_cols)
    meta_cell = ws.cell(row=meta_row, column=1)
    total_registros = sum(count for _, count in table_counts)
    meta_text = (
        f"Generado por: {generated_by or 'Sistema'}   |   "
        f"Tablas incluidas: {len(table_counts)}   |   "
        f"Registros totales: {total_registros}   |   Moneda: COP ($)"
    )
    meta_cell.value = meta_text
    meta_cell.font = Font(name="Arial", size=9, italic=True, color=GRAY_TEXT)
    meta_cell.fill = PatternFill(start_color=LIGHT_GRAY_FILL, end_color=LIGHT_GRAY_FILL, fill_type="solid")
    meta_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[meta_row].height = 18

    # ---------------- TÍTULO DE SECCIÓN ----------------
    section_row = meta_row + 2
    ws.merge_cells(start_row=section_row, start_column=1, end_row=section_row, end_column=total_cols)
    section_cell = ws.cell(row=section_row, column=1, value="RESUMEN DE TABLAS")
    section_cell.font = Font(name="Arial", bold=True, size=12, color=DARK_TEXT)
    for col_idx in range(1, total_cols + 1):
        ws.cell(row=section_row + 1, column=col_idx).border = Border(
            bottom=Side(style="medium", color=GOLD)
        )

    # ---------------- TARJETAS (3 por fila) ----------------
    cards_start_row = section_row + 3
    col_positions = [1, 4, 7]  # columnas A, D, G -> cada tarjeta ocupa 2 columnas
    row_offset = 0

    for i, (name, count) in enumerate(table_counts):
        card_col = col_positions[i % 3]
        card_row = cards_start_row + row_offset
        accent = CARD_ACCENTS[i % len(CARD_ACCENTS)]
        _write_kpi_card(ws, card_row, card_col, name, count, accent)

        if i % 3 == 2:
            row_offset += 4  # 3 filas de tarjeta + 1 de espacio

    last_row = cards_start_row + row_offset + 4

    # ---------------- PIE DE PÁGINA ----------------
    footer_row = last_row + 2

    ws.row_dimensions[footer_row].height = 30
    ws.row_dimensions[footer_row + 1].height = 15

    if footer_logo_path is not None:
        try:
            footer_img = XLImage(str(footer_logo_path))
            footer_img.height = 45
            footer_img.width = 45
            ws.add_image(footer_img, f"A{footer_row}")
        except Exception:
            pass

    text_start_col = 3  # columna C, deja A-B libres para el logo

    ws.merge_cells(start_row=footer_row, start_column=text_start_col, end_row=footer_row, end_column=total_cols)
    footer_cell = ws.cell(row=footer_row, column=text_start_col, value=FOOTER_COMPANY)
    footer_cell.font = Font(name="Arial", bold=True, size=10, color=DARK_TEXT)
    footer_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)

    ws.merge_cells(start_row=footer_row + 1, start_column=text_start_col, end_row=footer_row + 1, end_column=total_cols)
    tagline_cell = ws.cell(
        row=footer_row + 1,
        column=text_start_col,
        value=f"{FOOTER_TAGLINE}   -   (c) {datetime.now().year}   -   {FOOTER_SOFTWARE}",
    )
    tagline_cell.font = Font(name="Arial", size=8, color=GRAY_TEXT)
    tagline_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)


def generate_full_database_excel(db: Session, generated_by: str | None = None) -> BytesIO:
    wb = Workbook()
    logo_path = _find_logo_path()
    footer_logo_path = _find_footer_logo_path()

    table_counts: list[tuple[str, int]] = []
    for model, sheet_name in TABLES:
        count = _write_model_sheet(wb, db, model, sheet_name)
        table_counts.append((sheet_name, count))

    _build_summary_sheet(wb, table_counts, logo_path, footer_logo_path, generated_by)
    wb.move_sheet("Resumen", offset=-(len(wb.sheetnames) - 1))

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer