import { apiDownload, apiGet } from "./client";
import type { BalanceSheetForecastPeriod, IncomeStatementForecastPeriod, StatementForecastMethod } from "./types";

export const getIncomeStatementForecast = (
  companyId: string,
  startPeriod: string,
  periods: number,
  forecastMethod: StatementForecastMethod = "driver_based",
  trendModel: string = "exponential_smoothing",
) =>
  apiGet<IncomeStatementForecastPeriod[]>(
    `/forecast/income-statement?company_id=${companyId}&start_period=${startPeriod}&periods=${periods}` +
      `&forecast_method=${forecastMethod}&trend_model=${trendModel}`,
  );

export const getBalanceSheetForecast = (
  companyId: string,
  startPeriod: string,
  periods: number,
  dsoDays: number,
  dpoDays: number,
  collectionLagDays: number,
) =>
  apiGet<BalanceSheetForecastPeriod[]>(
    `/forecast/balance-sheet?company_id=${companyId}&start_period=${startPeriod}&periods=${periods}` +
      `&dso_days=${dsoDays}&dpo_days=${dpoDays}&collection_lag_days=${collectionLagDays}`,
  );

export const downloadStatementForecast = (
  companyId: string,
  startPeriod: string,
  periods: number,
  forecastMethod: StatementForecastMethod = "driver_based",
  trendModel: string = "exponential_smoothing",
) =>
  apiDownload(
    `/forecast/export?company_id=${companyId}&start_period=${startPeriod}&periods=${periods}` +
      `&forecast_method=${forecastMethod}&trend_model=${trendModel}`,
    "statement-forecast.xlsx",
  );
