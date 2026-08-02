import { apiGet, apiPost } from "./client";
import type { CashCategory, CashFlowForecastResponse, CashItem } from "./types";

export const listCashItems = (companyId: string) => apiGet<CashItem[]>(`/cashflow/items?company_id=${companyId}`);

export const createCashItem = (
  companyId: string,
  category: CashCategory,
  direction: "in" | "out",
  period: string,
  amount: number,
  description?: string,
) =>
  apiPost<CashItem>(`/cashflow/items?company_id=${companyId}`, { category, direction, period, amount, description });

export const getCashFlowForecast = (
  companyId: string,
  startPeriod: string,
  periods: number,
  collectionLagDays: number,
  openingBalance: number,
) =>
  apiGet<CashFlowForecastResponse>(
    `/cashflow/forecast?company_id=${companyId}&start_period=${startPeriod}&periods=${periods}` +
      `&collection_lag_days=${collectionLagDays}&opening_balance=${openingBalance}`,
  );
