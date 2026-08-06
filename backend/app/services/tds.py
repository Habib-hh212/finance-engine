"""India TDS (Tax Deducted at Source): the payer deducts tax at a
prescribed rate when booking certain vendor expenses (professional fees,
contractor payments, rent...) and remits it to the government instead of
paying it to the vendor. Deduction happens at bill posting time here (the
common case for most sections) -- see create_vendor_bill in
receivables_payables.py, which routes the deducted amount to whichever
G/L account is tagged forecast_role="tds_payable", the same tagging
convention AR/AP/cash already use."""
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models import TdsSection, Vendor, VendorBill


def tds_amount(tds_section: TdsSection, net_amount: float) -> float:
    return round(net_amount * float(tds_section.rate_pct) / 100, 2)


@dataclass
class TdsSectionSummaryRow:
    tds_section_id: object
    section_code: str
    description: str
    rate_pct: float
    gross_amount: float
    tds_amount: float


@dataclass
class TdsDeducteeSummaryRow:
    vendor_id: object
    vendor_name: str
    gross_amount: float
    tds_amount: float


@dataclass
class TdsSummaryResult:
    section_rows: list
    deductee_rows: list
    total_tds: float


def tds_summary(db: Session, company_id, start: date, end: date) -> TdsSummaryResult:
    bills = (
        db.query(VendorBill)
        .filter(
            VendorBill.company_id == company_id,
            VendorBill.tds_section_id.isnot(None),
            VendorBill.bill_date >= start,
            VendorBill.bill_date <= end,
        )
        .all()
    )

    sections = {s.id: s for s in db.query(TdsSection).filter(TdsSection.company_id == company_id).all()}
    vendors = {v.id: v for v in db.query(Vendor).filter(Vendor.company_id == company_id).all()}

    by_section: dict = {}
    by_vendor: dict = {}
    total_tds = 0.0

    for bill in bills:
        deducted = float(bill.tds_amount or 0.0)
        gross = float(bill.amount)
        total_tds += deducted

        section = sections.get(bill.tds_section_id)
        if section is not None:
            agg = by_section.setdefault(section.id, {"gross": 0.0, "tds": 0.0})
            agg["gross"] += gross
            agg["tds"] += deducted

        vendor = vendors.get(bill.vendor_id)
        if vendor is not None:
            agg = by_vendor.setdefault(vendor.id, {"gross": 0.0, "tds": 0.0})
            agg["gross"] += gross
            agg["tds"] += deducted

    section_rows = [
        TdsSectionSummaryRow(
            tds_section_id=section_id,
            section_code=sections[section_id].section_code,
            description=sections[section_id].description,
            rate_pct=float(sections[section_id].rate_pct),
            gross_amount=round(agg["gross"], 2),
            tds_amount=round(agg["tds"], 2),
        )
        for section_id, agg in by_section.items()
    ]
    section_rows.sort(key=lambda r: r.section_code)

    deductee_rows = [
        TdsDeducteeSummaryRow(
            vendor_id=vendor_id,
            vendor_name=vendors[vendor_id].name,
            gross_amount=round(agg["gross"], 2),
            tds_amount=round(agg["tds"], 2),
        )
        for vendor_id, agg in by_vendor.items()
    ]
    deductee_rows.sort(key=lambda r: r.vendor_name)

    return TdsSummaryResult(section_rows=section_rows, deductee_rows=deductee_rows, total_tds=round(total_tds, 2))
