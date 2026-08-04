import { useEffect, useState } from "react";
import {
  Alert,
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
import { getFxScenario, listExchangeRates, upsertExchangeRate } from "../api/fx";
import type { ExchangeRate, FxScenario } from "../api/types";

function currentMonthValue() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

const fmt = (v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 2 });

export function FxScenarioPage() {
  const { company } = useCompany();
  const [rates, setRates] = useState<ExchangeRate[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [fromCurrency, setFromCurrency] = useState("EUR");
  const [toCurrency, setToCurrency] = useState("USD");
  const [rateDate, setRateDate] = useState(new Date().toISOString().slice(0, 10));
  const [rateValue, setRateValue] = useState("1.10");

  const [startMonth, setStartMonth] = useState(currentMonthValue());
  const [endMonth, setEndMonth] = useState(currentMonthValue());
  const [shockPct, setShockPct] = useState("-10");
  const [scenario, setScenario] = useState<FxScenario | null>(null);
  const [scenarioError, setScenarioError] = useState<string | null>(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);

  const loadRates = async () => {
    try {
      setRates(await listExchangeRates());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load exchange rates");
    }
  };

  useEffect(() => {
    loadRates();
  }, []);

  const handleAddRate = async () => {
    if (!fromCurrency || !toCurrency || !rateDate || !rateValue) return;
    try {
      await upsertExchangeRate(fromCurrency.toUpperCase(), toCurrency.toUpperCase(), rateDate, Number(rateValue));
      await loadRates();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save exchange rate");
    }
  };

  const loadScenario = async () => {
    if (!company) return;
    setScenarioLoading(true);
    setScenarioError(null);
    try {
      const result = await getFxScenario(company.id, `${startMonth}-01`, `${endMonth}-28`, Number(shockPct) || 0);
      setScenario(result);
    } catch (err) {
      setScenarioError(err instanceof Error ? err.message : "Failed to run the FX scenario");
      setScenario(null);
    } finally {
      setScenarioLoading(false);
    }
  };

  useEffect(() => {
    loadScenario();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        FX Scenario
      </Typography>
      <Typography variant="caption" color="text.secondary">
        The currency-risk counterpart to Scenario Planning: converts non-base-currency sales into the company's base
        currency using the latest rate on file, then shows what that revenue would be worth if the rate moved by a
        hypothetical percentage. Scoped to sales actuals — record the rates you care about below first.
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle2" gutterBottom>
            Exchange Rates
          </Typography>
          <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", alignItems: "center", mb: 2 }}>
            <TextField label="From" size="small" value={fromCurrency} onChange={(e) => setFromCurrency(e.target.value)} sx={{ width: 90 }} />
            <TextField label="To" size="small" value={toCurrency} onChange={(e) => setToCurrency(e.target.value)} sx={{ width: 90 }} />
            <TextField
              label="Date"
              type="date"
              size="small"
              value={rateDate}
              onChange={(e) => setRateDate(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField label="Rate" type="number" size="small" value={rateValue} onChange={(e) => setRateValue(e.target.value)} sx={{ width: 120 }} />
            <Button variant="outlined" size="small" onClick={handleAddRate} disabled={!fromCurrency || !toCurrency || !rateValue}>
              Save rate
            </Button>
          </Stack>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>From</TableCell>
                  <TableCell>To</TableCell>
                  <TableCell>Date</TableCell>
                  <TableCell align="right">Rate</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rates.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell>{r.from_currency}</TableCell>
                    <TableCell>{r.to_currency}</TableCell>
                    <TableCell>{r.rate_date}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{r.rate}</TableCell>
                  </TableRow>
                ))}
                {rates.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4}>
                      <Typography variant="body2" color="text.secondary">
                        No exchange rates recorded yet.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap" }}>
        <TextField
          label="From"
          type="month"
          size="small"
          value={startMonth}
          onChange={(e) => setStartMonth(e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <TextField
          label="To"
          type="month"
          size="small"
          value={endMonth}
          onChange={(e) => setEndMonth(e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <TextField
          label="Shock %"
          type="number"
          size="small"
          value={shockPct}
          onChange={(e) => setShockPct(e.target.value)}
          helperText="e.g. -10 for a 10% depreciation"
          sx={{ width: 160 }}
        />
        <Button variant="contained" onClick={loadScenario} disabled={scenarioLoading}>
          {scenarioLoading ? "Running…" : "Run scenario"}
        </Button>
      </Stack>

      {scenarioError && <Alert severity="error">{scenarioError}</Alert>}

      {scenario && (
        <>
          {scenario.unrated_currencies.length > 0 && (
            <Alert severity="warning">
              No exchange rate on file for: {scenario.unrated_currencies.join(", ")} — those sales are excluded from
              the totals below until a rate is recorded.
            </Alert>
          )}

          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 4 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="body2" color="text.secondary">
                    Actual ({scenario.base_currency})
                  </Typography>
                  <Typography variant="h6" sx={{ fontVariantNumeric: "tabular-nums" }}>
                    {fmt(scenario.total_base_actual)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="body2" color="text.secondary">
                    Shocked ({scenario.shock_pct > 0 ? "+" : ""}
                    {scenario.shock_pct}%)
                  </Typography>
                  <Typography variant="h6" sx={{ fontVariantNumeric: "tabular-nums" }}>
                    {fmt(scenario.total_base_shocked)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="body2" color="text.secondary">
                    Impact
                  </Typography>
                  <Typography
                    variant="h6"
                    sx={{ fontVariantNumeric: "tabular-nums", color: scenario.impact < 0 ? "error.main" : "success.main" }}
                  >
                    {scenario.impact >= 0 ? "+" : ""}
                    {fmt(scenario.impact)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <TableContainer component={Card} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Currency</TableCell>
                  <TableCell>Period</TableCell>
                  <TableCell align="right">Native Amount</TableCell>
                  <TableCell align="right">Rate Used</TableCell>
                  <TableCell align="right">{scenario.base_currency} Amount</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {scenario.lines.map((line, i) => (
                  <TableRow key={i}>
                    <TableCell>{line.currency}</TableCell>
                    <TableCell>{line.period}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(line.native_amount)}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{line.rate_used ?? "—"}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                      {line.base_amount !== null ? fmt(line.base_amount) : "—"}
                    </TableCell>
                  </TableRow>
                ))}
                {scenario.lines.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <Typography variant="body2" color="text.secondary">
                        No non-base-currency sales in this range.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}
    </Stack>
  );
}
