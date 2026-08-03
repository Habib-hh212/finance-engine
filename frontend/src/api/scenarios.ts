import { apiDelete, apiGet, apiPost } from "./client";
import type { Scenario, ScenarioForecast } from "./types";

export const listScenarios = (companyId: string) => apiGet<Scenario[]>(`/scenarios?company_id=${companyId}`);

export const createScenario = (
  companyId: string,
  name: string,
  sales_growth_pct: number,
  expense_growth_pct: number,
  description?: string,
) =>
  apiPost<Scenario>(`/scenarios?company_id=${companyId}`, {
    name,
    description,
    sales_growth_pct,
    expense_growth_pct,
  });

export const deleteScenario = (scenarioId: string) => apiDelete<void>(`/scenarios/${scenarioId}`);

export const getScenarioForecast = (
  scenarioId: string,
  startPeriod: string,
  periods: number,
  dsoDays: number,
  dpoDays: number,
  collectionLagDays: number,
) =>
  apiGet<ScenarioForecast>(
    `/scenarios/${scenarioId}/forecast?start_period=${startPeriod}&periods=${periods}` +
      `&dso_days=${dsoDays}&dpo_days=${dpoDays}&collection_lag_days=${collectionLagDays}`,
  );
