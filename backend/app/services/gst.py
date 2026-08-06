"""India GST: unlike a flat VAT rate, a GST rate splits into CGST + SGST
(intra-state) or IGST alone (inter-state), decided by comparing the
transaction's place of supply against the company's registered state.
For a sale, place of supply is the customer's state; for a purchase, the
vendor's state. Two blank/differing states are treated as inter-state
(the conservative default -- IGST) since a confident intra-state
determination requires both sides to actually have a state on file."""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Customer, CustomerInvoice, GLAccount, GstRate, VendorBill


def is_intra_state(company_state: Optional[str], counterparty_state: Optional[str]) -> bool:
    if not company_state or not counterparty_state:
        return False
    return company_state.strip().casefold() == counterparty_state.strip().casefold()


@dataclass
class GstSplit:
    cgst_amount: float
    sgst_amount: float
    igst_amount: float

    @property
    def total(self) -> float:
        return round(self.cgst_amount + self.sgst_amount + self.igst_amount, 2)


def _taxable_value(rate_pct: float, cgst: float, sgst: float, igst: float) -> float:
    # Derived from the tax itself rather than backed out of the document's
    # stored `amount`, since `amount` on a VendorBill is net of any TDS
    # withheld too -- a separate, unrelated deduction that would otherwise
    # throw this off.
    total_tax = cgst + sgst + igst
    return round(total_tax / (rate_pct / 100), 2) if rate_pct else 0.0


def split_gst(gst_rate: GstRate, net_amount: float, intra_state: bool) -> GstSplit:
    total_tax = round(net_amount * float(gst_rate.rate_pct) / 100, 2)
    if intra_state:
        half = round(total_tax / 2, 2)
        # Put any odd paisa from rounding on SGST rather than losing it,
        # so cgst_amount + sgst_amount always reconciles to total_tax.
        return GstSplit(cgst_amount=half, sgst_amount=round(total_tax - half, 2), igst_amount=0.0)
    return GstSplit(cgst_amount=0.0, sgst_amount=0.0, igst_amount=total_tax)


# --- GSTR-1 (outward supplies) ----------------------------------------------


@dataclass
class Gstr1B2BRow:
    invoice_id: object
    invoice_number: str
    invoice_date: date
    customer_name: str
    customer_gstin: str
    taxable_value: float
    rate_pct: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    invoice_value: float


@dataclass
class Gstr1B2CRow:
    place_of_supply: str
    rate_pct: float
    taxable_value: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float


@dataclass
class Gstr1HsnRow:
    hsn_sac_code: str
    taxable_value: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float


@dataclass
class Gstr1Result:
    b2b_rows: list
    b2c_rows: list
    hsn_rows: list
    total_taxable_value: float
    total_tax: float


