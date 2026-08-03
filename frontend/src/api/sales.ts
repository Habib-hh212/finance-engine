import { apiGet, apiPatch, apiUpload } from "./client";
import type { ForecastModel, ForecastResponse, ModelComparison, Product, SalesUploadResult } from "./types";

export const listProducts = (companyId: string) => apiGet<Product[]>(`/products?company_id=${companyId}`);

export const setProductCost = (productId: string, unit_variable_cost: number) =>
  apiPatch<Product>(`/products/${productId}`, { unit_variable_cost });

export const uploadSalesCsv = (companyId: string, file: File) =>
  apiUpload<SalesUploadResult>(`/sales/upload?company_id=${companyId}`, file);

export const getForecast = (
  companyId: string,
  productId: string,
  model: ForecastModel,
  periods: number,
) =>
  apiGet<ForecastResponse>(
    `/sales/forecast?company_id=${companyId}&product_id=${productId}&model=${model}&periods=${periods}`,
  );

export const compareForecastModels = (companyId: string, productId: string) =>
  apiGet<ModelComparison>(`/sales/forecast/compare?company_id=${companyId}&product_id=${productId}`);
