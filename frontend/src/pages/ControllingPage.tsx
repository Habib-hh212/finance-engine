import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Grid,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useCompany } from "../context/CompanyContext";
import { createActual, getBudgetConsumption, getBudgetVsActual } from "../api/controlling";
import { listBudgets, listGLAccounts } from "../api/budgets";
import { StatusPill } from "../components/StatusPill";
import type { Budget, BudgetConsumption, GLAccount, VarianceRow } from "../api/types";

export function ControllingPage() {
  const { company } = useCompany();
  const [fiscalYear, setFiscalYear] = useState(String(new Date().getFullYear()));
  const [rows, setRows] = useState<VarianceRow[]>([]);
  const [glAccounts, setGlAccounts] = useState<GLAccount[]>([]);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [consumption, setConsumption] = useState<Record<string, BudgetConsumption>>({});
  const [error, setError] = useState<string | null>(null);

  const [actualGlId, setActualGlId] = useState("");
  const [actualPeriod, setActualPeriod] = useState("");
  const [actualAmount, setActualAmount] = useState("");

  const load = async () => {
    if (!company) return;
    setError(null);
    try {
      const [varianceRows, gls, bgs] = await Promise.all([
        getBudgetVsActual(company.id, Number(fiscalYear) || undefined),
        listGLAccounts(company.id),
        listBudgets(company.id),
      ]);
      setRows(varianceRows);
      setGlAccounts(gls);
      setBudgets(bgs.filter((b) => b.status === "approved" && b.fiscal_year === Number(fiscalYear)));

      const consumptionEntries = await Promise.all(
        bgs
          .filter((b) => b.status === "approved" && b.fiscal_year === Number(fiscalYear))
          .map(async (b) => [b.id, await getBudgetConsumption(b.id)] as const),
      );
      setConsumption(Object.fromEntries(consumptionEntries));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load controlling data");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);

  const handlePostActual = async () => {
    if (!company || !actualGlId || !actualPeriod || !actualAmount) return;
    await createActual(company.id, actualGlId, `${actualPeriod}-01`, Number(actualAmount));
    setActualAmount("");
    await load();
  };

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Cost Controlling & Variance
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
        <TextField label="Fiscal year" size="small" value={fiscalYear} onChange={(e) => setFiscalYear(e.target.value)} sx={{ width: 140 }} />
        <Button variant="contained" onClick={load}>
          Refresh
        </Button>
      </Stack>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle2" gutterBottom>
            Post an actual
          </Typography>
          <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", alignItems: "center" }}>
            <TextField select label="GL Account" size="small" value={actualGlId} onChange={(e) => setActualGlId(e.target.value)} sx={{ minWidth: 200 }}>
              {glAccounts.map((g) => (
                <MenuItem key={g.id} value={g.id}>
                  {g.code} {g.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Period" type="month" size="small" value={actualPeriod} onChange={(e) => setActualPeriod(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
            <TextField label="Amount" type="number" size="small" value={actualAmount} onChange={(e) => setActualAmount(e.target.value)} />
            <Button variant="outlined" onClick={handlePostActual} disabled={!actualGlId || !actualPeriod || !actualAmount}>
              Post
            </Button>
          </Stack>
        </CardContent>
      </Card>

      <Typography variant="h6">Budget vs. Actual</Typography>
      <TableContainer component={Card} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>GL Account</TableCell>
              <TableCell>Period</TableCell>
              <TableCell align="right">Budget</TableCell>
              <TableCell align="right">Actual</TableCell>
              <TableCell align="right">Variance</TableCell>
              <TableCell align="right">Variance %</TableCell>
              <TableCell align="center">Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((r, i) => (
              <TableRow key={i}>
                <TableCell>{r.gl_account_code} {r.gl_account_name}</TableCell>
                <TableCell>{r.period}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{r.budget_amount.toLocaleString()}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{r.actual_amount.toLocaleString()}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{r.variance_amount.toLocaleString()}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{r.variance_pct === null ? "—" : `${r.variance_pct}%`}</TableCell>
                <TableCell align="center">
                  <StatusPill status={r.status} />
                </TableCell>
              </TableRow>
            ))}
            {rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={7}>
                  <Typography variant="body2" color="text.secondary">
                    No budget or actual data for this fiscal year yet.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Typography variant="h6">Budget Consumption</Typography>
      <Grid container spacing={2}>
        {budgets.map((b) => {
          const c = consumption[b.id];
          if (!c) return null;
          return (
            <Grid size={{ xs: 12, sm: 6, md: 4 }} key={b.id}>
              <Card variant="outlined">
                <CardContent>
                  <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center" }}>
                    <Typography variant="subtitle2">{b.name}</Typography>
                    <StatusPill status={c.status} />
                  </Stack>
                  <Typography variant="h6" sx={{ mt: 1, fontVariantNumeric: "tabular-nums" }}>
                    {c.spent.toLocaleString()} / {c.budget_amount.toLocaleString()}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {c.consumption_pct === null ? "—" : `${c.consumption_pct}% consumed`} · remaining {c.remaining.toLocaleString()}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
        {budgets.length === 0 && (
          <Grid size={12}>
            <Typography variant="body2" color="text.secondary">
              No approved budgets for this fiscal year.
            </Typography>
          </Grid>
        )}
      </Grid>
    </Stack>
  );
}
