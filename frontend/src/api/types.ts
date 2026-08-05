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

export type ForecastModel =
  | "moving_average"
  | "weighted_average"
  | "exponential_smoothing"
  | "random_forest"
  | "gradient_boosting";

export interface ModelComparison {
  company_id: string;
  product_id: string;
  history_periods: number;
  mape_by_model: Record<string, number | null>;
}

export interface SalesUploadResult {
  rows_imported: number;
  products_created: number;
  customers_created: number;
}

export type GLCategory = "revenue" | "expense" | "asset" | "liability" | "equity";
export type GLForecastRole = "cash" | "accounts_receivable" | "accounts_payable";

export interface GLAccount {
  id: string;
  code: string;
  name: string;
  category: GLCategory;
  forecast_role: GLForecastRole | null;
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
  cost_center_id: string | null;
}

export interface CostCenter {
  id: string;
  code: string;
  name: string;
  manager_name: string | null;
}

export interface CostCenterVarianceRow {
  cost_center_id: string;
  cost_center_code: string;
  cost_center_name: string;
  period: string;
  budget_amount: number;
  actual_amount: number;
  variance_amount: number;
  variance_pct: number | null;
  status: TrafficLight;
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
  cost_center_id: string | null;
  journal_entry_line_id: string | null;
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

export interface StandardCost {
  id: string;
  product_id: string;
  material_std_price: number;
  material_std_qty: number;
  labor_std_rate: number;
  labor_std_hours: number;
  variable_overhead_std_rate: number;
  fixed_overhead_std_rate: number;
  fixed_overhead_budgeted: number;
}

export interface ProductionActual {
  id: string;
  product_id: string;
  period: string;
  units_produced: number;
  material_actual_price: number;
  material_actual_qty: number;
  labor_actual_rate: number;
  labor_actual_hours: number;
  actual_variable_overhead: number;
  actual_fixed_overhead: number;
}

export interface StandardCostVariance {
  product_id: string;
  product_sku: string;
  product_name: string;
  period: string;
  material_price_variance: number;
  material_quantity_variance: number;
  material_total_variance: number;
  labor_rate_variance: number;
  labor_efficiency_variance: number;
  labor_total_variance: number;
  variable_overhead_spending_variance: number;
  variable_overhead_efficiency_variance: number;
  variable_overhead_total_variance: number;
  fixed_overhead_budget_variance: number;
  fixed_overhead_volume_variance: number;
  fixed_overhead_total_variance: number;
  total_cost_variance: number;
}

export interface FixedCost {
  id: string;
  fiscal_year: number;
  name: string;
  amount: number;
  currency: string;
  category: string | null;
}

export interface MarginalCostingSummary {
  fiscal_year: number;
  revenue: number;
  variable_cost: number;
  contribution_margin: number;
  contribution_margin_ratio: number | null;
  fixed_costs: number;
  net_operating_income: number;
  break_even_revenue: number | null;
  margin_of_safety: number | null;
  margin_of_safety_pct: number | null;
  degree_of_operating_leverage: number | null;
  uncosted_product_skus: string[];
}

export interface BudgetVersion {
  id: string;
  version_number: number;
  submitted_at: string;
  lines_snapshot: Record<string, unknown>[];
}

export interface IncomeStatementForecastPeriod {
  period: string;
  revenue_forecast: number;
  expense_forecast: number;
  net_profit_forecast: number;
}

export interface BalanceSheetForecastPeriod {
  period: string;
  accounts_receivable: number;
  cash: number;
  other_assets: number;
  total_assets: number;
  accounts_payable: number;
  other_liabilities: number;
  total_liabilities: number;
  equity: number;
  is_balanced: boolean;
  difference: number;
}

export interface Scenario {
  id: string;
  name: string;
  description: string | null;
  sales_growth_pct: number;
  expense_growth_pct: number;
}

export interface ScenarioForecast {
  scenario: Scenario;
  base_income_statement: IncomeStatementForecastPeriod[];
  scenario_income_statement: IncomeStatementForecastPeriod[];
  base_balance_sheet: BalanceSheetForecastPeriod[];
  scenario_balance_sheet: BalanceSheetForecastPeriod[];
}

export interface DemandForecastPoint {
  period: string;
  forecast_units: number;
  lower_bound: number;
  upper_bound: number;
}

export interface DemandForecastResponse {
  company_id: string;
  product_id: string;
  model: string;
  history_periods: number;
  points: DemandForecastPoint[];
}

export interface MonteCarloPoint {
  period: string;
  p10: number;
  p50: number;
  p90: number;
  mean: number;
  currency: string;
}

export interface MonteCarloResponse {
  company_id: string;
  product_id: string;
  model: string;
  trials: number;
  history_periods: number;
  points: MonteCarloPoint[];
}

export interface StatementUploadResult {
  rows_imported: number;
  accounts_created: number;
  cost_centers_created: number;
}

export interface IncomeStatementTrendPoint {
  period: string;
  revenue: number;
  expense: number;
  net_profit: number;
}

export type StatementForecastMethod = "driver_based" | "historical_trend";

export interface ExchangeRate {
  id: string;
  from_currency: string;
  to_currency: string;
  rate_date: string;
  rate: number;
}

export interface FxExposureLine {
  currency: string;
  period: string;
  native_amount: number;
  rate_used: number | null;
  base_amount: number | null;
}

export interface FxScenario {
  base_currency: string;
  shock_pct: number;
  lines: FxExposureLine[];
  total_base_actual: number;
  total_base_shocked: number;
  impact: number;
  unrated_currencies: string[];
}

export type JournalEntryStatus = "draft" | "posted" | "reversed";

export interface JournalEntryLine {
  id: string;
  gl_account_id: string;
  gl_account_code: string;
  gl_account_name: string;
  cost_center_id: string | null;
  debit_amount: number;
  credit_amount: number;
  description: string | null;
}

export interface JournalEntry {
  id: string;
  entry_date: string;
  reference: string | null;
  description: string | null;
  currency: string;
  status: JournalEntryStatus;
  reverses_entry_id: string | null;
  created_at: string;
  posted_at: string | null;
  lines: JournalEntryLine[];
}

export interface TrialBalanceRow {
  gl_account_id: string;
  gl_account_code: string;
  gl_account_name: string;
  category: GLCategory;
  total_debit: number;
  total_credit: number;
  net_balance: number;
}

export interface TrialBalance {
  as_of: string;
  rows: TrialBalanceRow[];
  total_debit: number;
  total_credit: number;
  is_balanced: boolean;
}

export interface AuditLogEntry {
  id: string;
  entity_type: string;
  entity_id: string | null;
  action: string;
  actor_email: string;
  actor_name: string;
  summary: string;
  created_at: string;
}

export interface CustomerChurnRisk {
  customer_id: string;
  name: string;
  last_order_period: string;
  months_since_last_order: number;
  avg_order_interval_months: number;
  risk_ratio: number;
  risk_level: "low" | "medium" | "high";
  total_revenue: number;
}
