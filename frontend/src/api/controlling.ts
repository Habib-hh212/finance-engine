import { apiGet, apiPost } from "./client";
import type { ActualLine, BudgetConsumption, VarianceRow } from "./types";

export const createActual = (companyId: string, gl_account_id: string, period: string, amount: number, description?: string) =>
  apiPost<ActualLine>(`/actuals?company_id=${companyId}`, { gl_account_id, period, amount, description });

export const listActuals = (companyId: string) => apiGet<ActualLine[]>(`/actuals?company_id=${companyId}`);

export const getBudgetVsActual = (companyId: string, fiscalYear?: number) =>
  apiGet<VarianceRow[]>(
    `/variance/budget-vs-actual?company_id=${companyId}${fiscalYear ? `&fiscal_year=${fiscalYear}` : ""}`,
  );

export const getBudgetConsumption = (budgetId: string) =>
  apiGet<BudgetConsumption>(`/variance/budget-consumption/${budgetId}`);
