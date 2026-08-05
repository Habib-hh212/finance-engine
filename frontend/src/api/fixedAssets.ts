import { apiGet, apiPost } from "./client";
import type { Asset, AssetClass, AssetRegister, DepreciationMethod, DepreciationRun, DisposalType, DisposeAssetResult } from "./types";

export const listAssetClasses = (companyId: string) => apiGet<AssetClass[]>(`/asset-classes?company_id=${companyId}`);

export const createAssetClass = (
  companyId: string,
  name: string,
  apc_gl_account_id: string,
  depreciation_expense_gl_account_id: string,
  accumulated_depreciation_gl_account_id: string,
  disposal_gain_gl_account_id: string,
  disposal_loss_gl_account_id: string,
  default_depreciation_method: DepreciationMethod = "straight_line",
  default_useful_life_years = 5,
  default_declining_balance_factor = 2.0,
) =>
  apiPost<AssetClass>(`/asset-classes?company_id=${companyId}`, {
    name,
    apc_gl_account_id,
    depreciation_expense_gl_account_id,
    accumulated_depreciation_gl_account_id,
    disposal_gain_gl_account_id,
    disposal_loss_gl_account_id,
    default_depreciation_method,
    default_useful_life_years,
    default_declining_balance_factor,
  });

export interface AssetCreateInput {
  asset_class_id: string;
  code: string;
  name: string;
  acquisition_date: string;
  capitalized_cost: number;
  funding_gl_account_id: string;
  salvage_value?: number;
  useful_life_years?: number;
  depreciation_method?: DepreciationMethod;
  declining_balance_factor?: number;
  cost_center_id?: string;
}

export const listAssets = (companyId: string, status?: string) =>
  apiGet<Asset[]>(`/assets?company_id=${companyId}${status ? `&status=${status}` : ""}`);

export const createAsset = (companyId: string, input: AssetCreateInput) => apiPost<Asset>(`/assets?company_id=${companyId}`, input);

export const getAsset = (companyId: string, assetId: string) => apiGet<Asset>(`/assets/${assetId}?company_id=${companyId}`);

export const transferAsset = (companyId: string, assetId: string, to_cost_center_id: string, reason?: string) =>
  apiPost<Asset>(`/assets/${assetId}/transfer?company_id=${companyId}`, { to_cost_center_id, reason });

export const disposeAsset = (
  companyId: string,
  assetId: string,
  disposal_type: DisposalType,
  disposal_date: string,
  proceeds = 0,
  proceeds_gl_account_id?: string,
  reason?: string,
) =>
  apiPost<DisposeAssetResult>(`/assets/${assetId}/dispose?company_id=${companyId}`, {
    disposal_type,
    disposal_date,
    proceeds,
    proceeds_gl_account_id,
    reason,
  });

export const runDepreciation = (companyId: string, period: string) =>
  apiPost<DepreciationRun>(`/assets/depreciation-run?company_id=${companyId}&period=${period}`);

export const getAssetRegister = (companyId: string, asOf: string) =>
  apiGet<AssetRegister>(`/assets/register?company_id=${companyId}&as_of=${asOf}`);
