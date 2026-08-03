import { apiGet, apiPost } from "./client";
import type { FixedCost, MarginalCostingSummary } from "./types";

export const createFixedCost = (companyId: string, fiscal_year: number, name: string, amount: number, category?: string) =>
  apiPost<FixedCost>(`/fixed-costs?company_id=${companyId}`, { fiscal_year, name, amount, category });

export const listFixedCosts = (companyId: string, fiscalYear?: number) =>
  apiGet<FixedCost[]>(`/fixed-costs?company_id=${companyId}${fiscalYear ? `&fiscal_year=${fiscalYear}` : ""}`);

export const getMarginalCostingSummary = (companyId: string, fiscalYear: number) =>
  apiGet<MarginalCostingSummary>(`/marginal-costing/summary?company_id=${companyId}&fiscal_year=${fiscalYear}`);
