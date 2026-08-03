import { apiDownload, apiGet, apiUpload } from "./client";
import type { BalanceSheet, IncomeStatement, IncomeStatementTrendPoint, StatementUploadResult } from "./types";

export const getIncomeStatement = (companyId: string, startPeriod: string, endPeriod: string) =>
  apiGet<IncomeStatement>(`/reports/income-statement?company_id=${companyId}&start_period=${startPeriod}&end_period=${endPeriod}`);

export const getBalanceSheet = (companyId: string, asOf: string) =>
  apiGet<BalanceSheet>(`/reports/balance-sheet?company_id=${companyId}&as_of=${asOf}`);

export const getIncomeStatementTrend = (companyId: string, startPeriod: string, endPeriod: string) =>
  apiGet<IncomeStatementTrendPoint[]>(
    `/reports/income-statement/trend?company_id=${companyId}&start_period=${startPeriod}&end_period=${endPeriod}`,
  );

export const uploadStatements = (companyId: string, file: File) =>
  apiUpload<StatementUploadResult>(`/reports/upload-statements?company_id=${companyId}`, file);

export const downloadIncomeStatement = (companyId: string, startPeriod: string, endPeriod: string) =>
  apiDownload(
    `/reports/income-statement/export?company_id=${companyId}&start_period=${startPeriod}&end_period=${endPeriod}`,
    "income-statement.xlsx",
  );

export const downloadBalanceSheet = (companyId: string, asOf: string) =>
  apiDownload(`/reports/balance-sheet/export?company_id=${companyId}&as_of=${asOf}`, "balance-sheet.xlsx");
