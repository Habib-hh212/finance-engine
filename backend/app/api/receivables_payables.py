import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_company_access
from app.database import get_db
from app.models import (
    Customer,
    CustomerInvoice,
    CustomerReceipt,
    User,
    Vendor,
    VendorBill,
    VendorPayment,
)
from app.schemas.receivables_payables import (
    AgingReportOut,
    AgingRowOut,
    ApplyPaymentIn,
    ApplyReceiptIn,
    CustomerCreate,
    CustomerInvoiceCreate,
    CustomerInvoiceOut,
    CustomerOut,
    CustomerReceiptCreate,
    CustomerReceiptOut,
    VendorBillCreate,
    VendorBillOut,
    VendorCreate,
    VendorOut,
    VendorPaymentCreate,
    VendorPaymentOut,
)
from app.services import audit
from app.services import receivables_payables as arap

router = APIRouter(tags=["receivables-payables"])


def _get_or_404(db: Session, model, company_id: uuid.UUID, obj_id: uuid.UUID, label: str):
    obj = db.get(model, obj_id)
    if obj is None or obj.company_id != company_id:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return obj


@router.post("/vendors", response_model=VendorOut)
def create_vendor(payload: VendorCreate, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    vendor = Vendor(company_id=company_id, name=payload.name)
    db.add(vendor)
    db.flush()
    audit.record(db, company_id, "vendor", vendor.id, "create", current_user, f"Created vendor {vendor.name}")
    db.commit()
    db.refresh(vendor)
    return VendorOut(id=vendor.id, name=vendor.name)


@router.get("/vendors", response_model=list[VendorOut])
def list_vendors(company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    vendors = db.query(Vendor).filter(Vendor.company_id == company_id).order_by(Vendor.name).all()
    return [VendorOut(id=v.id, name=v.name) for v in vendors]


@router.post("/customers", response_model=CustomerOut)
def create_customer(payload: CustomerCreate, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    customer = Customer(company_id=company_id, name=payload.name)
    db.add(customer)
    db.flush()
    audit.record(db, company_id, "customer", customer.id, "create", current_user, f"Created customer {customer.name}")
    db.commit()
    db.refresh(customer)
    return CustomerOut(id=customer.id, name=customer.name)


@router.get("/customers", response_model=list[CustomerOut])
def list_customers(company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    customers = db.query(Customer).filter(Customer.company_id == company_id).order_by(Customer.name).all()
    return [CustomerOut(id=c.id, name=c.name) for c in customers]


# --- Customer invoices / receipts -----------------------------------------


def _invoice_out(db: Session, invoice: CustomerInvoice) -> CustomerInvoiceOut:
    customer = db.get(Customer, invoice.customer_id)
    return CustomerInvoiceOut(
        id=invoice.id,
        customer_id=invoice.customer_id,
        customer_name=customer.name if customer else "?",
        invoice_number=invoice.invoice_number,
        invoice_date=invoice.invoice_date,
        due_date=invoice.due_date,
        revenue_gl_account_id=invoice.revenue_gl_account_id,
        tax_code_id=invoice.tax_code_id,
        amount=float(invoice.amount),
        currency=invoice.currency,
        status=invoice.status,
        remaining_balance=arap.invoice_remaining_balance(db, invoice),
        journal_entry_id=invoice.journal_entry_id,
    )


@router.post("/customer-invoices", response_model=CustomerInvoiceOut)
def create_customer_invoice(payload: CustomerInvoiceCreate, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        invoice = arap.create_customer_invoice(db, company_id, **payload.model_dump())
    except arap.ARAPError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit.record(db, company_id, "customer_invoice", invoice.id, "create", current_user, f"Created invoice {invoice.invoice_number} for {invoice.amount}")
    db.commit()
    return _invoice_out(db, invoice)


@router.get("/customer-invoices", response_model=list[CustomerInvoiceOut])
def list_customer_invoices(company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    invoices = db.query(CustomerInvoice).filter(CustomerInvoice.company_id == company_id).order_by(CustomerInvoice.invoice_date.desc()).all()
    return [_invoice_out(db, i) for i in invoices]


def _receipt_out(db: Session, receipt: CustomerReceipt) -> CustomerReceiptOut:
    customer = db.get(Customer, receipt.customer_id)
    return CustomerReceiptOut(
        id=receipt.id,
        customer_id=receipt.customer_id,
        customer_name=customer.name if customer else "?",
        receipt_date=receipt.receipt_date,
        cash_gl_account_id=receipt.cash_gl_account_id,
        amount=float(receipt.amount),
        reference=receipt.reference,
        unapplied_balance=arap.receipt_unapplied_balance(db, receipt),
        journal_entry_id=receipt.journal_entry_id,
    )


@router.post("/customer-receipts", response_model=CustomerReceiptOut)
def create_customer_receipt(payload: CustomerReceiptCreate, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        receipt = arap.create_customer_receipt(db, company_id, **payload.model_dump())
    except arap.ARAPError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit.record(db, company_id, "customer_receipt", receipt.id, "create", current_user, f"Recorded receipt of {receipt.amount} from customer")
    db.commit()
    return _receipt_out(db, receipt)


@router.get("/customer-receipts", response_model=list[CustomerReceiptOut])
def list_customer_receipts(company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    receipts = db.query(CustomerReceipt).filter(CustomerReceipt.company_id == company_id).order_by(CustomerReceipt.receipt_date.desc()).all()
    return [_receipt_out(db, r) for r in receipts]


@router.post("/customer-receipts/apply", response_model=CustomerInvoiceOut)
def apply_customer_receipt(payload: ApplyReceiptIn, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    receipt = _get_or_404(db, CustomerReceipt, company_id, payload.receipt_id, "Receipt")
    invoice = _get_or_404(db, CustomerInvoice, company_id, payload.invoice_id, "Invoice")
    try:
        arap.apply_receipt_to_invoice(db, receipt, invoice, payload.amount, payload.applied_date)
    except arap.ARAPError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit.record(db, company_id, "customer_receipt", receipt.id, "apply", current_user, f"Applied {payload.amount} of receipt to invoice {invoice.invoice_number}")
    db.commit()
    return _invoice_out(db, invoice)


@router.get("/reports/ar-aging", response_model=AgingReportOut)
def get_ar_aging(company_id: uuid.UUID = Depends(require_company_access), as_of: date = Query(...), db: Session = Depends(get_db)):
    rows = arap.ar_aging(db, company_id, as_of)
    return AgingReportOut(as_of=as_of, rows=[AgingRowOut(**r.__dict__) for r in rows], total_remaining=round(sum(r.remaining_balance for r in rows), 2))


# --- Vendor bills / payments -----------------------------------------------


def _bill_out(db: Session, bill: VendorBill) -> VendorBillOut:
    vendor = db.get(Vendor, bill.vendor_id)
    return VendorBillOut(
        id=bill.id,
        vendor_id=bill.vendor_id,
        vendor_name=vendor.name if vendor else "?",
        bill_number=bill.bill_number,
        bill_date=bill.bill_date,
        due_date=bill.due_date,
        expense_gl_account_id=bill.expense_gl_account_id,
        tax_code_id=bill.tax_code_id,
        amount=float(bill.amount),
        currency=bill.currency,
        status=bill.status,
        remaining_balance=arap.bill_remaining_balance(db, bill),
        journal_entry_id=bill.journal_entry_id,
    )


@router.post("/vendor-bills", response_model=VendorBillOut)
def create_vendor_bill(payload: VendorBillCreate, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        bill = arap.create_vendor_bill(db, company_id, **payload.model_dump())
    except arap.ARAPError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit.record(db, company_id, "vendor_bill", bill.id, "create", current_user, f"Created bill {bill.bill_number} for {bill.amount}")
    db.commit()
    return _bill_out(db, bill)


@router.get("/vendor-bills", response_model=list[VendorBillOut])
def list_vendor_bills(company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    bills = db.query(VendorBill).filter(VendorBill.company_id == company_id).order_by(VendorBill.bill_date.desc()).all()
    return [_bill_out(db, b) for b in bills]


def _payment_out(db: Session, payment: VendorPayment) -> VendorPaymentOut:
    vendor = db.get(Vendor, payment.vendor_id)
    return VendorPaymentOut(
        id=payment.id,
        vendor_id=payment.vendor_id,
        vendor_name=vendor.name if vendor else "?",
        payment_date=payment.payment_date,
        cash_gl_account_id=payment.cash_gl_account_id,
        amount=float(payment.amount),
        reference=payment.reference,
        unapplied_balance=arap.payment_unapplied_balance(db, payment),
        journal_entry_id=payment.journal_entry_id,
    )


@router.post("/vendor-payments", response_model=VendorPaymentOut)
def create_vendor_payment(payload: VendorPaymentCreate, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        payment = arap.create_vendor_payment(db, company_id, **payload.model_dump())
    except arap.ARAPError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit.record(db, company_id, "vendor_payment", payment.id, "create", current_user, f"Recorded payment of {payment.amount} to vendor")
    db.commit()
    return _payment_out(db, payment)


@router.get("/vendor-payments", response_model=list[VendorPaymentOut])
def list_vendor_payments(company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db)):
    payments = db.query(VendorPayment).filter(VendorPayment.company_id == company_id).order_by(VendorPayment.payment_date.desc()).all()
    return [_payment_out(db, p) for p in payments]


@router.post("/vendor-payments/apply", response_model=VendorBillOut)
def apply_vendor_payment(payload: ApplyPaymentIn, company_id: uuid.UUID = Depends(require_company_access), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    payment = _get_or_404(db, VendorPayment, company_id, payload.payment_id, "Payment")
    bill = _get_or_404(db, VendorBill, company_id, payload.bill_id, "Bill")
    try:
        arap.apply_payment_to_bill(db, payment, bill, payload.amount, payload.applied_date)
    except arap.ARAPError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit.record(db, company_id, "vendor_payment", payment.id, "apply", current_user, f"Applied {payload.amount} of payment to bill {bill.bill_number}")
    db.commit()
    return _bill_out(db, bill)


@router.get("/reports/ap-aging", response_model=AgingReportOut)
def get_ap_aging(company_id: uuid.UUID = Depends(require_company_access), as_of: date = Query(...), db: Session = Depends(get_db)):
    rows = arap.ap_aging(db, company_id, as_of)
    return AgingReportOut(as_of=as_of, rows=[AgingRowOut(**r.__dict__) for r in rows], total_remaining=round(sum(r.remaining_balance for r in rows), 2))
