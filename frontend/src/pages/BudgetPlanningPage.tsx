import { useEffect, useMemo, useState } from "react";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  IconButton,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { AgGridReact } from "ag-grid-react";
import type { ColDef, ValueSetterParams } from "ag-grid-community";
import { AllCommunityModule, ModuleRegistry, themeQuartz } from "ag-grid-community";
import { useCompany } from "../context/CompanyContext";
import {
  addBudgetLines,
  approveBudget,
  createBudget,
  createGLAccount,
  deleteBudgetLine,
  getBudget,
  getCapitalAppraisal,
  getFlexibleVariance,
  listBudgets,
  listBudgetVersions,
  listGLAccounts,
  rejectBudget,
  rollForwardBudget,
  submitBudget,
  updateBudgetLine,
  updateGLAccount,
} from "../api/budgets";
import type {
  Budget,
  BudgetDetail,
  BudgetLine,
  BudgetStatus,
  BudgetType,
  BudgetVersion,
  CapitalAppraisalRow,
  FlexibleVarianceRow,
  GLAccount,
  GLCategory,
  GLForecastRole,
} from "../api/types";

ModuleRegistry.registerModules([AllCommunityModule]);

const STATUS_COLOR: Record<BudgetStatus, "default" | "info" | "success" | "error"> = {
  draft: "default",
  pending_manager: "info",
  pending_finance: "info",
  pending_cfo: "info",
  approved: "success",
  rejected: "error",
};

const NEXT_ROLE: Record<BudgetStatus, string | null> = {
  draft: null,
  pending_manager: "Manager",
  pending_finance: "Finance",
  pending_cfo: "CFO",
  approved: null,
  rejected: null,
};

const BUDGET_TYPE_LABEL: Record<BudgetType, string> = {
  revenue: "Revenue",
  expense: "Expense",
  master: "Master",
  zero_based: "Zero-Based",
  flexible: "Flexible",
  rolling: "Rolling",
  capital: "Capital",
};

const fmt = (n: number | null) => (n === null || n === undefined ? "—" : n.toLocaleString(undefined, { maximumFractionDigits: 2 }));

interface DeleteLineCellRendererProps {
  data: BudgetLine;
  context: { onDelete: (lineId: string) => void };
}

function DeleteLineCellRenderer({ data, context }: DeleteLineCellRendererProps) {
  return (
    <IconButton size="small" onClick={() => context.onDelete(data.id)} aria-label="Delete line">
      <DeleteIcon fontSize="small" />
    </IconButton>
  );
}

