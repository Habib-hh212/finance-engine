import { apiDownload, apiGet, apiPatch, apiPost } from "./client";
import type { Employee, Form16Summary, InvestmentDeclaration, PayrollRun, TaxRegime } from "./types";

export interface EmployeeInput {
  name: string;
  pan?: string;
  email?: string;
  date_of_joining: string;
  tax_regime: TaxRegime;
  basic_monthly: number;
  hra_monthly?: number;
  special_allowance_monthly?: number;
  other_allowance_monthly?: number;
  is_metro?: boolean;
}

export const listEmployees = (companyId: string) => apiGet<Employee[]>(`/employees?company_id=${companyId}`);
export const createEmployee = (companyId: string, input: EmployeeInput) => apiPost<Employee>(`/employees?company_id=${companyId}`, input);
export const updateEmployee = (companyId: string, employeeId: string, changes: Partial<EmployeeInput> & { is_active?: boolean }) =>
  apiPatch<Employee>(`/employees/${employeeId}?company_id=${companyId}`, changes);

export const upsertInvestmentDeclaration = (
  companyId: string,
  employeeId: string,
  financial_year: number,
  section_80c: number,
  section_80d: number,
  home_loan_interest: number,
  rent_paid_monthly: number,
) =>
  apiPost<InvestmentDeclaration>(`/employees/${employeeId}/investment-declarations?company_id=${companyId}`, {
    financial_year,
    section_80c,
    section_80d,
    home_loan_interest,
    rent_paid_monthly,
  });

export const listInvestmentDeclarations = (companyId: string, employeeId: string) =>
  apiGet<InvestmentDeclaration[]>(`/employees/${employeeId}/investment-declarations?company_id=${companyId}`);

export const listPayrollRuns = (companyId: string) => apiGet<PayrollRun[]>(`/payroll-runs?company_id=${companyId}`);

export const runPayroll = (companyId: string, period_month: number, period_year: number, cash_gl_account_id: string, run_date: string) =>
  apiPost<PayrollRun>(`/payroll-runs?company_id=${companyId}`, { period_month, period_year, cash_gl_account_id, run_date });

export const getForm16Summary = (companyId: string, employeeId: string, financialYear: number) =>
  apiGet<Form16Summary>(`/employees/${employeeId}/form16?company_id=${companyId}&financial_year=${financialYear}`);

export const downloadPayslipPdf = (companyId: string, payslipId: string) =>
  apiDownload(`/payslips/${payslipId}/pdf?company_id=${companyId}`, `payslip-${payslipId}.pdf`);

export const downloadForm16Pdf = (companyId: string, employeeId: string, financialYear: number) =>
  apiDownload(`/employees/${employeeId}/form16/pdf?company_id=${companyId}&financial_year=${financialYear}`, `form16-${employeeId}-FY${financialYear}.pdf`);
