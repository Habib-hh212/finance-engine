import { apiGet, apiPost } from "./client";
import type { AgingReport, CustomerInvoice, CustomerParty, CustomerReceipt, VendorBill, VendorParty, VendorPayment } from "./types";

export const listCustomers = (companyId: string) => apiGet<CustomerParty[]>(`/customers?company_id=${companyId}`);
export const createCustomer = (companyId: string, name: string) => apiPost<CustomerParty>(`/customers?company_id=${companyId}`, { name });

export const listVendors = (companyId: string) => apiGet<VendorParty[]>(`/vendors?company_id=${companyId}`);
export const createVendor = (companyId: string, name: string) => apiPost<VendorParty>(`/vendors?company_id=${companyId}`, { name });

export interface CustomerInvoiceInput {
  customer_id: string;
  invoice_number: string;
  invoice_date: string;
  due_date: string;
  revenue_gl_account_id: string;
  net_amount: number;
  tax_code_id?: string;
  currency?: string;
}

export const listCustomerInvoices = (companyId: string) => apiGet<CustomerInvoice[]>(`/customer-invoices?company_id=${companyId}`);
export const createCustomerInvoice = (companyId: string, input: CustomerInvoiceInput) => apiPost<CustomerInvoice>(`/customer-invoices?company_id=${companyId}`, input);

export const listCustomerReceipts = (companyId: string) => apiGet<CustomerReceipt[]>(`/customer-receipts?company_id=${companyId}`);
export const createCustomerReceipt = (companyId: string, customer_id: string, receipt_date: string, cash_gl_account_id: string, amount: number, reference?: string) =>
  apiPost<CustomerReceipt>(`/customer-receipts?company_id=${companyId}`, { customer_id, receipt_date, cash_gl_account_id, amount, reference });
export const applyCustomerReceipt = (companyId: string, receipt_id: string, invoice_id: string, amount: number, applied_date: string) =>
  apiPost<CustomerInvoice>(`/customer-receipts/apply?company_id=${companyId}`, { receipt_id, invoice_id, amount, applied_date });

export interface VendorBillInput {
  vendor_id: string;
  bill_number: string;
  bill_date: string;
  due_date: string;
  expense_gl_account_id: string;
  net_amount: number;
  tax_code_id?: string;
  currency?: string;
}

export const listVendorBills = (companyId: string) => apiGet<VendorBill[]>(`/vendor-bills?company_id=${companyId}`);
export const createVendorBill = (companyId: string, input: VendorBillInput) => apiPost<VendorBill>(`/vendor-bills?company_id=${companyId}`, input);

export const listVendorPayments = (companyId: string) => apiGet<VendorPayment[]>(`/vendor-payments?company_id=${companyId}`);
export const createVendorPayment = (companyId: string, vendor_id: string, payment_date: string, cash_gl_account_id: string, amount: number, reference?: string) =>
  apiPost<VendorPayment>(`/vendor-payments?company_id=${companyId}`, { vendor_id, payment_date, cash_gl_account_id, amount, reference });
export const applyVendorPayment = (companyId: string, payment_id: string, bill_id: string, amount: number, applied_date: string) =>
  apiPost<VendorBill>(`/vendor-payments/apply?company_id=${companyId}`, { payment_id, bill_id, amount, applied_date });

export const getArAging = (companyId: string, asOf: string) => apiGet<AgingReport>(`/reports/ar-aging?company_id=${companyId}&as_of=${asOf}`);
export const getApAging = (companyId: string, asOf: string) => apiGet<AgingReport>(`/reports/ap-aging?company_id=${companyId}&as_of=${asOf}`);
