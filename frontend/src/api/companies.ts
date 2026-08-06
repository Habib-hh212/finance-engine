import { apiGet, apiPatch, apiPost } from "./client";
import type { Company } from "./types";

export const listCompanies = () => apiGet<Company[]>("/companies");

export const createCompany = (name: string, base_currency: string) =>
  apiPost<Company>("/companies", { name, base_currency });

export const updateCompany = (companyId: string, changes: { home_state?: string | null }) =>
  apiPatch<Company>(`/companies/${companyId}`, changes);
