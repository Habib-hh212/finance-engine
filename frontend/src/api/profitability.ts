import { apiGet } from "./client";
import type { CustomerChurnRisk, CustomerProfitability, ProductProfitability } from "./types";

export const getProfitabilityByProduct = (companyId: string) =>
  apiGet<ProductProfitability[]>(`/profitability/by-product?company_id=${companyId}`);

export const getProfitabilityByCustomer = (companyId: string) =>
  apiGet<CustomerProfitability[]>(`/profitability/by-customer?company_id=${companyId}`);

export const getCustomerChurnRisk = (companyId: string) =>
  apiGet<CustomerChurnRisk[]>(`/profitability/customer-churn-risk?company_id=${companyId}`);
