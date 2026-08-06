"""Accounts Receivable and Accounts Payable sub-ledgers.

A design choice worth stating up front: there's no separate "down payment"
G/L account here, unlike SAP's special-G/L indicator technique. A customer
receipt always posts Dr Cash / Cr Accounts Receivable, whether or not it's
linked to an invoice yet -- an unapplied receipt just sits as a credit
balance on that customer's slice of the AR control account until it's
matched to one. That IS a down payment, economically: cash received ahead
of the invoice that will eventually offset it. The vendor side mirrors
this (Dr Accounts Payable / Cr Cash). Matching a receipt/payment to an
invoice/bill after the fact -- the "later adjustment" -- is a reporting-
level link (an Application row), not a second journal entry, since both
sides already hit the same control account. This is simpler than a
special-G/L account and reaches the same economic result.

Invoices and bills reuse the tax-code engine from bookkeeping.py directly
-- an invoice's revenue line can carry a tax_code_id the same way any
journal entry line can, so VAT/GST on a real sales or purchase invoice is
computed and posted exactly the way it already is everywhere else.
"""
import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InvoiceStatus:
    OPEN = "open"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    VOID = "void"


INVOICE_STATUSES = {InvoiceStatus.OPEN, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.PAID, InvoiceStatus.VOID}


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # See Customer.state/gstin -- same place-of-supply comparison, on the
    # purchase side (decides whether input ITC is CGST+SGST or IGST).
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)


class CustomerInvoice(Base):
    __tablename__ = "customer_invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    revenue_gl_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False)
    tax_code_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("tax_codes.id"), nullable=True)
    # India GST path (mutually exclusive with tax_code_id in practice --
    # a company uses one tax system or the other): the rate applied and
    # its CGST/SGST/IGST split, decided by comparing the customer's state
    # to the company's home_state at posting time.
    gst_rate_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("gst_rates.id"), nullable=True)
    cgst_amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    sgst_amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    igst_amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=InvoiceStatus.OPEN)
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=False)


class CustomerReceipt(Base):
    __tablename__ = "customer_receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False)
    cash_gl_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=False)


class CustomerReceiptApplication(Base):
    __tablename__ = "customer_receipt_applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receipt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customer_receipts.id"), nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customer_invoices.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    applied_date: Mapped[date] = mapped_column(Date, nullable=False)


class VendorBill(Base):
    __tablename__ = "vendor_bills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    bill_number: Mapped[str] = mapped_column(String(50), nullable=False)
    bill_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    expense_gl_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False)
    tax_code_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("tax_codes.id"), nullable=True)
    tds_section_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("tds_sections.id"), nullable=True)
    tds_amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    # See CustomerInvoice.gst_rate_id -- same India GST path, on the
    # purchase side (input CGST/SGST/IGST, i.e. ITC).
    gst_rate_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("gst_rates.id"), nullable=True)
    cgst_amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    sgst_amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    igst_amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=InvoiceStatus.OPEN)
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=False)


class VendorPayment(Base):
    __tablename__ = "vendor_payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    cash_gl_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=False)


class VendorPaymentApplication(Base):
    __tablename__ = "vendor_payment_applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vendor_payments.id"), nullable=False)
    bill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vendor_bills.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    applied_date: Mapped[date] = mapped_column(Date, nullable=False)
