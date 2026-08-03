import { apiGet, apiPost } from "./client";
import type { ProductionActual, StandardCost, StandardCostVariance } from "./types";

export interface StandardCostInput {
  product_id: string;
  material_std_price: number;
  material_std_qty: number;
  labor_std_rate: number;
  labor_std_hours: number;
  variable_overhead_std_rate: number;
  fixed_overhead_std_rate: number;
  fixed_overhead_budgeted: number;
}

export const upsertStandardCost = (companyId: string, payload: StandardCostInput) =>
  apiPost<StandardCost>(`/standard-costs?company_id=${companyId}`, payload);

export const listStandardCosts = (companyId: string) => apiGet<StandardCost[]>(`/standard-costs?company_id=${companyId}`);

export interface ProductionActualInput {
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

export const createProductionActual = (companyId: string, payload: ProductionActualInput) =>
  apiPost<ProductionActual>(`/production-actuals?company_id=${companyId}`, payload);

export const listProductionActuals = (companyId: string) =>
  apiGet<ProductionActual[]>(`/production-actuals?company_id=${companyId}`);

export const getStandardCostVariance = (companyId: string, fiscalYear?: number) =>
  apiGet<StandardCostVariance[]>(
    `/standard-costing/variance?company_id=${companyId}${fiscalYear ? `&fiscal_year=${fiscalYear}` : ""}`,
  );
