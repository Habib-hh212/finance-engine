import { apiGet } from "./client";
import type { Insight, KPIResponse } from "./types";

export const getKPIs = (
  companyId: string,
  fiscalYear?: number,
  cashStartPeriod?: string,
  cashOpeningBalance?: number,
) => {
  const params = new URLSearchParams({ company_id: companyId });
  if (fiscalYear) params.set("fiscal_year", String(fiscalYear));
  if (cashStartPeriod) {
    params.set("cash_start_period", cashStartPeriod);
    params.set("cash_opening_balance", String(cashOpeningBalance ?? 0));
  }
  return apiGet<KPIResponse>(`/kpis?${params.toString()}`);
};

export const getInsights = (companyId: string, fiscalYear?: number) =>
  apiGet<Insight[]>(`/ai/insights?company_id=${companyId}${fiscalYear ? `&fiscal_year=${fiscalYear}` : ""}`);
