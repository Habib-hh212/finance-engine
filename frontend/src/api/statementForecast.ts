import { apiGet } from "./client";
import type { BalanceSheetForecastPeriod, IncomeStatementForecastPeriod } from "./types";

export const getIncomeStatementForecast = (companyId: string, startPeriod: string, periods: number) =>
  apiGet<IncomeStatementForecastPeriod[]>(
    `/forecast/income-statement?company_id=${companyId}&start_period=${startPeriod}&periods=${periods}`,
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
