import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  FormControlLabel,
  Grid,
  IconButton,
  MenuItem,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import { TabPanel } from "../components/TabPanel";
import { useCompany } from "../context/CompanyContext";
import { listGLAccounts } from "../api/budgets";
import {
  createEmployee,
  downloadForm16Pdf,
  downloadPayslipPdf,
  getForm16Summary,
  listEmployees,
  listInvestmentDeclarations,
  listPayrollRuns,
  runPayroll,
  updateEmployee,
  upsertInvestmentDeclaration,
} from "../api/payroll";
import type { Employee, Form16Summary, GLAccount, InvestmentDeclaration, PayrollRun, TaxRegime } from "../api/types";

const fmt = (v: number) => v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function todayValue() {
  return new Date().toISOString().slice(0, 10);
}

function currentFinancialYear() {
  const now = new Date();
  return now.getMonth() + 1 >= 4 ? now.getFullYear() : now.getFullYear() - 1;
}

export function PayrollPage() {
  const { company } = useCompany();
  const [tab, setTab] = useState(0);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [glAccounts, setGlAccounts] = useState<GLAccount[]>([]);
  const [runs, setRuns] = useState<PayrollRun[]>([]);
  const [error, setError] = useState<string | null>(null);

  // New employee form
  const [empName, setEmpName] = useState("");
  const [empPan, setEmpPan] = useState("");
  const [empDoj, setEmpDoj] = useState(todayValue());
  const [empRegime, setEmpRegime] = useState<TaxRegime>("new");
  const [empBasic, setEmpBasic] = useState("");
  const [empHra, setEmpHra] = useState("");
  const [empSpecial, setEmpSpecial] = useState("");
  const [empOther, setEmpOther] = useState("");
  const [empMetro, setEmpMetro] = useState(false);

  // Investment declaration form
  const [declEmployeeId, setDeclEmployeeId] = useState("");
  const [declFy, setDeclFy] = useState(String(currentFinancialYear()));
  const [decl80c, setDecl80c] = useState("");
  const [decl80d, setDecl80d] = useState("");
  const [declHomeLoan, setDeclHomeLoan] = useState("");
  const [declRent, setDeclRent] = useState("");
  const [declSaved, setDeclSaved] = useState<InvestmentDeclaration | null>(null);
  const [declError, setDeclError] = useState<string | null>(null);

  // Run payroll form
  const [runMonth, setRunMonth] = useState(String(new Date().getMonth() + 1));
  const [runYear, setRunYear] = useState(String(new Date().getFullYear()));
  const [runCashAccount, setRunCashAccount] = useState("");
  const [runDate, setRunDate] = useState(todayValue());
  const [runError, setRunError] = useState<string | null>(null);
  const [lastRun, setLastRun] = useState<PayrollRun | null>(null);

  // Form 16
  const [form16EmployeeId, setForm16EmployeeId] = useState("");
  const [form16Fy, setForm16Fy] = useState(String(currentFinancialYear()));
  const [form16Summary, setForm16Summary] = useState<Form16Summary | null>(null);
  const [form16Error, setForm16Error] = useState<string | null>(null);

  const load = async () => {
    if (!company) return;
    setError(null);
    try {
      const [emps, accounts, payrollRuns] = await Promise.all([listEmployees(company.id), listGLAccounts(company.id), listPayrollRuns(company.id)]);
      setEmployees(emps);
      setGlAccounts(accounts);
      setRuns(payrollRuns);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load payroll data");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);

  const employeeName = (id: string) => employees.find((e) => e.id === id)?.name ?? "—";

  const handleCreateEmployee = async () => {
    if (!company || !empName || !empDoj || !empBasic) return;
    setError(null);
    try {
      await createEmployee(company.id, {
        name: empName,
        pan: empPan || undefined,
        date_of_joining: empDoj,
        tax_regime: empRegime,
        basic_monthly: Number(empBasic),
        hra_monthly: Number(empHra || 0),
        special_allowance_monthly: Number(empSpecial || 0),
        other_allowance_monthly: Number(empOther || 0),
        is_metro: empMetro,
      });
      setEmpName("");
      setEmpPan("");
      setEmpBasic("");
      setEmpHra("");
      setEmpSpecial("");
      setEmpOther("");
      setEmpMetro(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add employee");
    }
  };

  const handleToggleActive = async (employee: Employee) => {
    if (!company) return;
    setError(null);
    try {
      await updateEmployee(company.id, employee.id, { is_active: !employee.is_active });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update employee");
    }
  };

  const loadDeclaration = async (employeeId: string, fy: string) => {
    if (!company || !employeeId || !fy) return;
    try {
      const list = await listInvestmentDeclarations(company.id, employeeId);
      setDeclSaved(list.find((d) => d.financial_year === Number(fy)) ?? null);
    } catch {
      setDeclSaved(null);
    }
  };

  const handleSelectDeclarationEmployee = (employeeId: string) => {
    setDeclEmployeeId(employeeId);
    loadDeclaration(employeeId, declFy);
  };

  const handleSaveDeclaration = async () => {
    if (!company || !declEmployeeId || !declFy) return;
    setDeclError(null);
    try {
      const saved = await upsertInvestmentDeclaration(
        company.id,
        declEmployeeId,
        Number(declFy),
        Number(decl80c || 0),
        Number(decl80d || 0),
        Number(declHomeLoan || 0),
        Number(declRent || 0),
      );
      setDeclSaved(saved);
    } catch (err) {
      setDeclError(err instanceof Error ? err.message : "Failed to save investment declaration");
    }
  };

  const handleRunPayroll = async () => {
    if (!company || !runMonth || !runYear || !runCashAccount || !runDate) return;
    setRunError(null);
    try {
      const run = await runPayroll(company.id, Number(runMonth), Number(runYear), runCashAccount, runDate);
      setLastRun(run);
      await load();
    } catch (err) {
      setRunError(err instanceof Error ? err.message : "Failed to run payroll");
    }
  };

  const handleLoadForm16 = async () => {
    if (!company || !form16EmployeeId || !form16Fy) return;
    setForm16Error(null);
    try {
      setForm16Summary(await getForm16Summary(company.id, form16EmployeeId, Number(form16Fy)));
    } catch (err) {
      setForm16Summary(null);
      setForm16Error(err instanceof Error ? err.message : "Failed to load Form 16 summary");
    }
  };

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Payroll (India)
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)}>
          <Tab label="Employees" />
          <Tab label="Run Payroll" />
          <Tab label="Form 16" />
          <Tab label="Help" />
        </Tabs>
      </Box>

      <TabPanel value={tab} index={0}>
        <Stack spacing={2}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                New Employee
              </Typography>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 6, md: 2.4 }}>
                  <TextField label="Name" size="small" fullWidth value={empName} onChange={(e) => setEmpName(e.target.value)} />
                </Grid>
                <Grid size={{ xs: 6, sm: 3, md: 1.6 }}>
                  <TextField label="PAN" size="small" fullWidth value={empPan} onChange={(e) => setEmpPan(e.target.value)} />
                </Grid>
                <Grid size={{ xs: 6, sm: 3, md: 2 }}>
                  <TextField
                    label="Date of joining"
                    type="date"
                    size="small"
                    fullWidth
                    value={empDoj}
                    onChange={(e) => setEmpDoj(e.target.value)}
                    slotProps={{ inputLabel: { shrink: true } }}
                  />
                </Grid>
                <Grid size={{ xs: 6, sm: 3, md: 1.6 }}>
                  <TextField select label="Tax regime" size="small" fullWidth value={empRegime} onChange={(e) => setEmpRegime(e.target.value as TaxRegime)}>
                    <MenuItem value="new">New regime</MenuItem>
                    <MenuItem value="old">Old regime</MenuItem>
                  </TextField>
                </Grid>
                <Grid size={{ xs: 6, sm: 3, md: 1.6 }}>
                  <TextField label="Basic / month" type="number" size="small" fullWidth value={empBasic} onChange={(e) => setEmpBasic(e.target.value)} />
                </Grid>
                <Grid size={{ xs: 6, sm: 3, md: 1.6 }}>
                  <TextField label="HRA / month" type="number" size="small" fullWidth value={empHra} onChange={(e) => setEmpHra(e.target.value)} />
                </Grid>
                <Grid size={{ xs: 6, sm: 3, md: 1.8 }}>
                  <TextField label="Special allowance" type="number" size="small" fullWidth value={empSpecial} onChange={(e) => setEmpSpecial(e.target.value)} />
                </Grid>
                <Grid size={{ xs: 6, sm: 3, md: 1.8 }}>
                  <TextField label="Other allowance" type="number" size="small" fullWidth value={empOther} onChange={(e) => setEmpOther(e.target.value)} />
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 3 }} sx={{ display: "flex", alignItems: "center" }}>
                  <FormControlLabel control={<Checkbox checked={empMetro} onChange={(e) => setEmpMetro(e.target.checked)} />} label="Metro city (HRA)" />
                </Grid>
              </Grid>
              <Button variant="contained" sx={{ mt: 2 }} onClick={handleCreateEmployee} disabled={!empName || !empDoj || !empBasic}>
                Add employee
              </Button>
            </CardContent>
          </Card>

          <TableContainer component={Card} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Regime</TableCell>
                  <TableCell align="right">Basic</TableCell>
                  <TableCell align="right">HRA</TableCell>
                  <TableCell align="right">Special</TableCell>
                  <TableCell align="right">Other</TableCell>
                  <TableCell align="center">Active</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {employees.map((e) => (
                  <TableRow key={e.id}>
                    <TableCell>
                      {e.name} {e.pan && <Chip size="small" label={e.pan} sx={{ ml: 1 }} />}
                    </TableCell>
                    <TableCell>{e.tax_regime === "old" ? "Old" : "New"}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                      {fmt(e.basic_monthly)}
                    </TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                      {fmt(e.hra_monthly)}
                    </TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                      {fmt(e.special_allowance_monthly)}
                    </TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                      {fmt(e.other_allowance_monthly)}
                    </TableCell>
                    <TableCell align="center">
                      <Button size="small" onClick={() => handleToggleActive(e)}>
                        {e.is_active ? "Deactivate" : "Activate"}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {employees.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7}>
                      <Typography variant="body2" color="text.secondary">
                        No employees yet.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          <Typography variant="h6">Investment Declaration (Old Regime)</Typography>
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center" }}>
                <TextField select label="Employee" size="small" value={declEmployeeId} onChange={(e) => handleSelectDeclarationEmployee(e.target.value)} sx={{ minWidth: 180 }}>
                  {employees.map((e) => (
                    <MenuItem key={e.id} value={e.id}>
                      {e.name}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  label="Financial year"
                  size="small"
                  value={declFy}
                  onChange={(e) => {
                    setDeclFy(e.target.value);
                    loadDeclaration(declEmployeeId, e.target.value);
                  }}
                  sx={{ width: 130 }}
                />
                <TextField label="Section 80C" type="number" size="small" value={decl80c} onChange={(e) => setDecl80c(e.target.value)} sx={{ width: 130 }} />
                <TextField label="Section 80D" type="number" size="small" value={decl80d} onChange={(e) => setDecl80d(e.target.value)} sx={{ width: 130 }} />
                <TextField label="Home loan interest" type="number" size="small" value={declHomeLoan} onChange={(e) => setDeclHomeLoan(e.target.value)} sx={{ width: 150 }} />
                <TextField label="Rent paid / month" type="number" size="small" value={declRent} onChange={(e) => setDeclRent(e.target.value)} sx={{ width: 150 }} />
                <Button variant="contained" onClick={handleSaveDeclaration} disabled={!declEmployeeId || !declFy}>
                  Save
                </Button>
              </Stack>
              {declError && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {declError}
                </Alert>
              )}
              {declSaved && (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
                  Saved: 80C {fmt(declSaved.section_80c)} · 80D {fmt(declSaved.section_80d)} · Home loan interest{" "}
                  {fmt(declSaved.home_loan_interest)} · Rent/month {fmt(declSaved.rent_paid_monthly)}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Stack>
      </TabPanel>

      <TabPanel value={tab} index={1}>
        <Stack spacing={2}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Run Payroll
              </Typography>
              <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center" }}>
                <TextField label="Month (1-12)" type="number" size="small" value={runMonth} onChange={(e) => setRunMonth(e.target.value)} sx={{ width: 130 }} />
                <TextField label="Year" type="number" size="small" value={runYear} onChange={(e) => setRunYear(e.target.value)} sx={{ width: 110 }} />
                <TextField select label="Cash account" size="small" value={runCashAccount} onChange={(e) => setRunCashAccount(e.target.value)} sx={{ minWidth: 170 }}>
                  {glAccounts.map((g) => (
                    <MenuItem key={g.id} value={g.id}>
                      {g.code} {g.name}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  label="Run date"
                  type="date"
                  size="small"
                  value={runDate}
                  onChange={(e) => setRunDate(e.target.value)}
                  slotProps={{ inputLabel: { shrink: true } }}
                />
                <Button variant="contained" onClick={handleRunPayroll} disabled={!runMonth || !runYear || !runCashAccount || !runDate}>
                  Run payroll
                </Button>
              </Stack>
              {runError && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {runError}
                </Alert>
              )}
              {lastRun && (
                <TableContainer sx={{ mt: 2 }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Employee</TableCell>
                        <TableCell align="right">Gross</TableCell>
                        <TableCell align="right">PF (emp.)</TableCell>
                        <TableCell align="right">ESI (emp.)</TableCell>
                        <TableCell align="right">Prof. Tax</TableCell>
                        <TableCell align="right">TDS</TableCell>
                        <TableCell align="right">Net Pay</TableCell>
                        <TableCell align="center">Payslip</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {lastRun.payslips.map((p) => (
                        <TableRow key={p.id}>
                          <TableCell>{employeeName(p.employee_id)}</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                            {fmt(p.gross_pay)}
                          </TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                            {fmt(p.pf_employee)}
                          </TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                            {fmt(p.esi_employee)}
                          </TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                            {fmt(p.professional_tax)}
                          </TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                            {fmt(p.tds_amount)}
                          </TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>
                            {fmt(p.net_pay)}
                          </TableCell>
                          <TableCell align="center">
                            <IconButton size="small" onClick={() => company && downloadPayslipPdf(company.id, p.id)}>
                              <PictureAsPdfIcon fontSize="small" />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>

          <Typography variant="h6">Past Payroll Runs</Typography>
          <TableContainer component={Card} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Period</TableCell>
                  <TableCell align="right">Employees</TableCell>
                  <TableCell align="right">Total Net Pay</TableCell>
                  <TableCell>Run date</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {runs.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell>
                      {r.period_month}/{r.period_year}
                    </TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                      {r.payslips.length}
                    </TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                      {fmt(r.payslips.reduce((sum, p) => sum + p.net_pay, 0))}
                    </TableCell>
                    <TableCell>{r.run_date}</TableCell>
                  </TableRow>
                ))}
                {runs.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4}>
                      <Typography variant="body2" color="text.secondary">
                        No payroll runs yet.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Stack>
      </TabPanel>

      <TabPanel value={tab} index={2}>
        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>
              Form 16 (Annual TDS Certificate)
            </Typography>
            <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center" }}>
              <TextField select label="Employee" size="small" value={form16EmployeeId} onChange={(e) => setForm16EmployeeId(e.target.value)} sx={{ minWidth: 180 }}>
                {employees.map((e) => (
                  <MenuItem key={e.id} value={e.id}>
                    {e.name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField label="Financial year" size="small" value={form16Fy} onChange={(e) => setForm16Fy(e.target.value)} sx={{ width: 130 }} />
              <Button variant="contained" onClick={handleLoadForm16} disabled={!form16EmployeeId || !form16Fy}>
                View summary
              </Button>
              <Button
                variant="outlined"
                startIcon={<PictureAsPdfIcon />}
                disabled={!form16EmployeeId || !form16Fy}
                onClick={() => company && downloadForm16Pdf(company.id, form16EmployeeId, Number(form16Fy))}
              >
                Download PDF
              </Button>
            </Stack>
            {form16Error && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {form16Error}
              </Alert>
            )}
            {form16Summary && (
              <Stack spacing={2} sx={{ mt: 2 }}>
                <Typography variant="body2">
                  Total gross salary: <strong>{fmt(form16Summary.total_gross)}</strong> &middot; Total TDS deducted:{" "}
                  <strong>{fmt(form16Summary.total_tds)}</strong> &middot; Regime: {form16Summary.regime === "old" ? "Old" : "New"}
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Period</TableCell>
                        <TableCell align="right">Gross Pay</TableCell>
                        <TableCell align="right">TDS Deducted</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {form16Summary.months.map((m) => (
                        <TableRow key={`${m.period_month}-${m.period_year}`}>
                          <TableCell>
                            {m.period_month}/{m.period_year}
                          </TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                            {fmt(m.gross_pay)}
                          </TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                            {fmt(m.tds_amount)}
                          </TableCell>
                        </TableRow>
                      ))}
                      {form16Summary.months.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={3}>
                            <Typography variant="body2" color="text.secondary">
                              No payroll runs found for this financial year.
                            </Typography>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Stack>
            )}
          </CardContent>
        </Card>
      </TabPanel>

      <TabPanel value={tab} index={3}>
        <Stack spacing={2}>
          <Typography variant="body2">
            Employee master, Section 192 salary TDS (old vs. new regime, HRA exemption, Chapter VI-A deductions),
            Provident Fund, ESI, and a simplified Professional Tax slab. Running payroll for a month posts one
            journal entry — salary expense and the employer's own PF/ESI contribution debited, every statutory
            payable plus the net cash actually paid credited — and disburses net pay from the cash account you pick,
            same-day.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Tag G/L accounts for <code>salary_expense</code>, <code>pf_payable</code>, <code>esi_payable</code>,{" "}
            <code>professional_tax_payable</code>, and <code>tds_payable</code> on the Chart of Accounts page before
            running payroll.
          </Typography>
          <Typography variant="subtitle2">Investment Declaration</Typography>
          <Typography variant="body2" color="text.secondary">
            Only affects TDS for employees on the old regime — Section 80C (cap ₹1,50,000), Section 80D (cap
            ₹25,000), home loan interest under Section 24(b) (cap ₹2,00,000), and rent paid (feeds the HRA
            exemption calculation).
          </Typography>
          <Typography variant="subtitle2">Form 16</Typography>
          <Typography variant="body2" color="text.secondary">
            Aggregates gross pay and TDS deducted across every payroll run in a financial year (India's FY runs
            April–March) into the annual TDS certificate you'd hand an employee.
          </Typography>
        </Stack>
      </TabPanel>
    </Stack>
  );
}
