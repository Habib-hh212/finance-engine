import { apiDelete, apiGet, apiPatch, apiPost } from "./client";
import type {
  Budget,
  BudgetDetail,
  BudgetLine,
  BudgetType,
  BudgetVersion,
  CapitalAppraisalRow,
  CostCenter,
  FlexibleVarianceRow,
  GLAccount,
  GLCategory,
  GLForecastRole,
} from "./types";

export const listCostCenters = (companyId: string) => apiGet<CostCenter[]>(`/cost-centers?company_id=${companyId}`);

export const createCostCenter = (companyId: string, code: string, name: string, manager_name?: string) =>
  apiPost<CostCenter>(`/cost-centers?company_id=${companyId}`, { code, name, manager_name });

export const listGLAccounts = (companyId: string) => apiGet<GLAccount[]>(`/gl-accounts?company_id=${companyId}`);

export const createGLAccount = (
  companyId: string,
  code: string,
  name: string,
  category: GLCategory,
  forecast_role?: GLForecastRole,
) => apiPost<GLAccount>(`/gl-accounts?company_id=${companyId}`, { code, name, category, forecast_role });

export const updateGLAccount = (accountId: string, forecast_role: GLForecastRole | null) =>
  apiPatch<GLAccount>(`/gl-accounts/${accountId}`, { forecast_role });

export const listBudgets = (companyId: string) => apiGet<Budget[]>(`/budgets?company_id=${companyId}`);

export const createBudget = (
  companyId: string,
  name: string,
  type: BudgetType,
  fiscal_year: number,
  currency: string,
  rolling_window_months?: number,
) => apiPost<Budget>(`/budgets?company_id=${companyId}`, { name, type, fiscal_year, currency, rolling_window_months });

export const getBudget = (budgetId: string) => apiGet<BudgetDetail>(`/budgets/${budgetId}`);

export interface BudgetLineInput {
  gl_account_id: string;
  period: string;
  amount: number;
  justification?: string;
  variable_rate_per_unit?: number;
  useful_life_years?: number;
  annual_cash_flow?: number;
  cost_center_id?: string;
}

export const addBudgetLines = (budgetId: string, lines: BudgetLineInput[]) =>
  apiPost<BudgetLine[]>(`/budgets/${budgetId}/lines`, lines);

export const submitBudget = (budgetId: string) => apiPost<Budget>(`/budgets/${budgetId}/submit`);

export const approveBudget = (budgetId: string, actor_name: string, comment?: string) =>
  apiPost<Budget>(`/budgets/${budgetId}/approve`, { actor_name, comment });

export const rejectBudget = (budgetId: string, actor_name: string, comment?: string) =>
  apiPost<Budget>(`/budgets/${budgetId}/reject`, { actor_name, comment });

export const updateBudgetLine = (budgetId: string, lineId: string, changes: Partial<BudgetLineInput>) =>
  apiPatch<BudgetLine>(`/budgets/${budgetId}/lines/${lineId}`, changes);

export const deleteBudgetLine = (budgetId: string, lineId: string) =>
  apiDelete<void>(`/budgets/${budgetId}/lines/${lineId}`);

export const listBudgetVersions = (budgetId: string) => apiGet<BudgetVersion[]>(`/budgets/${budgetId}/versions`);

export const rollForwardBudget = (budgetId: string) => apiPost<Budget>(`/budgets/${budgetId}/roll-forward`);

export const getFlexibleVariance = (budgetId: string) =>
  apiGet<FlexibleVarianceRow[]>(`/budgets/${budgetId}/flexible-variance`);

export const getCapitalAppraisal = (budgetId: string) =>
  apiGet<CapitalAppraisalRow[]>(`/budgets/${budgetId}/capital-appraisal`);
