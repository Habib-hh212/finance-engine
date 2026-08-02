import { apiGet } from "./client";
import type { CustomerProfitability, ProductProfitability } from "./types";

export const getProfitabilityByProduct = (companyId: string) =>
  apiGet<ProductProfitability[]>(`/profitability/by-product?company_id=${companyId}`);

export const getProfitabilityByCustomer = (companyId: string) =>
  apiGet<CustomerProfitability[]>(`/profitability/by-customer?company_id=${companyId}`);
