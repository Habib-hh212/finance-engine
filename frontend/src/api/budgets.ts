import { apiGet, apiPost } from "./client";
import type { Budget, BudgetDetail, BudgetLine, BudgetType, GLAccount, GLCategory } from "./types";

export const listGLAccounts = (companyId: string) => apiGet<GLAccount[]>(`/gl-accounts?company_id=${companyId}`);

export const createGLAccount = (companyId: string, code: string, name: string, category: GLCategory) =>
  apiPost<GLAccount>(`/gl-accounts?company_id=${companyId}`, { code, name, category });

export const listBudgets = (companyId: string) => apiGet<Budget[]>(`/budgets?company_id=${companyId}`);

export const createBudget = (companyId: string, name: string, type: BudgetType, fiscal_year: number, currency: string) =>
  apiPost<Budget>(`/budgets?company_id=${companyId}`, { name, type, fiscal_year, currency });

export const getBudget = (budgetId: string) => apiGet<BudgetDetail>(`/budgets/${budgetId}`);

export const addBudgetLines = (
  budgetId: string,
  lines: { gl_account_id: string; period: string; amount: number }[],
) => apiPost<BudgetLine[]>(`/budgets/${budgetId}/lines`, lines);

export const submitBudget = (budgetId: string) => apiPost<Budget>(`/budgets/${budgetId}/submit`);

export const approveBudget = (budgetId: string, actor_name: string, comment?: string) =>
  apiPost<Budget>(`/budgets/${budgetId}/approve`, { actor_name, comment });

export const rejectBudget = (budgetId: string, actor_name: string, comment?: string) =>
  apiPost<Budget>(`/budgets/${budgetId}/reject`, { actor_name, comment });
