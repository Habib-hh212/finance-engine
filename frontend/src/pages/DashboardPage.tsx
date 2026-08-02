import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Card,
  CardContent,
  CircularProgress,
  Grid,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useCompany } from "../context/CompanyContext";
import { getInsights, getKPIs } from "../api/kpis";
import type { Insight, KPIResponse } from "../api/types";

function currentMonthValue() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function KpiTile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent>
        <Typography variant="body2" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h4" sx={{ mt: 1, fontVariantNumeric: "tabular-nums" }}>
          {value}
        </Typography>
        {hint && (
          <Typography variant="caption" color="text.secondary">
            {hint}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

const SEVERITY_COLOR: Record<Insight["severity"], "error" | "warning"> = { red: "error", yellow: "warning" };

export function DashboardPage() {
  const { company } = useCompany();
  const [fiscalYear, setFiscalYear] = useState(String(new Date().getFullYear()));
  const [cashMonth, setCashMonth] = useState(currentMonthValue());
  const [openingBalance, setOpeningBalance] = useState("0");
  const [kpis, setKpis] = useState<KPIResponse | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!company) return;
    setLoading(true);
    setError(null);
    try {
      const cashStartPeriod = cashMonth ? `${cashMonth}-01` : undefined;
      const [kpiResult, insightResult] = await Promise.all([
        getKPIs(company.id, Number(fiscalYear) || undefined, cashStartPeriod, Number(openingBalance) || 0),
        getInsights(company.id, Number(fiscalYear) || undefined),
      ]);
      setKpis(kpiResult);
      setInsights(insightResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);

  const fmtPct = (v: number | null) => (v === null ? "—" : `${v.toFixed(1)}%`);

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>
          Dashboard
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {company?.name} · {company?.base_currency}
        </Typography>
      </Box>

      <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap" }}>
        <TextField label="Fiscal year" size="small" value={fiscalYear} onChange={(e) => setFiscalYear(e.target.value)} sx={{ width: 140 }} />
        <TextField
          label="Cash runway anchor month"
          type="month"
          size="small"
          value={cashMonth}
          onChange={(e) => setCashMonth(e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
          sx={{ width: 220 }}
        />
        <TextField
          label="Opening balance"
          type="number"
          size="small"
          value={openingBalance}
          onChange={(e) => setOpeningBalance(e.target.value)}
          sx={{ width: 160 }}
        />
      </Stack>

      {error && <Alert severity="error">{error}</Alert>}
      {loading && <CircularProgress size={24} />}

      {kpis && (
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <KpiTile label="Gross Margin" value={fmtPct(kpis.gross_margin_pct)} hint="Contribution margin / revenue" />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <KpiTile label="Budget Utilization" value={fmtPct(kpis.budget_utilization_pct)} hint="Approved budgets, this fiscal year" />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <KpiTile
              label="Forecast Accuracy (MAPE)"
              value={kpis.forecast_accuracy_mape === null ? "—" : `${kpis.forecast_accuracy_mape.toFixed(1)}%`}
              hint="Walk-forward backtest, lower is better"
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <KpiTile
              label="Cash Runway"
              value={kpis.cash_runway_months === null ? "12+ mo" : `${kpis.cash_runway_months} mo`}
              hint="Months until balance goes negative"
            />
          </Grid>
        </Grid>
      )}

      <Box>
        <Typography variant="h6" sx={{ mb: 1.5 }}>
          AI Insights
        </Typography>
        {insights.length === 0 && !loading && (
          <Alert severity="success" variant="outlined">
            Nothing needs attention right now.
          </Alert>
        )}
        <Stack spacing={1}>
          {insights.map((insight, i) => (
            <Alert key={i} severity={SEVERITY_COLOR[insight.severity]} variant="outlined">
              {insight.message}
            </Alert>
          ))}
        </Stack>
      </Box>
    </Stack>
  );
}
