import { apiGet, apiPatch, apiPost } from "./client";
import type { TdsSection, TdsSummary } from "./types";

export const listTdsSections = (companyId: string) => apiGet<TdsSection[]>(`/tds-sections?company_id=${companyId}`);

export const createTdsSection = (companyId: string, section_code: string, description: string, rate_pct: number) =>
  apiPost<TdsSection>(`/tds-sections?company_id=${companyId}`, { section_code, description, rate_pct });

export const updateTdsSection = (companyId: string, sectionId: string, changes: { description?: string; rate_pct?: number; is_active?: boolean }) =>
  apiPatch<TdsSection>(`/tds-sections/${sectionId}?company_id=${companyId}`, changes);

export const getTdsReport = (companyId: string, start: string, end: string) =>
  apiGet<TdsSummary>(`/tds-report?company_id=${companyId}&start=${start}&end=${end}`);