export function BudgetPlanningPage() {
  const { company } = useCompany();
  const [glAccounts, setGlAccounts] = useState<GLAccount[]>([]);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [selected, setSelected] = useState<BudgetDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [glCode, setGlCode] = useState("");
  const [glName, setGlName] = useState("");
  const [glCategory, setGlCategory] = useState<GLCategory>("expense");
  const [glForecastRole, setGlForecastRole] = useState<GLForecastRole | "">("");

  const [budgetName, setBudgetName] = useState("");
  const [budgetType, setBudgetType] = useState<BudgetType>("expense");
  const [fiscalYear, setFiscalYear] = useState(String(new Date().getFullYear()));
  const [rollingWindowMonths, setRollingWindowMonths] = useState("12");

  const [lineGlId, setLineGlId] = useState("");
  const [linePeriod, setLinePeriod] = useState("");
  const [lineAmount, setLineAmount] = useState("");
  const [lineJustification, setLineJustification] = useState("");
  const [lineVariableRate, setLineVariableRate] = useState("");
  const [lineUsefulLife, setLineUsefulLife] = useState("");
  const [lineAnnualCashFlow, setLineAnnualCashFlow] = useState("");

  const [actorName, setActorName] = useState("");
  const [comment, setComment] = useState("");

  const [flexVariance, setFlexVariance] = useState<FlexibleVarianceRow[]>([]);
  const [capitalRows, setCapitalRows] = useState<CapitalAppraisalRow[]>([]);
  const [versions, setVersions] = useState<BudgetVersion[]>([]);

  const loadAll = async () => {
    if (!company) return;
    const [gls, bgs] = await Promise.all([listGLAccounts(company.id), listBudgets(company.id)]);
    setGlAccounts(gls);
    setBudgets(bgs);
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);

  const openBudget = async (id: string) => {
    setError(null);
    const detail = await getBudget(id);
    setSelected(detail);
    setFlexVariance(detail.type === "flexible" ? await getFlexibleVariance(id) : []);
    setCapitalRows(detail.type === "capital" ? await getCapitalAppraisal(id) : []);
    setVersions(await listBudgetVersions(id));
  };

  const glNameFor = useMemo(() => {
    const map = new Map(glAccounts.map((g) => [g.id, `${g.code} ${g.name}`]));
    return (id: string) => map.get(id) ?? id;
  }, [glAccounts]);

  const runAction = async (fn: () => Promise<unknown>) => {
    setError(null);
    try {
      await fn();
      if (selected) await openBudget(selected.id);
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    }
  };

  const handleCreateGl = () =>
    runAction(async () => {
      if (!company || !glCode || !glName) return;
      await createGLAccount(company.id, glCode, glName, glCategory, glForecastRole || undefined);
      setGlCode("");
      setGlName("");
      setGlForecastRole("");
    });

  const handleChangeGlRole = (accountId: string, role: GLForecastRole | "") =>
    runAction(() => updateGLAccount(accountId, role || null));

  const rolesForCategory = (category: GLCategory): GLForecastRole[] => {
    if (category === "asset") return ["cash", "accounts_receivable"];
    if (category === "liability") return ["accounts_payable"];
    return [];
  };

  const handleCreateBudget = () =>
    runAction(async () => {
      if (!company || !budgetName) return;
      const created = await createBudget(
        company.id,
        budgetName,
        budgetType,
        Number(fiscalYear),
        company.base_currency,
        budgetType === "rolling" ? Number(rollingWindowMonths) : undefined,
      );
      setBudgetName("");
      await openBudget(created.id);
    });

  const handleAddLine = () =>
    runAction(async () => {
      if (!selected || !lineGlId || !linePeriod || !lineAmount) return;
      await addBudgetLines(selected.id, [
        {
          gl_account_id: lineGlId,
          period: `${linePeriod}-01`,
          amount: Number(lineAmount),
          justification: selected.type === "zero_based" ? lineJustification || undefined : undefined,
          variable_rate_per_unit: selected.type === "flexible" && lineVariableRate ? Number(lineVariableRate) : undefined,
          useful_life_years: selected.type === "capital" && lineUsefulLife ? Number(lineUsefulLife) : undefined,
          annual_cash_flow: selected.type === "capital" && lineAnnualCashFlow ? Number(lineAnnualCashFlow) : undefined,
        },
      ]);
      setLineAmount("");
      setLineJustification("");
      setLineVariableRate("");
      setLineUsefulLife("");
      setLineAnnualCashFlow("");
    });

  const linesEditable = selected?.status === "draft" || selected?.status === "rejected";

  const handleDeleteLine = (lineId: string) => {
    if (!selected) return;
    runAction(() => deleteBudgetLine(selected.id, lineId));
  };

  const handleCellValueChanged = (field: keyof BudgetLine) => (params: ValueSetterParams) => {
    if (!selected) return true;
    const raw = params.newValue;
    const numericFields = new Set(["amount", "variable_rate_per_unit", "useful_life_years", "annual_cash_flow"]);
    const value = numericFields.has(field) ? (raw === "" || raw === null || raw === undefined ? undefined : Number(raw)) : raw;
    (params.data as BudgetLine)[field] = value as never;
    runAction(() => updateBudgetLine(selected.id, params.data.id, { [field]: value }));
    return true;
  };

  const columnDefs: ColDef[] = useMemo(() => {
    const base: ColDef[] = [
      { field: "gl_account_id", headerName: "GL Account", valueFormatter: (p) => glNameFor(p.value), flex: 2 },
      { field: "period", headerName: "Period", flex: 1 },
      {
        field: "amount",
        headerName: "Amount",
        flex: 1,
        valueFormatter: (p) => Number(p.value).toLocaleString(),
        editable: linesEditable,
        valueSetter: handleCellValueChanged("amount"),
      },
      { field: "currency", headerName: "Currency", flex: 1 },
    ];
    if (selected?.type === "zero_based") {
      base.push({
        field: "justification",
        headerName: "Justification",
        flex: 2,
        editable: linesEditable,
        valueSetter: handleCellValueChanged("justification"),
      });
    }
    if (selected?.type === "flexible") {
      base.push({
        field: "variable_rate_per_unit",
        headerName: "Rate/unit",
        flex: 1,
        editable: linesEditable,
        valueSetter: handleCellValueChanged("variable_rate_per_unit"),
      });
    }
    if (selected?.type === "capital") {
      base.push({
        field: "useful_life_years",
        headerName: "Useful life (yrs)",
        flex: 1,
        editable: linesEditable,
        valueSetter: handleCellValueChanged("useful_life_years"),
      });
      base.push({
        field: "annual_cash_flow",
        headerName: "Annual cash flow",
        flex: 1,
        editable: linesEditable,
        valueSetter: handleCellValueChanged("annual_cash_flow"),
      });
    }
    if (linesEditable) {
      base.push({
        headerName: "",
        colId: "_delete",
        width: 56,
        sortable: false,
        filter: false,
        cellRenderer: DeleteLineCellRenderer,
      });
    }
    return base;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected?.type, selected?.status, glNameFor]);

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Budget Planning
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Stack spacing={2}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle1" gutterBottom>
                  GL Accounts
                </Typography>
                <Stack spacing={1}>
                  {glAccounts.map((g) => {
                    const options = rolesForCategory(g.category);
                    return (
                      <Stack key={g.id} direction="row" sx={{ alignItems: "center", flexWrap: "wrap" }} spacing={1}>
                        <Typography variant="body2">
                          {g.code} — {g.name}
                        </Typography>
                        <Chip size="small" label={g.category} />
                        {options.length > 0 && (
                          <TextField
                            select
                            size="small"
                            value={g.forecast_role ?? ""}
                            onChange={(e) => handleChangeGlRole(g.id, e.target.value as GLForecastRole | "")}
                            sx={{ minWidth: 150 }}
                            slotProps={{ select: { displayEmpty: true } }}
                          >
                            <MenuItem value="">
                              <em>No forecast role</em>
                            </MenuItem>
                            {options.map((role) => (
                              <MenuItem key={role} value={role}>
                                {role.replace(/_/g, " ")}
                              </MenuItem>
                            ))}
                          </TextField>
                        )}
                      </Stack>
                    );
                  })}
                </Stack>
                <Stack spacing={1} sx={{ mt: 2 }}>
                  <TextField label="Code" size="small" value={glCode} onChange={(e) => setGlCode(e.target.value)} />
                  <TextField label="Name" size="small" value={glName} onChange={(e) => setGlName(e.target.value)} />
                  <TextField select label="Category" size="small" value={glCategory} onChange={(e) => { setGlCategory(e.target.value as GLCategory); setGlForecastRole(""); }}>
                    <MenuItem value="revenue">Revenue</MenuItem>
                    <MenuItem value="expense">Expense</MenuItem>
                    <MenuItem value="asset">Asset</MenuItem>
                    <MenuItem value="liability">Liability</MenuItem>
                    <MenuItem value="equity">Equity</MenuItem>
                  </TextField>
                  {rolesForCategory(glCategory).length > 0 && (
                    <TextField
                      select
                      label="Forecast role (optional)"
                      size="small"
                      value={glForecastRole}
                      onChange={(e) => setGlForecastRole(e.target.value as GLForecastRole | "")}
                      slotProps={{ select: { displayEmpty: true } }}
                    >
                      <MenuItem value="">
                        <em>None</em>
                      </MenuItem>
                      {rolesForCategory(glCategory).map((role) => (
                        <MenuItem key={role} value={role}>
                          {role.replace(/_/g, " ")}
                        </MenuItem>
                      ))}
                    </TextField>
                  )}
                  <Button variant="outlined" size="small" onClick={handleCreateGl} disabled={!glCode || !glName}>
                    Add GL account
                  </Button>
                </Stack>
              </CardContent>
            </Card>

            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle1" gutterBottom>
                  New Budget
                </Typography>
                <Stack spacing={1}>
                  <TextField label="Name" size="small" value={budgetName} onChange={(e) => setBudgetName(e.target.value)} />
                  <TextField select label="Type" size="small" value={budgetType} onChange={(e) => setBudgetType(e.target.value as BudgetType)}>
                    <MenuItem value="revenue">Revenue</MenuItem>
                    <MenuItem value="expense">Expense</MenuItem>
                    <MenuItem value="master">Master</MenuItem>
                    <MenuItem value="zero_based">Zero-Based</MenuItem>
                    <MenuItem value="flexible">Flexible</MenuItem>
                    <MenuItem value="rolling">Rolling</MenuItem>
                    <MenuItem value="capital">Capital</MenuItem>
                  </TextField>
                  <TextField label="Fiscal year" size="small" value={fiscalYear} onChange={(e) => setFiscalYear(e.target.value)} />
                  {budgetType === "rolling" && (
                    <TextField
                      label="Rolling window (months)"
                      type="number"
                      size="small"
                      value={rollingWindowMonths}
                      onChange={(e) => setRollingWindowMonths(e.target.value)}
                    />
                  )}
                  <Button variant="contained" size="small" onClick={handleCreateBudget} disabled={!budgetName}>
                    Create budget
                  </Button>
                </Stack>
              </CardContent>
            </Card>

            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle1" gutterBottom>
                  Budgets
                </Typography>
                <Stack spacing={1}>
                  {budgets.map((b) => (
                    <Box
                      key={b.id}
                      onClick={() => openBudget(b.id)}
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        p: 1,
                        borderRadius: 1,
                        cursor: "pointer",
                        bgcolor: selected?.id === b.id ? "action.selected" : "transparent",
                        "&:hover": { bgcolor: "action.hover" },
                      }}
                    >
                      <Typography variant="body2">{b.name}</Typography>
                      <Chip size="small" label={b.status} color={STATUS_COLOR[b.status]} />
                    </Box>
                  ))}
                  {budgets.length === 0 && (
                    <Typography variant="body2" color="text.secondary">
                      No budgets yet.
                    </Typography>
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Stack>
        </Grid>

        <Grid size={{ xs: 12, md: 8 }}>
          {!selected ? (
            <Alert severity="info">Select or create a budget to see its detail.</Alert>
          ) : (
            <Stack spacing={2}>
              <Card variant="outlined">
                <CardContent>
                  <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center" }}>
                    <Box>
                      <Typography variant="h6">{selected.name}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {BUDGET_TYPE_LABEL[selected.type]} · FY{selected.fiscal_year} · {selected.currency}
                        {selected.type === "rolling" && selected.rolling_window_months
                          ? ` · ${selected.rolling_window_months}-month window`
                          : ""}
                      </Typography>
                    </Box>
                    <Chip label={selected.status} color={STATUS_COLOR[selected.status]} />
                  </Stack>
                </CardContent>
              </Card>

              {linesEditable && (
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="subtitle2" gutterBottom>
                      Add line
                    </Typography>
                    <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", alignItems: "center" }}>
                      <TextField select label="GL Account" size="small" value={lineGlId} onChange={(e) => setLineGlId(e.target.value)} sx={{ minWidth: 200 }}>
                        {glAccounts.map((g) => (
                          <MenuItem key={g.id} value={g.id}>
                            {g.code} {g.name}
                          </MenuItem>
                        ))}
                      </TextField>
                      <TextField
                        label="Period"
                        type="month"
                        size="small"
                        value={linePeriod}
                        onChange={(e) => setLinePeriod(e.target.value)}
                        slotProps={{ inputLabel: { shrink: true } }}
                      />
                      <TextField
                        label={selected.type === "capital" ? "Investment" : "Amount"}
                        type="number"
                        size="small"
                        value={lineAmount}
                        onChange={(e) => setLineAmount(e.target.value)}
                      />
                      {selected.type === "zero_based" && (
                        <TextField
                          label="Justification"
                          size="small"
                          value={lineJustification}
                          onChange={(e) => setLineJustification(e.target.value)}
                          sx={{ minWidth: 220 }}
                        />
                      )}
                      {selected.type === "flexible" && (
                        <TextField
                          label="Variable rate/unit"
                          type="number"
                          size="small"
                          value={lineVariableRate}
                          onChange={(e) => setLineVariableRate(e.target.value)}
                        />
                      )}
                      {selected.type === "capital" && (
                        <>
                          <TextField
                            label="Useful life (yrs)"
                            type="number"
                            size="small"
                            value={lineUsefulLife}
                            onChange={(e) => setLineUsefulLife(e.target.value)}
                          />
                          <TextField
                            label="Annual cash flow"
                            type="number"
                            size="small"
                            value={lineAnnualCashFlow}
                            onChange={(e) => setLineAnnualCashFlow(e.target.value)}
                          />
                        </>
                      )}
                      <Button
                        variant="outlined"
                        onClick={handleAddLine}
                        disabled={
                          !lineGlId ||
                          !linePeriod ||
                          !lineAmount ||
                          (selected.type === "zero_based" && !lineJustification)
                        }
                      >
                        Add
                      </Button>
                    </Stack>
                  </CardContent>
                </Card>
              )}

              <Box sx={{ height: 260, width: "100%" }}>
                <AgGridReact
                  rowData={selected.lines}
                  columnDefs={columnDefs}
                  theme={themeQuartz}
                  getRowId={(p) => p.data.id}
                  context={{ onDelete: handleDeleteLine }}
                />
              </Box>

              {selected.type === "rolling" && selected.status === "draft" && (
                <Card variant="outlined">
                  <CardContent>
                    <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center" }}>
                      <Typography variant="body2" color="text.secondary">
                        Roll the window forward one month — copies the latest period's lines and drops the oldest.
                      </Typography>
                      <Button variant="outlined" onClick={() => runAction(() => rollForwardBudget(selected.id))}>
                        Roll forward
                      </Button>
                    </Stack>
                  </CardContent>
                </Card>
              )}

              {selected.type === "flexible" && flexVariance.length > 0 && (
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="subtitle2" gutterBottom>
                      Flexible budget variance
                    </Typography>
                    <Box sx={{ overflowX: "auto" }}>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Account</TableCell>
                            <TableCell>Period</TableCell>
                            <TableCell align="right">Static</TableCell>
                            <TableCell align="right">Flexed</TableCell>
                            <TableCell align="right">Actual</TableCell>
                            <TableCell align="right">Spending var.</TableCell>
                            <TableCell align="right">Volume var.</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {flexVariance.map((row, i) => (
                            <TableRow key={i}>
                              <TableCell>
                                {row.gl_account_code} {row.gl_account_name}
                              </TableCell>
                              <TableCell>{row.period}</TableCell>
                              <TableCell align="right">{fmt(row.static_amount)}</TableCell>
                              <TableCell align="right">{fmt(row.flexed_amount)}</TableCell>
                              <TableCell align="right">{fmt(row.actual_amount)}</TableCell>
                              <TableCell align="right">{fmt(row.spending_variance)}</TableCell>
                              <TableCell align="right">{fmt(row.volume_variance)}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </Box>
                  </CardContent>
                </Card>
              )}

              {selected.type === "capital" && capitalRows.length > 0 && (
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="subtitle2" gutterBottom>
                      Capital appraisal
                    </Typography>
                    <Box sx={{ overflowX: "auto" }}>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Account</TableCell>
                            <TableCell align="right">Investment</TableCell>
                            <TableCell align="right">Payback (yrs)</TableCell>
                            <TableCell align="right">Total cash flow</TableCell>
                            <TableCell align="right">Net gain</TableCell>
                            <TableCell align="right">ROI %</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {capitalRows.map((row, i) => (
                            <TableRow key={i}>
                              <TableCell>
                                {row.gl_account_code} {row.gl_account_name}
                              </TableCell>
                              <TableCell align="right">{fmt(row.investment)}</TableCell>
                              <TableCell align="right">{fmt(row.payback_period_years)}</TableCell>
                              <TableCell align="right">{fmt(row.total_cash_flow)}</TableCell>
                              <TableCell align="right">{fmt(row.net_gain)}</TableCell>
                              <TableCell align="right">{fmt(row.roi_pct)}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </Box>
                  </CardContent>
                </Card>
              )}

              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle2" gutterBottom>
                    Workflow
                  </Typography>
                  {selected.status === "draft" || selected.status === "rejected" ? (
                    <Button variant="contained" onClick={() => runAction(() => submitBudget(selected.id))}>
                      Submit for approval
                    </Button>
                  ) : selected.status === "approved" ? (
                    <Typography variant="body2" color="text.secondary">
                      Locked — fully approved.
                    </Typography>
                  ) : (
                    <Stack spacing={1}>
                      <Typography variant="body2" color="text.secondary">
                        Awaiting {NEXT_ROLE[selected.status]} approval
                      </Typography>
                      <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
                        <TextField label="Actor name" size="small" value={actorName} onChange={(e) => setActorName(e.target.value)} />
                        <TextField label="Comment (optional)" size="small" value={comment} onChange={(e) => setComment(e.target.value)} />
                        <Button
                          variant="contained"
                          color="success"
                          disabled={!actorName}
                          onClick={() => runAction(() => approveBudget(selected.id, actorName, comment || undefined))}
                        >
                          Approve
                        </Button>
                        <Button
                          variant="outlined"
                          color="error"
                          disabled={!actorName}
                          onClick={() => runAction(() => rejectBudget(selected.id, actorName, comment || undefined))}
                        >
                          Reject
                        </Button>
                      </Stack>
                    </Stack>
                  )}

                  {selected.approvals.length > 0 && (
                    <Stack spacing={0.5} sx={{ mt: 2 }}>
                      <Typography variant="caption" color="text.secondary">
                        History
                      </Typography>
                      {selected.approvals.map((a, i) => (
                        <Typography variant="body2" key={i}>
                          {a.role} · {a.action} by {a.actor_name}
                          {a.comment ? ` — "${a.comment}"` : ""}
                        </Typography>
                      ))}
                    </Stack>
                  )}
                </CardContent>
              </Card>

              {versions.length > 0 && (
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="subtitle2" gutterBottom>
                      Version History
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                      A snapshot is captured every time this budget is submitted — reject, edit, resubmit, and both
                      versions stay visible here.
                    </Typography>
                    {versions
                      .slice()
                      .reverse()
                      .map((v) => (
                        <Accordion key={v.id} disableGutters>
                          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                            <Typography variant="body2">
                              Version {v.version_number} — submitted {new Date(v.submitted_at).toLocaleString()}
                            </Typography>
                          </AccordionSummary>
                          <AccordionDetails>
                            <Table size="small">
                              <TableHead>
                                <TableRow>
                                  <TableCell>GL Account</TableCell>
                                  <TableCell>Period</TableCell>
                                  <TableCell align="right">Amount</TableCell>
                                  <TableCell>Currency</TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {v.lines_snapshot.map((line, i) => (
                                  <TableRow key={i}>
                                    <TableCell>{glNameFor(String(line.gl_account_id))}</TableCell>
                                    <TableCell>{String(line.period)}</TableCell>
                                    <TableCell align="right">{Number(line.amount).toLocaleString()}</TableCell>
                                    <TableCell>{String(line.currency)}</TableCell>
                                  </TableRow>
                                ))}
                                {v.lines_snapshot.length === 0 && (
                                  <TableRow>
                                    <TableCell colSpan={4}>
                                      <Typography variant="body2" color="text.secondary">
                                        No lines in this version.
                                      </Typography>
                                    </TableCell>
                                  </TableRow>
                                )}
                              </TableBody>
                            </Table>
                          </AccordionDetails>
                        </Accordion>
                      ))}
                  </CardContent>
                </Card>
              )}
            </Stack>
          )}
        </Grid>
      </Grid>
    </Stack>
  );
}
