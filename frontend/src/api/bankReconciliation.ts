import { apiDelete, apiGet, apiPost, apiUpload } from "./client";
import type { BankImportResult, BankStatementLine, ReconciliationSummary, UnmatchedGLLine } from "./types";

export const uploadBankStatement = (companyId: string, cashGlAccountId: string, file: File) =>
  apiUpload<BankImportResult>(`/bank-statements/upload?company_id=${companyId}&cash_gl_account_id=${cashGlAccountId}`, file);

export const listBankStatementLines = (companyId: string, cashGlAccountId: string) =>
  apiGet<BankStatementLine[]>(`/bank-statements?company_id=${companyId}&cash_gl_account_id=${cashGlAccountId}`);

export const matchBankStatementLine = (companyId: string, lineId: string, actualLineId: string) =>
  apiPost<BankStatementLine>(`/bank-statements/${lineId}/match?company_id=${companyId}`, { actual_line_id: actualLineId });

export const unmatchBankStatementLine = (companyId: string, lineId: string) =>
  apiPost<BankStatementLine>(`/bank-statements/${lineId}/unmatch?company_id=${companyId}`);

export const deleteBankStatementLine = (companyId: string, lineId: string) => apiDelete<void>(`/bank-statements/${lineId}?company_id=${companyId}`);

export const listUnmatchedGLLines = (companyId: string, cashGlAccountId: string) =>
  apiGet<UnmatchedGLLine[]>(`/bank-reconciliation/unmatched-gl-lines?company_id=${companyId}&cash_gl_account_id=${cashGlAccountId}`);

export const getReconciliationSummary = (companyId: string, cashGlAccountId: string, asOf: string, bankStatementEndingBalance: number) =>
  apiGet<ReconciliationSummary>(
    `/bank-reconciliation/summary?company_id=${companyId}&cash_gl_account_id=${cashGlAccountId}&as_of=${asOf}&bank_statement_ending_balance=${bankStatementEndingBalance}`,
  );
