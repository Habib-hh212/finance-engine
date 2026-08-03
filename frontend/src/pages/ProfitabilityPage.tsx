import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
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
import { getCustomerChurnRisk, getProfitabilityByCustomer, getProfitabilityByProduct } from "../api/profitability";
import { createFixedCost, getMarginalCostingSummary, listFixedCosts } from "../api/marginalCosting";
import type { CustomerChurnRisk, CustomerProfitability, FixedCost, MarginalCostingSummary, ProductProfitability } from "../api/types";

const fmt = (v: number | null) => (v === null ? "—" : v.toLocaleString());
const fmtPct = (v: number | null) => (v === null ? "—" : `${v}%`);

const RISK_COLOR: Record<CustomerChurnRisk["risk_level"], "error" | "warning" | "success"> = {
  high: "error",
  medium: "warning",
  low: "success",
};

function MetricCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Grid size={{ xs: 12, sm: 6, md: 3 }}>
      <Card variant="outlined">
        <CardContent>
          <Typography variant="caption" color="text.secondary">
            {label}
          </Typography>
          <Typography variant="h6" sx={{ fontVariantNumeric: "tabular-nums" }}>
            {value}
          </Typography>
          {hint && (
            <Typography variant="caption" color="text.secondary">
              {hint}
            </Typography>
          )}
        </CardContent>
      </Card>
    </Grid>
  );
}

