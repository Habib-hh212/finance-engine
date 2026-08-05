import { apiDelete, apiGet, apiPost } from "./client";
import type { GLLedger, JournalEntry, TrialBalance } from "./types";

export interface JournalEntryLineInput {
  gl_account_id: string;
  debit_amount: number;
  credit_amount: number;
  cost_center_id?: string;
  description?: string;
  tax_code_id?: string;
}

export const listJournalEntries = (companyId: string, status?: string) =>
  apiGet<JournalEntry[]>(`/journal-entries?company_id=${companyId}${status ? `&status=${status}` : ""}`);

export const createJournalEntry = (
  companyId: string,
  entry_date: string,
  lines: JournalEntryLineInput[],
  reference?: string,
  description?: string,
  currency = "USD",
) => apiPost<JournalEntry>(`/journal-entries?company_id=${companyId}`, { entry_date, reference, description, currency, lines });

export const postJournalEntry = (entryId: string) => apiPost<JournalEntry>(`/journal-entries/${entryId}/post`);

export const reverseJournalEntry = (entryId: string, entry_date: string) =>
  apiPost<JournalEntry>(`/journal-entries/${entryId}/reverse`, { entry_date });

export const deleteJournalEntry = (entryId: string) => apiDelete<void>(`/journal-entries/${entryId}`);

export const getTrialBalance = (companyId: string, asOf: string) =>
  apiGet<TrialBalance>(`/trial-balance?company_id=${companyId}&as_of=${asOf}`);

export const getGLLedger = (companyId: string, glAccountId: string, start: string, end: string) =>
  apiGet<GLLedger>(`/gl-ledger?company_id=${companyId}&gl_account_id=${glAccountId}&start=${start}&end=${end}`);
