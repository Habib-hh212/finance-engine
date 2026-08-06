"""Payslip and Form 16 PDFs -- reuses the same reportlab table styling as
report_generation.py's board report so every generated document in this
app looks like it comes from the same system."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models import Company, Employee, Payslip
from app.services.payroll import Form16Summary

BRAND_COLOR = "#2f5d50"

MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def _fmt(value: float) -> str:
    return f"{value:,.2f}"


def _pdf_table(rows: list[list[str]], col_widths=None) -> Table:
    table = Table(rows, colWidths=col_widths or [3.5 * inch, 2.5 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND_COLOR)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d0d0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f6f4")]),
            ]
        )
    )
    return table


def render_payslip_pdf(company: Company, employee: Employee, payslip: Payslip, period_month: int, period_year: int) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("PayslipTitle", parent=styles["Title"], textColor=colors.HexColor(BRAND_COLOR))
    heading_style = ParagraphStyle("PayslipHeading", parent=styles["Heading2"], textColor=colors.HexColor(BRAND_COLOR), spaceBefore=18)
    currency = company.base_currency if company else "USD"

    earnings_rows = [
        ["Earnings", "Amount"],
        ["Basic", _fmt(float(payslip.basic))],
        ["HRA", _fmt(float(payslip.hra))],
        ["Special Allowance", _fmt(float(payslip.special_allowance))],
        ["Other Allowance", _fmt(float(payslip.other_allowance))],
        ["Gross Pay", _fmt(float(payslip.gross_pay))],
    ]
    deduction_rows = [
        ["Deductions", "Amount"],
        ["Provident Fund (employee)", _fmt(float(payslip.pf_employee))],
        ["ESI (employee)", _fmt(float(payslip.esi_employee))],
        ["Professional Tax", _fmt(float(payslip.professional_tax))],
        ["TDS (Section 192)", _fmt(float(payslip.tds_amount))],
        ["Net Pay", _fmt(float(payslip.net_pay))],
    ]

    elements = [
        Paragraph(f"{company.name if company else 'Company'} — Payslip", title_style),
        Paragraph(
            f"{employee.name} &middot; PAN {employee.pan or '—'} &middot; {MONTH_NAMES[period_month]} {period_year} &middot; {currency}",
            styles["Normal"],
        ),
        Spacer(1, 16),
        Paragraph("Earnings", heading_style),
        _pdf_table(earnings_rows),
        Paragraph("Deductions", heading_style),
        _pdf_table(deduction_rows),
    ]
    doc.build(elements)
    return buffer.getvalue()


def render_form16_pdf(company: Company, summary: Form16Summary) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Form16Title", parent=styles["Title"], textColor=colors.HexColor(BRAND_COLOR))
    heading_style = ParagraphStyle("Form16Heading", parent=styles["Heading2"], textColor=colors.HexColor(BRAND_COLOR), spaceBefore=18)
    currency = company.base_currency if company else "USD"

    summary_rows = [
        ["Summary", "Amount"],
        ["Tax regime", "Old regime" if summary.regime == "old" else "New regime"],
        ["Total gross salary paid", _fmt(summary.total_gross)],
        ["Total tax deducted at source", _fmt(summary.total_tds)],
    ]
    month_rows = [["Month", "Gross Pay", "TDS Deducted"]] + [
        [f"{MONTH_NAMES[m.period_month]} {m.period_year}", _fmt(m.gross_pay), _fmt(m.tds_amount)] for m in summary.months
    ]

    elements = [
        Paragraph(f"{company.name if company else 'Company'} — Form 16 (Part B summary)", title_style),
        Paragraph(
            f"{summary.employee.name} &middot; PAN {summary.employee.pan or '—'} &middot; FY {summary.financial_year}-{str(summary.financial_year + 1)[-2:]} &middot; {currency}",
            styles["Normal"],
        ),
        Spacer(1, 16),
        Paragraph("Summary", heading_style),
        _pdf_table(summary_rows),
        Paragraph("Month-wise TDS Deducted", heading_style),
        _pdf_table(month_rows, col_widths=[2.5 * inch, 1.75 * inch, 1.75 * inch]) if month_rows[1:] else Paragraph("No payroll runs found for this financial year.", styles["Normal"]),
    ]
    doc.build(elements)
    return buffer.getvalue()