def gstr1_report(db: Session, company_id, start: date, end: date) -> Gstr1Result:
    invoices = (
        db.query(CustomerInvoice)
        .filter(
            CustomerInvoice.company_id == company_id,
            CustomerInvoice.gst_rate_id.isnot(None),
            CustomerInvoice.invoice_date >= start,
            CustomerInvoice.invoice_date <= end,
        )
        .all()
    )
    customers = {c.id: c for c in db.query(Customer).filter(Customer.company_id == company_id).all()}
    gl_accounts = {g.id: g for g in db.query(GLAccount).filter(GLAccount.company_id == company_id).all()}
    gst_rates = {r.id: r for r in db.query(GstRate).filter(GstRate.company_id == company_id).all()}

    b2b_rows = []
    b2c_agg: dict = {}
    hsn_agg: dict = {}
    total_taxable = 0.0
    total_tax = 0.0

    for inv in invoices:
        customer = customers.get(inv.customer_id)
        rate = gst_rates.get(inv.gst_rate_id)
        cgst, sgst, igst = float(inv.cgst_amount or 0.0), float(inv.sgst_amount or 0.0), float(inv.igst_amount or 0.0)
        taxable_value = _taxable_value(float(rate.rate_pct) if rate else 0.0, cgst, sgst, igst)
        total_taxable += taxable_value
        total_tax += cgst + sgst + igst

        if customer is not None and customer.gstin:
            b2b_rows.append(
                Gstr1B2BRow(
                    invoice_id=inv.id,
                    invoice_number=inv.invoice_number,
                    invoice_date=inv.invoice_date,
                    customer_name=customer.name,
                    customer_gstin=customer.gstin,
                    taxable_value=taxable_value,
                    rate_pct=float(rate.rate_pct) if rate else 0.0,
                    cgst_amount=cgst,
                    sgst_amount=sgst,
                    igst_amount=igst,
                    invoice_value=float(inv.amount),
                )
            )
        else:
            place = (customer.state if customer and customer.state else "Unknown").strip()
            key = (place, float(rate.rate_pct) if rate else 0.0)
            agg = b2c_agg.setdefault(key, {"taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0})
            agg["taxable"] += taxable_value
            agg["cgst"] += cgst
            agg["sgst"] += sgst
            agg["igst"] += igst

        account = gl_accounts.get(inv.revenue_gl_account_id)
        hsn = account.hsn_sac_code if account and account.hsn_sac_code else "Unclassified"
        agg = hsn_agg.setdefault(hsn, {"taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0})
        agg["taxable"] += taxable_value
        agg["cgst"] += cgst
        agg["sgst"] += sgst
        agg["igst"] += igst

    b2b_rows.sort(key=lambda r: r.invoice_date)
    b2c_rows = [
        Gstr1B2CRow(
            place_of_supply=place,
            rate_pct=rate_pct,
            taxable_value=round(agg["taxable"], 2),
            cgst_amount=round(agg["cgst"], 2),
            sgst_amount=round(agg["sgst"], 2),
            igst_amount=round(agg["igst"], 2),
        )
        for (place, rate_pct), agg in b2c_agg.items()
    ]
    b2c_rows.sort(key=lambda r: (r.place_of_supply, r.rate_pct))
    hsn_rows = [
        Gstr1HsnRow(
            hsn_sac_code=hsn,
            taxable_value=round(agg["taxable"], 2),
            cgst_amount=round(agg["cgst"], 2),
            sgst_amount=round(agg["sgst"], 2),
            igst_amount=round(agg["igst"], 2),
        )
        for hsn, agg in hsn_agg.items()
    ]
    hsn_rows.sort(key=lambda r: r.hsn_sac_code)

    return Gstr1Result(
        b2b_rows=b2b_rows,
        b2c_rows=b2c_rows,
        hsn_rows=hsn_rows,
        total_taxable_value=round(total_taxable, 2),
        total_tax=round(total_tax, 2),
    )


# --- GSTR-3B (summary return) ------------------------------------------------


@dataclass
class Gstr3bResult:
    outward_taxable_value: float
    output_cgst: float
    output_sgst: float
    output_igst: float
    inward_taxable_value: float
    input_cgst: float
    input_sgst: float
    input_igst: float
    net_cgst_payable: float
    net_sgst_payable: float
    net_igst_payable: float
    net_tax_payable: float


def gstr3b_report(db: Session, company_id, start: date, end: date) -> Gstr3bResult:
    invoices = (
        db.query(CustomerInvoice)
        .filter(
            CustomerInvoice.company_id == company_id,
            CustomerInvoice.gst_rate_id.isnot(None),
            CustomerInvoice.invoice_date >= start,
            CustomerInvoice.invoice_date <= end,
        )
        .all()
    )
    bills = (
        db.query(VendorBill)
        .filter(
            VendorBill.company_id == company_id,
            VendorBill.gst_rate_id.isnot(None),
            VendorBill.bill_date >= start,
            VendorBill.bill_date <= end,
        )
        .all()
    )

    gst_rates = {r.id: r for r in db.query(GstRate).filter(GstRate.company_id == company_id).all()}

    output_cgst = sum(float(i.cgst_amount or 0.0) for i in invoices)
    output_sgst = sum(float(i.sgst_amount or 0.0) for i in invoices)
    output_igst = sum(float(i.igst_amount or 0.0) for i in invoices)
    outward_taxable_value = sum(
        _taxable_value(
            float(gst_rates[i.gst_rate_id].rate_pct) if i.gst_rate_id in gst_rates else 0.0,
            float(i.cgst_amount or 0.0),
            float(i.sgst_amount or 0.0),
            float(i.igst_amount or 0.0),
        )
        for i in invoices
    )

    input_cgst = sum(float(b.cgst_amount or 0.0) for b in bills)
    input_sgst = sum(float(b.sgst_amount or 0.0) for b in bills)
    input_igst = sum(float(b.igst_amount or 0.0) for b in bills)
    inward_taxable_value = sum(
        _taxable_value(
            float(gst_rates[b.gst_rate_id].rate_pct) if b.gst_rate_id in gst_rates else 0.0,
            float(b.cgst_amount or 0.0),
            float(b.sgst_amount or 0.0),
            float(b.igst_amount or 0.0),
        )
        for b in bills
    )

    net_cgst = round(output_cgst - input_cgst, 2)
    net_sgst = round(output_sgst - input_sgst, 2)
    net_igst = round(output_igst - input_igst, 2)

    return Gstr3bResult(
        outward_taxable_value=round(outward_taxable_value, 2),
        output_cgst=round(output_cgst, 2),
        output_sgst=round(output_sgst, 2),
        output_igst=round(output_igst, 2),
        inward_taxable_value=round(inward_taxable_value, 2),
        input_cgst=round(input_cgst, 2),
        input_sgst=round(input_sgst, 2),
        input_igst=round(input_igst, 2),
        net_cgst_payable=net_cgst,
        net_sgst_payable=net_sgst,
        net_igst_payable=net_igst,
        net_tax_payable=round(net_cgst + net_sgst + net_igst, 2),
    )
