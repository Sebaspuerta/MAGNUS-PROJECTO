"""
Servicio para generar un reporte Excel (.xlsx) con toda la información
de la base de datos de MAGNUS BARBER, con el logo de la barbería
incrustado en la hoja de resumen.
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


# Columnas que jamás se exportan, aunque existan en el modelo
SENSITIVE_FIELDS = {"password_hash", "quick_pin_hash", "code_hash"}

# (Modelo, nombre de la hoja) — se exporta en este orden
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

BRAND_COLOR = "1A1A1A"      # negro/gris oscuro del tema de la barbería
ACCENT_COLOR = "C9A227"     # dorado, típico de identidad de barbería
HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=11)
HEADER_FILL = PatternFill(start_color=BRAND_COLOR, end_color=BRAND_COLOR, fill_type="solid")
TITLE_FONT = Font(name="Arial", bold=True, color=BRAND_COLOR, size=16)
SUBTITLE_FONT = Font(name="Arial", italic=True, color="555555", size=10)
THIN_BORDER = Border(*(Side(style="thin", color="DDDDDD") for _ in range(4)))


def _find_logo_path() -> Path | None:
    """
    Busca el logo de la barbería en un par de ubicaciones probables
    dentro del proyecto. Ajusta esta lista si tu logo vive en otra ruta.
    """
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


def _clean_value(value):
    """Convierte tipos que openpyxl no serializa bien de forma directa."""
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


def _build_summary_sheet(wb: Workbook, table_counts: list[tuple[str, int]], logo_path: Path | None) -> None:
    ws = wb.active
    ws.title = "Resumen"

    if logo_path is not None:
        try:
            img = XLImage(str(logo_path))
            img.height = 90
            img.width = 90
            ws.add_image(img, "A1")
        except Exception:
            # Si la imagen no se puede leer, seguimos sin logo en vez de romper el reporte
            pass

    ws["D1"] = "MAGNUS BARBER"
    ws["D1"].font = TITLE_FONT
    ws["D2"] = "Reporte General de Base de Datos"
    ws["D2"].font = Font(name="Arial", bold=True, size=12, color=BRAND_COLOR)
    ws["D3"] = f"Generado el {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ws["D3"].font = SUBTITLE_FONT

    start_row = 8
    ws.cell(row=start_row, column=1, value="Tabla").font = HEADER_FONT
    ws.cell(row=start_row, column=2, value="Registros").font = HEADER_FONT
    for col in (1, 2):
        c = ws.cell(row=start_row, column=col)
        c.fill = HEADER_FILL
        c.alignment = Alignment(horizontal="left" if col == 1 else "center")

    for i, (name, count) in enumerate(table_counts, start=start_row + 1):
        ws.cell(row=i, column=1, value=name).border = THIN_BORDER
        cell_count = ws.cell(row=i, column=2, value=count)
        cell_count.border = THIN_BORDER
        cell_count.alignment = Alignment(horizontal="center")

    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["D"].width = 40


def generate_full_database_excel(db: Session) -> BytesIO:
    wb = Workbook()
    logo_path = _find_logo_path()

    table_counts: list[tuple[str, int]] = []
    for model, sheet_name in TABLES:
        count = _write_model_sheet(wb, db, model, sheet_name)
        table_counts.append((sheet_name, count))

    # La hoja "Resumen" se arma al final para tener ya los conteos, pero
    # queremos que quede primera en el libro.
    _build_summary_sheet(wb, table_counts, logo_path)
    wb.move_sheet("Resumen", offset=-(len(wb.sheetnames) - 1))

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer