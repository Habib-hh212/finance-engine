import { apiGet, apiPost } from "./client";
import type { Accrual, PeriodCloseStatus, YearEndCloseResult } from "./types";

export const listAccruals = (companyId: string) => apiGet<Accrual[]>(`/accruals?company_id=${companyId}`);

export const createAccrual = (
  companyId: string,
  entry_date: string,
  debit_gl_account_id: string,
  credit_gl_account_id: string,
  amount: number,
  reversal_date: string,
  reference?: string,
  description?: string,
) => apiPost<Accrual>(`/accruals?company_id=${companyId}`, { entry_date, debit_gl_account_id, credit_gl_account_id, amount, reversal_date, reference, description });

export const reverseAccrual = (companyId: string, accrualId: string) => apiPost<Accrual>(`/accruals/${accrualId}/reverse?company_id=${companyId}`);

export const getPeriodCloseStatus = (companyId: string, period: string) => apiGet<PeriodCloseStatus>(`/period-close/status?company_id=${companyId}&period=${period}`);

export const closeFiscalYear = (companyId: string, start: string, end: string, retained_earnings_gl_account_id: string) =>
  apiPost<YearEndCloseResult>(`/year-end/close?company_id=${companyId}`, { start, end, retained_earnings_gl_account_id });
