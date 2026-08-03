export interface Company {
  id: string;
  name: string;
  base_currency: string;
}

export interface Product {
  id: string;
  sku: string;
  name: string;
  unit_variable_cost: number | null;
}

export interface ForecastPoint {
  period: string;
  forecast: number;
  lower_bound: number;
  upper_bound: number;
  currency: string;
}

export interface ForecastResponse {
  company_id: string;
  product_id: string;
  model: string;
  history_periods: number;
  points: ForecastPoint[];
}

export type ForecastModel = "moving_average" | "weighted_average" | "exponential_smoothing";

export interface SalesUploadResult {
  rows_imported: number;
  products_created: number;
  customers_created: number;
}

export type GLCategory = "revenue" | "expense" | "asset" | "liability" | "equity";

export interface GLAccount {
  id: string;
  code: string;
  name: string;
  category: GLCategory;
}

export type BudgetType = "revenue" | "expense" | "master" | "zero_based" | "flexible" | "rolling" | "capital";
export type BudgetStatus = "draft" | "pending_manager" | "pending_finance" | "pending_cfo" | "approved" | "rejected";

export interface Budget {
  id: string;
  company_id: string;
  name: string;
  type: BudgetType;
  fiscal_year: number;
  currency: string;
  status: BudgetStatus;
  rolling_window_months: number | null;
}

export interface BudgetLine {
  id: string;
  gl_account_id: string;
  period: string;
  amount: number;
  currency: string;
  justification: string | null;
  variable_rate_per_unit: number | null;
  useful_life_years: number | null;
  annual_cash_flow: number | null;
}

export interface Approval {
  role: string;
  action: "approved" | "rejected";
  actor_name: string;
  comment: string | null;
  acted_at: string;
}

export interface BudgetDetail extends Budget {
  lines: BudgetLine[];
  approvals: Approval[];
}

export type CashCategory = "receivable_collection" | "payroll" | "vendor_payment" | "tax" | "loan" | "interest" | "other";

export interface CashItem {
  id: string;
  category: CashCategory;
  direction: "in" | "out";
  period: string;
  amount: number;
  currency: string;
  description: string | null;
}

export interface CashFlowPeriodRow {
  period: string;
  cash_in_forecast: number;
  cash_in_manual: number;
  cash_in_total: number;
  cash_out_budget: number;
  cash_out_manual: number;
  cash_out_total: number;
  net_cash_flow: number;
  opening_balance: number;
  closing_balance: number;
}

export interface CashFlowForecastResponse {
  company_id: string;
  start_period: string;
  periods: number;
  collection_lag_days: number;
  rows: CashFlowPeriodRow[];
}

export type TrafficLight = "green" | "yellow" | "red";

export interface ActualLine {
  id: string;
  gl_account_id: string;
  period: string;
  amount: number;
  currency: string;
  description: string | null;
  actual_quantity: number | null;
}

export interface VarianceRow {
  gl_account_id: string;
  gl_account_code: string;
  gl_account_name: string;
  category: GLCategory;
  period: string;
  budget_amount: number;
  actual_amount: number;
  variance_amount: number;
  variance_pct: number | null;
  status: TrafficLight;
}

export interface BudgetConsumption {
  budget_id: string;
  budget_amount: number;
  spent: number;
  remaining: number;
  consumption_pct: number | null;
  status: TrafficLight;
}

export interface FlexibleVarianceRow {
  gl_account_id: string;
  gl_account_code: string;
  gl_account_name: string;
  period: string;
  static_amount: number;
  variable_rate_per_unit: number;
  actual_quantity: number | null;
  flexed_amount: number;
  actual_amount: number;
  spending_variance: number;
  volume_variance: number;
  total_variance: number;
}

export interface CapitalAppraisalRow {
  gl_account_id: string;
  gl_account_code: string;
  gl_account_name: string;
  period: string;
  investment: number;
  annual_cash_flow: number | null;
  useful_life_years: number | null;
  payback_period_years: number | null;
  total_cash_flow: number | null;
  net_gain: number | null;
  roi_pct: number | null;
  average_annual_roi_pct: number | null;
}

export interface ProductProfitability {
  product_id: string;
  sku: string;
  name: string;
  quantity: number;
  revenue: number;
  unit_price: number | null;
  unit_variable_cost: number | null;
  contribution_per_unit: number | null;
  contribution_margin_total: number | null;
  contribution_margin_pct: number | null;
}

export interface CustomerProfitability {
  customer_id: string;
  name: string;
  revenue: number;
  contribution_margin_total: number | null;
  contribution_margin_pct: number | null;
}

export interface KPIResponse {
  gross_margin_pct: number | null;
  budget_utilization_pct: number | null;
  forecast_accuracy_mape: number | null;
  cash_runway_months: number | null;
}

export interface Insight {
  type: string;
  severity: "red" | "yellow";
  message: string;
}

export interface AccountAmount {
  gl_account_id: string;
  code: string;
  name: string;
  amount: number;
}

export interface IncomeStatement {
  start_period: string;
  end_period: string;
  revenue_lines: AccountAmount[];
  total_revenue: number;
  expense_lines: AccountAmount[];
  total_expense: number;
  net_profit: number;
}

export interface BalanceSheet {
  as_of: string;
  asset_lines: AccountAmount[];
  total_assets: number;
  liability_lines: AccountAmount[];
  total_liabilities: number;
  equity_lines: AccountAmount[];
  total_equity: number;
  is_balanced: boolean;
  difference: number;
}
