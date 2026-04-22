import csv
import io
from datetime import datetime
from typing import List

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from app.models import DocumentLog, AckStatus

_HEADERS = [
    "ID", "Username", "Full Name", "Department", "Email",
    "Status", "Opened At", "Confirmed At", "Acknowledged At", "IP Address",
]

_STATUS_LABELS = {
    AckStatus.ANONYMOUS_OPENED: "Anonymous",
    AckStatus.IDENTIFIED_NOT_CONFIRMED: "Identified (not confirmed)",
    AckStatus.CONFIRMED: "Confirmed",
    AckStatus.ACKNOWLEDGED: "Acknowledged",
}


def _fmt_dt(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


def _row(log: DocumentLog) -> list:
    return [
        log.id,
        log.ad_username or "",
        log.full_name or "",
        log.department or "",
        log.email or "",
        _STATUS_LABELS.get(log.status, log.status),
        _fmt_dt(log.opened_at),
        _fmt_dt(log.confirmed_at),
        _fmt_dt(log.acknowledged_at),
        log.ip_address or "",
    ]


def export_csv(logs: List[DocumentLog]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_HEADERS)
    for log in logs:
        writer.writerow(_row(log))
    return buf.getvalue().encode("utf-8-sig")  # BOM for Excel compat


def export_excel(logs: List[DocumentLog], doc_title: str) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Acknowledgements"

    # Title row
    ws.merge_cells("A1:J1")
    title_cell = ws["A1"]
    title_cell.value = doc_title
    title_cell.font = Font(bold=True, size=13)
    title_cell.alignment = Alignment(horizontal="center")

    # Header row
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(bold=True, color="FFFFFF")
    for col, header in enumerate(_HEADERS, start=1):
        cell = ws.cell(row=2, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    # Data rows
    status_colors = {
        AckStatus.ANONYMOUS_OPENED: "FFF2CC",
        AckStatus.IDENTIFIED_NOT_CONFIRMED: "FCE4D6",
        AckStatus.CONFIRMED: "DDEBF7",
        AckStatus.ACKNOWLEDGED: "E2EFDA",
    }

    for row_idx, log in enumerate(logs, start=3):
        data = _row(log)
        row_fill = PatternFill("solid", fgColor=status_colors.get(log.status, "FFFFFF"))
        for col_idx, value in enumerate(data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.fill = row_fill

    # Column widths
    col_widths = [6, 20, 28, 22, 28, 28, 20, 20, 20, 16]
    for col, width in enumerate(col_widths, start=1):
        ws.column_dimensions[ws.cell(row=2, column=col).column_letter].width = width

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
