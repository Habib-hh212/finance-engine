import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Grid,
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
import { createScenario, deleteScenario, getScenarioForecast, listScenarios } from "../api/scenarios";
import type { Scenario, ScenarioForecast } from "../api/types";

function nextMonthValue() {
  const now = new Date();
  const next = new Date(now.getFullYear(), now.getMonth() + 1, 1);
  return `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}`;
}

const fmt = (v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 2 });

export function ScenarioPlanningPage() {
  const { company } = useCompany();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [salesGrowth, setSalesGrowth] = useState("10");
  const [expenseGrowth, setExpenseGrowth] = useState("-5");

  const [startMonth, setStartMonth] = useState(nextMonthValue());
  const [periods, setPeriods] = useState("6");
  const [dsoDays, setDsoDays] = useState("45");
  const [dpoDays, setDpoDays] = useState("30");
  const [collectionLagDays, setCollectionLagDays] = useState("30");
  const [comparison, setComparison] = useState<ScenarioForecast | null>(null);
  const [comparisonError, setComparisonError] = useState<string | null>(null);

  const loadScenarios = async () => {
    if (!company) return;
    setError(null);
    try {
      const list = await listScenarios(company.id);
      setScenarios(list);
      if (list.length > 0 && !list.some((s) => s.id === selectedId)) {
        setSelectedId(list[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load scenarios");
    }
  };

  useEffect(() => {
    loadScenarios();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);

  const handleCreate = async () => {
    if (!company || !name) return;
    setError(null);
    try {
      await createScenario(company.id, name, Number(salesGrowth), Number(expenseGrowth));
      setName("");
      await loadScenarios();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create scenario");
    }
  };

  const handleDelete = async (id: string) => {
    setError(null);
    try {
      await deleteScenario(id);
      if (selectedId === id) {
        setSelectedId("");
        setComparison(null);
      }
      await loadScenarios();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete scenario");
    }
  };

  const loadComparison = async () => {
    if (!selectedId) return;
    setComparisonError(null);
    try {
      const result = await getScenarioForecast(
        selectedId,
        `${startMonth}-01`,
        Number(periods),
        Number(dsoDays),
        Number(dpoDays),
        Number(collectionLagDays),
      );
      setComparison(result);
    } catch (err) {
      setComparisonError(err instanceof Error ? err.message : "Failed to compare scenario");
      setComparison(null);
    }
  };

  useEffect(() => {
    setComparison(null);
    setComparisonError(null);
  }, [selectedId]);

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Scenario Planning
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Scenarios
              </Typography>
              <Stack spacing={1}>
                {scenarios.map((s) => (
                  <Box
                    key={s.id}
                    onClick={() => setSelectedId(s.id)}
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      p: 1,
                      borderRadius: 1,
                      cursor: "pointer",
                      bgcolor: selectedId === s.id ? "action.selected" : "transparent",
                      "&:hover": { bgcolor: "action.hover" },
                    }}
                  >
                    <Box>
                      <Typography variant="body2">{s.name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        sales {s.sales_growth_pct >= 0 ? "+" : ""}{s.sales_growth_pct}% · expense {s.expense_growth_pct >= 0 ? "+" : ""}{s.expense_growth_pct}%
                      </Typography>
                    </Box>
                    <Button size="small" color="error" onClick={(e) => { e.stopPropagation(); handleDelete(s.id); }}>
                      Delete
                    </Button>
                  </Box>
                ))}
                {scenarios.length === 0 && (
                  <Typography variant="body2" color="text.secondary">
                    No scenarios yet.
                  </Typography>
                )}
              </Stack>

              <Stack spacing={1} sx={{ mt: 2 }}>
                <TextField label="Name" size="small" value={name} onChange={(e) => setName(e.target.value)} />
                <TextField
                  label="Sales growth %"
                  type="number"
                  size="small"
                  value={salesGrowth}
                  onChange={(e) => setSalesGrowth(e.target.value)}
                  helperText="e.g. 10 for +10%, -10 for -10%"
                />
                <TextField
                  label="Expense growth %"
                  type="number"
                  size="small"
                  value={expenseGrowth}
                  onChange={(e) => setExpenseGrowth(e.target.value)}
                  helperText="e.g. -5 for a 5% cost cut"
                />
                <Button variant="contained" size="small" onClick={handleCreate} disabled={!name}>
                  Create scenario
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 8 }}>
          {!selectedId ? (
            <Alert severity="info">Select or create a scenario to compare it against the base case.</Alert>
          ) : (
            <Stack spacing={2}>
              <Card variant="outlined">
                <CardContent>
                  <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center" }}>
                    <TextField
                      label="Start"
                      type="month"
                      size="small"
                      value={startMonth}
                      onChange={(e) => setStartMonth(e.target.value)}
                      slotProps={{ inputLabel: { shrink: true } }}
                    />
                    <TextField label="Periods" type="number" size="small" value={periods} onChange={(e) => setPeriods(e.target.value)} sx={{ width: 100 }} />
                    <TextField label="DSO days" type="number" size="small" value={dsoDays} onChange={(e) => setDsoDays(e.target.value)} sx={{ width: 110 }} />
                    <TextField label="DPO days" type="number" size="small" value={dpoDays} onChange={(e) => setDpoDays(e.target.value)} sx={{ width: 110 }} />
                    <TextField
                      label="Collection lag (days)"
                      type="number"
                      size="small"
                      value={collectionLagDays}
                      onChange={(e) => setCollectionLagDays(e.target.value)}
                      sx={{ width: 160 }}
                    />
                    <Button variant="contained" size="small" onClick={loadComparison}>
                      Compare
                    </Button>
                  </Stack>
                  {comparisonError && (
                    <Alert severity="error" sx={{ mt: 2 }}>
                      {comparisonError}
                    </Alert>
                  )}
                </CardContent>
              </Card>

              {comparison && (
                <>
                  <Typography variant="h6">Income Statement — Base vs. {comparison.scenario.name}</Typography>
                  <TableContainer component={Card} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Period</TableCell>
                          <TableCell align="right">Base Revenue</TableCell>
                          <TableCell align="right">Scenario Revenue</TableCell>
                          <TableCell align="right">Base Net Profit</TableCell>
                          <TableCell align="right">Scenario Net Profit</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {comparison.base_income_statement.map((base, i) => {
                          const scenario = comparison.scenario_income_statement[i];
                          return (
                            <TableRow key={base.period}>
                              <TableCell>{base.period}</TableCell>
                              <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(base.revenue_forecast)}</TableCell>
                              <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>{fmt(scenario.revenue_forecast)}</TableCell>
                              <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(base.net_profit_forecast)}</TableCell>
                              <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>{fmt(scenario.net_profit_forecast)}</TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </TableContainer>

                  <Typography variant="h6">Balance Sheet — Base vs. {comparison.scenario.name}</Typography>
                  <TableContainer component={Card} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Period</TableCell>
                          <TableCell align="right">Base Cash</TableCell>
                          <TableCell align="right">Scenario Cash</TableCell>
                          <TableCell align="right">Base Total Assets</TableCell>
                          <TableCell align="right">Scenario Total Assets</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {comparison.base_balance_sheet.map((base, i) => {
                          const scenario = comparison.scenario_balance_sheet[i];
                          return (
                            <TableRow key={base.period}>
                              <TableCell>{base.period}</TableCell>
                              <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(base.cash)}</TableCell>
                              <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>{fmt(scenario.cash)}</TableCell>
                              <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(base.total_assets)}</TableCell>
                              <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>{fmt(scenario.total_assets)}</TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </>
              )}
            </Stack>
          )}
        </Grid>
      </Grid>
    </Stack>
  );
}