export function ProfitabilityPage() {
  const { company } = useCompany();
  const [byProduct, setByProduct] = useState<ProductProfitability[]>([]);
  const [byCustomer, setByCustomer] = useState<CustomerProfitability[]>([]);
  const [churnRisk, setChurnRisk] = useState<CustomerChurnRisk[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [fiscalYear, setFiscalYear] = useState(String(new Date().getFullYear()));
  const [fixedCosts, setFixedCosts] = useState<FixedCost[]>([]);
  const [summary, setSummary] = useState<MarginalCostingSummary | null>(null);
  const [fcName, setFcName] = useState("");
  const [fcAmount, setFcAmount] = useState("");

  const loadProfitability = () => {
    if (!company) return;
    setError(null);
    Promise.all([getProfitabilityByProduct(company.id), getProfitabilityByCustomer(company.id), getCustomerChurnRisk(company.id)])
      .then(([products, customers, risk]) => {
        setByProduct(products);
        setByCustomer(customers);
        setChurnRisk(risk);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load profitability"));
  };

  const loadMarginalCosting = async () => {
    if (!company) return;
    setError(null);
    try {
      const year = Number(fiscalYear);
      const [fc, s] = await Promise.all([
        listFixedCosts(company.id, year),
        getMarginalCostingSummary(company.id, year),
      ]);
      setFixedCosts(fc);
      setSummary(s);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load marginal costing");
    }
  };

  useEffect(() => {
    loadProfitability();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);

  useEffect(() => {
    loadMarginalCosting();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id, fiscalYear]);

  const handleAddFixedCost = async () => {
    if (!company || !fcName || !fcAmount) return;
    setError(null);
    try {
      await createFixedCost(company.id, Number(fiscalYear), fcName, Number(fcAmount));
      setFcName("");
      setFcAmount("");
      await loadMarginalCosting();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add fixed cost");
    }
  };

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Profitability Analysis
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}
      <Typography variant="caption" color="text.secondary">
        Contribution margin needs a unit variable cost set per product — set it on the Sales Forecast page. Products without
        one show revenue but a blank contribution, not a false zero.
      </Typography>

      <Typography variant="h6">By Product</Typography>
      <TableContainer component={Card} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Product</TableCell>
              <TableCell align="right">Qty</TableCell>
              <TableCell align="right">Revenue</TableCell>
              <TableCell align="right">Unit Price</TableCell>
              <TableCell align="right">Unit Cost</TableCell>
              <TableCell align="right">Contribution/Unit</TableCell>
              <TableCell align="right">Total Contribution</TableCell>
              <TableCell align="right">Margin %</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {byProduct.map((p) => (
              <TableRow key={p.product_id}>
                <TableCell>{p.sku} — {p.name}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(p.quantity)}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(p.revenue)}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(p.unit_price)}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(p.unit_variable_cost)}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(p.contribution_per_unit)}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(p.contribution_margin_total)}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmtPct(p.contribution_margin_pct)}</TableCell>
              </TableRow>
            ))}
            {byProduct.length === 0 && (
              <TableRow>
                <TableCell colSpan={8}>
                  <Typography variant="body2" color="text.secondary">
                    No sales data yet.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Typography variant="h6">By Customer</Typography>
      <TableContainer component={Card} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Customer</TableCell>
              <TableCell align="right">Revenue</TableCell>
              <TableCell align="right">Total Contribution</TableCell>
              <TableCell align="right">Margin %</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {byCustomer.map((c) => (
              <TableRow key={c.customer_id}>
                <TableCell>{c.name}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(c.revenue)}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(c.contribution_margin_total)}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmtPct(c.contribution_margin_pct)}</TableCell>
              </TableRow>
            ))}
            {byCustomer.length === 0 && (
              <TableRow>
                <TableCell colSpan={4}>
                  <Typography variant="body2" color="text.secondary">
                    No customer-attributed sales yet.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Typography variant="h6">Customer Churn Risk</Typography>
      <Typography variant="caption" color="text.secondary">
        A statistical recency score, not a trained classifier — this system has no "did they churn" outcome to train on.
        Risk ratio = months since the customer's last order ÷ their own typical gap between orders. A customer who
        usually orders every 2 months and hasn't in 5 is flagged; one who always orders once a year and it's been 8
        months is not.
      </Typography>
      <TableContainer component={Card} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Customer</TableCell>
              <TableCell align="right">Last Order</TableCell>
              <TableCell align="right">Usual Cadence</TableCell>
              <TableCell align="right">Months Since</TableCell>
              <TableCell align="right">Revenue</TableCell>
              <TableCell align="center">Risk</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {churnRisk.map((c) => (
              <TableRow key={c.customer_id}>
                <TableCell>{c.name}</TableCell>
                <TableCell align="right">{c.last_order_period}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{c.avg_order_interval_months.toFixed(1)} mo</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{c.months_since_last_order}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(c.total_revenue)}</TableCell>
                <TableCell align="center">
                  <Chip size="small" label={c.risk_level} color={RISK_COLOR[c.risk_level]} />
                </TableCell>
              </TableRow>
            ))}
            {churnRisk.length === 0 && (
              <TableRow>
                <TableCell colSpan={6}>
                  <Typography variant="body2" color="text.secondary">
                    No customer has ordered enough times yet to establish a cadence.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center" }}>
        <Typography variant="h6">Marginal Costing (CVP Analysis)</Typography>
        <TextField label="Fiscal year" size="small" value={fiscalYear} onChange={(e) => setFiscalYear(e.target.value)} sx={{ width: 140 }} />
      </Stack>
      <Typography variant="caption" color="text.secondary">
        Company-level, not per-product — fixed costs are period costs, not unitized, so break-even and operating leverage
        are computed off the weighted-average contribution margin ratio across all costed products' revenue.
      </Typography>

      {summary && summary.uncosted_product_skus.length > 0 && (
        <Alert severity="warning">
          Excluded from these totals (no unit variable cost set): {summary.uncosted_product_skus.join(", ")}
        </Alert>
      )}

      {summary && (
        <Grid container spacing={2}>
          <MetricCard label="Revenue" value={fmt(summary.revenue)} />
          <MetricCard label="Contribution Margin" value={fmt(summary.contribution_margin)} hint={fmtPct(summary.contribution_margin_ratio)} />
          <MetricCard label="Fixed Costs" value={fmt(summary.fixed_costs)} />
          <MetricCard label="Net Operating Income" value={fmt(summary.net_operating_income)} />
          <MetricCard label="Break-Even Revenue" value={fmt(summary.break_even_revenue)} />
          <MetricCard label="Margin of Safety" value={fmt(summary.margin_of_safety)} hint={fmtPct(summary.margin_of_safety_pct)} />
          <MetricCard label="Degree of Operating Leverage" value={summary.degree_of_operating_leverage === null ? "—" : summary.degree_of_operating_leverage.toFixed(2)} />
        </Grid>
      )}

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle2" gutterBottom>
            Fixed Costs — FY{fiscalYear}
          </Typography>
          <Stack spacing={1}>
            {fixedCosts.map((f) => (
              <Stack key={f.id} direction="row" spacing={1} sx={{ alignItems: "center" }}>
                <Typography variant="body2" sx={{ flexGrow: 1 }}>{f.name}</Typography>
                <Chip size="small" label={`${f.amount.toLocaleString()} ${f.currency}`} />
              </Stack>
            ))}
            {fixedCosts.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                No fixed costs entered for this fiscal year yet.
              </Typography>
            )}
          </Stack>
          <Stack direction="row" spacing={1} sx={{ mt: 2, flexWrap: "wrap", alignItems: "center" }}>
            <TextField label="Name" size="small" value={fcName} onChange={(e) => setFcName(e.target.value)} />
            <TextField label="Amount" type="number" size="small" value={fcAmount} onChange={(e) => setFcAmount(e.target.value)} />
            <Button variant="outlined" size="small" onClick={handleAddFixedCost} disabled={!fcName || !fcAmount}>
              Add fixed cost
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
