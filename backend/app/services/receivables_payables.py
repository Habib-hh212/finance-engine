"""AR/AP: customer invoices and vendor bills post real journal entries
(reusing the tax-code engine from bookkeeping.py directly), and every
receipt or payment posts against whichever G/L account is tagged
forecast_role="accounts_receivable" / "accounts_payable" on this company's
Chart of Accounts -- the same tagging convention the Balance Sheet
forecast and Cash Flow Statement already rely on, so there is exactly one
place a company designates its AR/AP control account, not one per
transaction. See app/models/receivables_payables.py for why down payments
don't need a separate G/L account.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    Customer,
    CustomerInvoice,
    CustomerReceipt,
    CustomerReceiptApplication,
    GLAccount,
    TaxCode,
    TdsSection,
    Vendor,
    VendorBill,
    VendorPayment,
    VendorPaymentApplication,
)
from app.models.receivables_payables import InvoiceStatus
from app.services import bookkeeping
from app.services import tds as tds_service

TOLERANCE = 0.01


class ARAPError(ValueError):
    """Raised when an AR/AP transaction violates a rule."""


def _control_account(db: Session, company_id, forecast_role: str, label: str) -> GLAccount:
    account = db.query(GLAccount).filter(GLAccount.company_id == company_id, GLAccount.forecast_role == forecast_role).first()
    if account is None:
        raise ARAPError(f"No G/L account is tagged as {label} for this company -- tag one on the Chart of Accounts page.")
    return account


def _tax_amount(tax_code: Optional[TaxCode], net_amount: float) -> float:
    if tax_code is None:
        return 0.0
    return round(net_amount * float(tax_code.rate_pct) / 100, 2)


# --- Customer invoices / receipts (AR) -----------------------------------


def create_customer_invoice(
    db: Session,
    company_id,
    customer_id,
    invoice_number: str,
    invoice_date: date,
    due_date: date,
    revenue_gl_account_id,
    net_amount: float,
    tax_code_id=None,
    currency: str = "USD",
) -> CustomerInvoice:
    if net_amount <= 0:
        raise ARAPError("Invoice amount must be positive.")
    customer = db.get(Customer, customer_id)
    if customer is None or customer.company_id != company_id:
        raise ARAPError("Customer not found in this company.")
    ar_account = _control_account(db, company_id, "accounts_receivable", "Accounts Receivable")

    tax_code = None
    if tax_code_id is not None:
        tax_code = db.get(TaxCode, tax_code_id)
        if tax_code is None or tax_code.company_id != company_id:
            raise ARAPError("Tax code doesn't belong to this company.")
    gross_amount = round(net_amount + _tax_amount(tax_code, net_amount), 2)

    entry = bookkeeping.create_journal_entry(
        db,
        company_id,
        invoice_date,
        [
            bookkeeping.LineInput(gl_account_id=ar_account.id, debit_amount=gross_amount),
            bookkeeping.LineInput(gl_account_id=revenue_gl_account_id, credit_amount=net_amount, tax_code_id=tax_code_id),
        ],
        reference=f"Invoice {invoice_number}",
        description=f"Invoice {invoice_number} to {customer.name}",
        currency=currency,
    )
    entry = bookkeeping.post_journal_entry(db, entry)

    invoice = CustomerInvoice(
        company_id=company_id,
        customer_id=customer_id,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        due_date=due_date,
        revenue_gl_account_id=revenue_gl_account_id,
        tax_code_id=tax_code_id,
        amount=gross_amount,
        currency=currency,
        status=InvoiceStatus.OPEN,
        journal_entry_id=entry.id,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def create_customer_receipt(
    db: Session, company_id, customer_id, receipt_date: date, cash_gl_account_id, amount: float, reference: Optional[str] = None
) -> CustomerReceipt:
    if amount <= 0:
        raise ARAPError("Receipt amount must be positive.")
    customer = db.get(Customer, customer_id)
    if customer is None or customer.company_id != company_id:
        raise ARAPError("Customer not found in this company.")
    ar_account = _control_account(db, company_id, "accounts_receivable", "Accounts Receivable")

    entry = bookkeeping.create_journal_entry(
        db,
        company_id,
        receipt_date,
        [
            bookkeeping.LineInput(gl_account_id=cash_gl_account_id, debit_amount=amount),
            bookkeeping.LineInput(gl_account_id=ar_account.id, credit_amount=amount),
        ],
        reference=reference or f"Receipt from {customer.name}",
        description=f"Receipt from {customer.name}",
        currency="USD",
    )
    entry = bookkeeping.post_journal_entry(db, entry)

    receipt = CustomerReceipt(
        company_id=company_id, customer_id=customer_id, receipt_date=receipt_date, cash_gl_account_id=cash_gl_account_id, amount=amount, reference=reference, journal_entry_id=entry.id
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt


def receipt_unapplied_balance(db: Session, receipt: CustomerReceipt) -> float:
    applied = sum(
        float(a.amount) for a in db.query(CustomerReceiptApplication).filter(CustomerReceiptApplication.receipt_id == receipt.id).all()
    )
    return round(float(receipt.amount) - applied, 2)


def invoice_remaining_balance(db: Session, invoice: CustomerInvoice) -> float:
    applied = sum(
        float(a.amount) for a in db.query(CustomerReceiptApplication).filter(CustomerReceiptApplication.invoice_id == invoice.id).all()
    )
    return round(float(invoice.amount) - applied, 2)


def apply_receipt_to_invoice(db: Session, receipt: CustomerReceipt, invoice: CustomerInvoice, amount: float, applied_date: date) -> CustomerReceiptApplication:
    if receipt.customer_id != invoice.customer_id:
        raise ARAPError("This receipt and invoice belong to different customers.")
    if invoice.status == InvoiceStatus.VOID:
        raise ARAPError("Can't apply a receipt to a void invoice.")
    if amount <= 0:
        raise ARAPError("Applied amount must be positive.")
    unapplied = receipt_unapplied_balance(db, receipt)
    if amount > unapplied + TOLERANCE:
        raise ARAPError(f"Only {unapplied:.2f} of this receipt is unapplied.")
    remaining = invoice_remaining_balance(db, invoice)
    if amount > remaining + TOLERANCE:
        raise ARAPError(f"Only {remaining:.2f} remains on this invoice.")

    application = CustomerReceiptApplication(receipt_id=receipt.id, invoice_id=invoice.id, amount=amount, applied_date=applied_date)
    db.add(application)
    db.flush()

    new_remaining = invoice_remaining_balance(db, invoice)
    invoice.status = InvoiceStatus.PAID if new_remaining <= TOLERANCE else InvoiceStatus.PARTIALLY_PAID
    db.commit()
    db.refresh(application)
    return application


# --- Vendor bills / payments (AP) -----------------------------------------


def create_vendor_bill(
    db: Session,
    company_id,
    vendor_id,
    bill_number: str,
    bill_date: date,
    due_date: date,
    expense_gl_account_id,
    net_amount: float,
    tax_code_id=None,
    tds_section_id=None,
    currency: str = "USD",
) -> VendorBill:
    if net_amount <= 0:
        raise ARAPError("Bill amount must be positive.")
    vendor = db.get(Vendor, vendor_id)
    if vendor is None or vendor.company_id != company_id:
        raise ARAPError("Vendor not found in this company.")
    ap_account = _control_account(db, company_id, "accounts_payable", "Accounts Payable")

    tax_code = None
    if tax_code_id is not None:
        tax_code = db.get(TaxCode, tax_code_id)
        if tax_code is None or tax_code.company_id != company_id:
            raise ARAPError("Tax code doesn't belong to this company.")
    gross_amount = round(net_amount + _tax_amount(tax_code, net_amount), 2)

    tds_section = None
    tds_deducted = 0.0
    if tds_section_id is not None:
        tds_section = db.get(TdsSection, tds_section_id)
        if tds_section is None or tds_section.company_id != company_id:
            raise ARAPError("TDS section doesn't belong to this company.")
        tds_deducted = tds_service.tds_amount(tds_section, net_amount)

    # TDS reduces what's actually owed to the vendor, not the expense
    # booked -- the deducted amount moves to a TDS payable liability
    # (remitted to the government) instead of the vendor's payable.
    payable_amount = round(gross_amount - tds_deducted, 2)

    lines = [bookkeeping.LineInput(gl_account_id=expense_gl_account_id, debit_amount=net_amount, tax_code_id=tax_code_id)]
    if tds_deducted > 0:
        tds_account = _control_account(db, company_id, "tds_payable", "TDS Payable")
        lines.append(bookkeeping.LineInput(gl_account_id=tds_account.id, credit_amount=tds_deducted))
    lines.append(bookkeeping.LineInput(gl_account_id=ap_account.id, credit_amount=payable_amount))

    entry = bookkeeping.create_journal_entry(
        db,
        company_id,
        bill_date,
        lines,
        reference=f"Bill {bill_number}",
        description=f"Bill {bill_number} from {vendor.name}",
        currency=currency,
    )
    entry = bookkeeping.post_journal_entry(db, entry)

    bill = VendorBill(
        company_id=company_id,
        vendor_id=vendor_id,
        bill_number=bill_number,
        bill_date=bill_date,
        due_date=due_date,
        expense_gl_account_id=expense_gl_account_id,
        tax_code_id=tax_code_id,
        tds_section_id=tds_section_id,
        tds_amount=tds_deducted,
        amount=payable_amount,
        currency=currency,
        status=InvoiceStatus.OPEN,
        journal_entry_id=entry.id,
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


def create_vendor_payment(
    db: Session, company_id, vendor_id, payment_date: date, cash_gl_account_id, amount: float, reference: Optional[str] = None
) -> VendorPayment:
    if amount <= 0:
        raise ARAPError("Payment amount must be positive.")
    vendor = db.get(Vendor, vendor_id)
    if vendor is None or vendor.company_id != company_id:
        raise ARAPError("Vendor not found in this company.")
    ap_account = _control_account(db, company_id, "accounts_payable", "Accounts Payable")

    entry = bookkeeping.create_journal_entry(
        db,
        company_id,
        payment_date,
        [
            bookkeeping.LineInput(gl_account_id=ap_account.id, debit_amount=amount),
            bookkeeping.LineInput(gl_account_id=cash_gl_account_id, credit_amount=amount),
        ],
        reference=reference or f"Payment to {vendor.name}",
        description=f"Payment to {vendor.name}",
        currency="USD",
    )
    entry = bookkeeping.post_journal_entry(db, entry)

    payment = VendorPayment(
        company_id=company_id, vendor_id=vendor_id, payment_date=payment_date, cash_gl_account_id=cash_gl_account_id, amount=amount, reference=reference, journal_entry_id=entry.id
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def payment_unapplied_balance(db: Session, payment: VendorPayment) -> float:
    applied = sum(
        float(a.amount) for a in db.query(VendorPaymentApplication).filter(VendorPaymentApplication.payment_id == payment.id).all()
    )
    return round(float(payment.amount) - applied, 2)


def bill_remaining_balance(db: Session, bill: VendorBill) -> float:
    applied = sum(float(a.amount) for a in db.query(VendorPaymentApplication).filter(VendorPaymentApplication.bill_id == bill.id).all())
    return round(float(bill.amount) - applied, 2)


def apply_payment_to_bill(db: Session, payment: VendorPayment, bill: VendorBill, amount: float, applied_date: date) -> VendorPaymentApplication:
    if payment.vendor_id != bill.vendor_id:
        raise ARAPError("This payment and bill belong to different vendors.")
    if bill.status == InvoiceStatus.VOID:
        raise ARAPError("Can't apply a payment to a void bill.")
    if amount <= 0:
        raise ARAPError("Applied amount must be positive.")
    unapplied = payment_unapplied_balance(db, payment)
    if amount > unapplied + TOLERANCE:
        raise ARAPError(f"Only {unapplied:.2f} of this payment is unapplied.")
    remaining = bill_remaining_balance(db, bill)
    if amount > remaining + TOLERANCE:
        raise ARAPError(f"Only {remaining:.2f} remains on this bill.")

    application = VendorPaymentApplication(payment_id=payment.id, bill_id=bill.id, amount=amount, applied_date=applied_date)
    db.add(application)
    db.flush()

    new_remaining = bill_remaining_balance(db, bill)
    bill.status = InvoiceStatus.PAID if new_remaining <= TOLERANCE else InvoiceStatus.PARTIALLY_PAID
    db.commit()
    db.refresh(application)
    return application


# --- Aging ------------------------------------------------------------------


def _bucket(days_overdue: int) -> str:
    if days_overdue <= 0:
        return "current"
    if days_overdue <= 30:
        return "1-30"
    if days_overdue <= 60:
        return "31-60"
    if days_overdue <= 90:
        return "61-90"
    return "90+"


@dataclass
class AgingRow:
    party_id: object
    party_name: str
    document_id: object
    number: str
    due_date: date
    days_overdue: int
    remaining_balance: float
    bucket: str


def ar_aging(db: Session, company_id, as_of: date) -> list:
    customers = {c.id: c for c in db.query(Customer).filter(Customer.company_id == company_id).all()}
    rows = []
    for invoice in db.query(CustomerInvoice).filter(CustomerInvoice.company_id == company_id, CustomerInvoice.status != InvoiceStatus.VOID).all():
        remaining = invoice_remaining_balance(db, invoice)
        if remaining <= TOLERANCE:
            continue
        days_overdue = (as_of - invoice.due_date).days
        rows.append(
            AgingRow(
                party_id=invoice.customer_id,
                party_name=customers[invoice.customer_id].name if invoice.customer_id in customers else "?",
                document_id=invoice.id,
                number=invoice.invoice_number,
                due_date=invoice.due_date,
                days_overdue=days_overdue,
                remaining_balance=remaining,
                bucket=_bucket(days_overdue),
            )
        )
    return sorted(rows, key=lambda r: (r.party_name, r.due_date))


def ap_aging(db: Session, company_id, as_of: date) -> list:
    vendors = {v.id: v for v in db.query(Vendor).filter(Vendor.company_id == company_id).all()}
    rows = []
    for bill in db.query(VendorBill).filter(VendorBill.company_id == company_id, VendorBill.status != InvoiceStatus.VOID).all():
        remaining = bill_remaining_balance(db, bill)
        if remaining <= TOLERANCE:
            continue
        days_overdue = (as_of - bill.due_date).days
        rows.append(
            AgingRow(
                party_id=bill.vendor_id,
                party_name=vendors[bill.vendor_id].name if bill.vendor_id in vendors else "?",
                document_id=bill.id,
                number=bill.bill_number,
                due_date=bill.due_date,
                days_overdue=days_overdue,
                remaining_balance=remaining,
                bucket=_bucket(days_overdue),
            )
        )
    return sorted(rows, key=lambda r: (r.party_name, r.due_date))
