import { apiDownload, apiGet, apiPatch, apiUpload } from "./client";
import type {
  DemandForecastResponse,
  ForecastModel,
  ForecastResponse,
  ModelComparison,
  MonteCarloResponse,
  Product,
  SalesUploadResult,
} from "./types";

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

export const getDemandForecast = (companyId: string, productId: string, model: ForecastModel, periods: number) =>
  apiGet<DemandForecastResponse>(
    `/sales/forecast/demand?company_id=${companyId}&product_id=${productId}&model=${model}&periods=${periods}`,
  );

export const downloadForecast = (companyId: string, productId: string, model: ForecastModel, periods: number) =>
  apiDownload(
    `/sales/forecast/export?company_id=${companyId}&product_id=${productId}&model=${model}&periods=${periods}`,
    "sales-forecast.xlsx",
  );

export const getMonteCarloForecast = (companyId: string, productId: string, model: ForecastModel, periods: number, trials = 1000) =>
  apiGet<MonteCarloResponse>(
    `/sales/forecast/monte-carlo?company_id=${companyId}&product_id=${productId}&model=${model}&periods=${periods}&trials=${trials}`,
  );
