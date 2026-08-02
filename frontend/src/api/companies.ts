import { apiGet, apiPost } from "./client";
import type { Company } from "./types";

export const listCompanies = () => apiGet<Company[]>("/companies");

export const createCompany = (name: string, base_currency: string) =>
  apiPost<Company>("/companies", { name, base_currency });
