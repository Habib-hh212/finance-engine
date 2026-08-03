import { apiGet } from "./client";
import type { BalanceSheet, IncomeStatement } from "./types";

export const getIncomeStatement = (companyId: string, startPeriod: string, endPeriod: string) =>
  apiGet<IncomeStatement>(`/reports/income-statement?company_id=${companyId}&start_period=${startPeriod}&end_period=${endPeriod}`);

export const getBalanceSheet = (companyId: string, asOf: string) =>
  apiGet<BalanceSheet>(`/reports/balance-sheet?company_id=${companyId}&as_of=${asOf}`);
