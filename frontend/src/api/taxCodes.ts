import { apiGet, apiPatch, apiPost } from "./client";
import type { TaxCode, TaxDirection, TaxReport, TaxType } from "./types";

export const listTaxCodes = (companyId: string) => apiGet<TaxCode[]>(`/tax-codes?company_id=${companyId}`);

export const createTaxCode = (
  companyId: string,
  country: string,
  code: string,
  name: string,
  tax_type: TaxType,
  rate_pct: number,
  direction: TaxDirection,
  gl_account_id: string,
) => apiPost<TaxCode>(`/tax-codes?company_id=${companyId}`, { country, code, name, tax_type, rate_pct, direction, gl_account_id });

export const updateTaxCode = (companyId: string, taxCodeId: string, changes: { name?: string; rate_pct?: number; is_active?: boolean }) =>
  apiPatch<TaxCode>(`/tax-codes/${taxCodeId}?company_id=${companyId}`, changes);

export const getTaxReport = (companyId: string, start: string, end: string) =>
  apiGet<TaxReport>(`/tax-report?company_id=${companyId}&start=${start}&end=${end}`);
