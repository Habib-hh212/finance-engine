import { apiGet, apiPatch, apiPost } from "./client";
import type { GstDirection, GstRate, Gstr1Report, Gstr3bReport } from "./types";

export const listGstRates = (companyId: string) => apiGet<GstRate[]>(`/gst-rates?company_id=${companyId}`);

export const createGstRate = (
  companyId: string,
  description: string,
  rate_pct: number,
  direction: GstDirection,
  cgst_gl_account_id: string,
  sgst_gl_account_id: string,
  igst_gl_account_id: string,
) =>
  apiPost<GstRate>(`/gst-rates?company_id=${companyId}`, {
    description,
    rate_pct,
    direction,
    cgst_gl_account_id,
    sgst_gl_account_id,
    igst_gl_account_id,
  });

export const updateGstRate = (companyId: string, rateId: string, changes: { description?: string; rate_pct?: number; is_active?: boolean }) =>
  apiPatch<GstRate>(`/gst-rates/${rateId}?company_id=${companyId}`, changes);

export const getGstr1Report = (companyId: string, start: string, end: string) =>
  apiGet<Gstr1Report>(`/gstr1-report?company_id=${companyId}&start=${start}&end=${end}`);

export const getGstr3bReport = (companyId: string, start: string, end: string) =>
  apiGet<Gstr3bReport>(`/gstr3b-report?company_id=${companyId}&start=${start}&end=${end}`);
