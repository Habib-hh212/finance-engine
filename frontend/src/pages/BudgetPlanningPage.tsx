import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { AgGridReact } from "ag-grid-react";
import type { ColDef } from "ag-grid-community";
import { AllCommunityModule, ModuleRegistry, themeQuartz } from "ag-grid-community";
import { useCompany } from "../context/CompanyContext";
import {
  addBudgetLines,
  approveBudget,
  createBudget,
  createGLAccount,
  getBudget,
  listBudgets,
  listGLAccounts,
  rejectBudget,
  submitBudget,
} from "../api/budgets";
import type { Budget, BudgetDetail, BudgetStatus, BudgetType, GLAccount, GLCategory } from "../api/types";

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

export function BudgetPlanningPage() {
  const { company } = useCompany();
  const [glAccounts, setGlAccounts] = useState<GLAccount[]>([]);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [selected, setSelected] = useState<BudgetDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [glCode, setGlCode] = useState("");
  const [glName, setGlName] = useState("");
  const [glCategory, setGlCategory] = useState<GLCategory>("expense");

  const [budgetName, setBudgetName] = useState("");
  const [budgetType, setBudgetType] = useState<BudgetType>("expense");
  const [fiscalYear, setFiscalYear] = useState(String(new Date().getFullYear()));

  const [lineGlId, setLineGlId] = useState("");
  const [linePeriod, setLinePeriod] = useState("");
  const [lineAmount, setLineAmount] = useState("");

  const [actorName, setActorName] = useState("");
  const [comment, setComment] = useState("");

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
      await createGLAccount(company.id, glCode, glName, glCategory);
      setGlCode("");
      setGlName("");
    });

  const handleCreateBudget = () =>
    runAction(async () => {
      if (!company || !budgetName) return;
      const created = await createBudget(company.id, budgetName, budgetType, Number(fiscalYear), company.base_currency);
      setBudgetName("");
      await openBudget(created.id);
    });

  const handleAddLine = () =>
    runAction(async () => {
      if (!selected || !lineGlId || !linePeriod || !lineAmount) return;
      await addBudgetLines(selected.id, [{ gl_account_id: lineGlId, period: `${linePeriod}-01`, amount: Number(lineAmount) }]);
      setLineAmount("");
    });

  const columnDefs: ColDef[] = [
    { field: "gl_account_id", headerName: "GL Account", valueFormatter: (p) => glNameFor(p.value), flex: 2 },
    { field: "period", headerName: "Period", flex: 1 },
    { field: "amount", headerName: "Amount", flex: 1, valueFormatter: (p) => Number(p.value).toLocaleString() },
    { field: "currency", headerName: "Currency", flex: 1 },
  ];

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
                  {glAccounts.map((g) => (
                    <Stack key={g.id} direction="row" sx={{ alignItems: "center" }} spacing={1}>
                      <Typography variant="body2">
                        {g.code} — {g.name}
                      </Typography>
                      <Chip size="small" label={g.category} />
                    </Stack>
                  ))}
                </Stack>
                <Stack spacing={1} sx={{ mt: 2 }}>
                  <TextField label="Code" size="small" value={glCode} onChange={(e) => setGlCode(e.target.value)} />
                  <TextField label="Name" size="small" value={glName} onChange={(e) => setGlName(e.target.value)} />
                  <TextField select label="Category" size="small" value={glCategory} onChange={(e) => setGlCategory(e.target.value as GLCategory)}>
                    <MenuItem value="revenue">Revenue</MenuItem>
                    <MenuItem value="expense">Expense</MenuItem>
                  </TextField>
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
                  </TextField>
                  <TextField label="Fiscal year" size="small" value={fiscalYear} onChange={(e) => setFiscalYear(e.target.value)} />
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
                        {selected.type} · FY{selected.fiscal_year} · {selected.currency}
                      </Typography>
                    </Box>
                    <Chip label={selected.status} color={STATUS_COLOR[selected.status]} />
                  </Stack>
                </CardContent>
              </Card>

              {selected.status === "draft" && (
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
                      <TextField label="Amount" type="number" size="small" value={lineAmount} onChange={(e) => setLineAmount(e.target.value)} />
                      <Button variant="outlined" onClick={handleAddLine} disabled={!lineGlId || !linePeriod || !lineAmount}>
                        Add
                      </Button>
                    </Stack>
                  </CardContent>
                </Card>
              )}

              <Box sx={{ height: 260, width: "100%" }}>
                <AgGridReact rowData={selected.lines} columnDefs={columnDefs} theme={themeQuartz} />
              </Box>

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
            </Stack>
          )}
        </Grid>
      </Grid>
    </Stack>
  );
}
