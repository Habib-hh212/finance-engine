import { apiGet, apiPost } from "./client";
import type { ExchangeRate, FxScenario } from "./types";

export const listExchangeRates = (fromCurrency?: string, toCurrency?: string) => {
  const params = new URLSearchParams();
  if (fromCurrency) params.set("from_currency", fromCurrency);
  if (toCurrency) params.set("to_currency", toCurrency);
  const qs = params.toString();
  return apiGet<ExchangeRate[]>(`/exchange-rates${qs ? `?${qs}` : ""}`);
};

export const upsertExchangeRate = (from_currency: string, to_currency: string, rate_date: string, rate: number) =>
  apiPost<ExchangeRate>("/exchange-rates", { from_currency, to_currency, rate_date, rate });

export const getFxScenario = (companyId: string, startPeriod: string, endPeriod: string, shockPct: number) =>
  apiGet<FxScenario>(
    `/fx/scenario?company_id=${companyId}&start_period=${startPeriod}&end_period=${endPeriod}&shock_pct=${shockPct}`,
  );
