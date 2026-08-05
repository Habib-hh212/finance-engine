"""VAT/GST return: sums the actual tax G/L postings a journal entry's tax
code auto-generated (see app/services/bookkeeping.py apply_tax_code), the
same way a real tax return is built off the tax account's activity rather
than off a hypothetical calculation."""
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models import JournalEntry, JournalEntryLine, TaxCode
from app.models.journal_entry import JournalEntryStatus
from app.models.tax_code import TaxDirection


@dataclass
class TaxReportRow:
    tax_code_id: object
    code: str
    name: str
    country: str
    tax_type: str
    direction: str
    rate_pct: float
    taxable_base: float
    tax_amount: float


@dataclass
class TaxReportResult:
    rows: list
    total_output_tax: float
    total_input_tax: float
    net_tax_payable: float


def tax_report(db: Session, company_id, start: date, end: date) -> TaxReportResult:
    tax_codes = {tc.id: tc for tc in db.query(TaxCode).filter(TaxCode.company_id == company_id).all()}

    entries = (
        db.query(JournalEntry)
        .filter(
            JournalEntry.company_id == company_id,
            JournalEntry.status == JournalEntryStatus.POSTED,
            JournalEntry.entry_date >= start,
            JournalEntry.entry_date <= end,
        )
        .all()
    )
    entry_ids = [e.id for e in entries]

    totals: dict = {}
    if entry_ids:
        lines = (
            db.query(JournalEntryLine)
            .filter(JournalEntryLine.journal_entry_id.in_(entry_ids), JournalEntryLine.tax_code_id.isnot(None))
            .all()
        )
        for line in lines:
            if line.tax_code_id not in tax_codes:
                continue
            totals[line.tax_code_id] = totals.get(line.tax_code_id, 0.0) + float(line.tax_amount or 0.0)

    rows = []
    total_output = 0.0
    total_input = 0.0
    for tax_code_id, tax_amount in totals.items():
        tax_code = tax_codes[tax_code_id]
        rate = float(tax_code.rate_pct)
        taxable_base = round(tax_amount / (rate / 100), 2) if rate else 0.0
        rows.append(
            TaxReportRow(
                tax_code_id=tax_code_id,
                code=tax_code.code,
                name=tax_code.name,
                country=tax_code.country,
                tax_type=tax_code.tax_type,
                direction=tax_code.direction,
                rate_pct=rate,
                taxable_base=taxable_base,
                tax_amount=round(tax_amount, 2),
            )
        )
        if tax_code.direction == TaxDirection.OUTPUT:
            total_output += tax_amount
        else:
            total_input += tax_amount

    rows.sort(key=lambda r: (r.country, r.code))
    return TaxReportResult(
        rows=rows,
        total_output_tax=round(total_output, 2),
        total_input_tax=round(total_input, 2),
        net_tax_payable=round(total_output - total_input, 2),
    )
