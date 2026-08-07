import { useEffect, useState } from "react";
import {
  Alert,
  Box,
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
import { listProducts } from "../api/sales";
import {
  createProductionActual,
  getStandardCostVariance,
  listStandardCosts,
  upsertStandardCost,
} from "../api/standardCosting";
import type { Product, StandardCost, StandardCostVariance } from "../api/types";

const fmt = (v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 2 });

function VarianceCell({ value }: { value: number }) {
  return (
    <TableCell
      align="right"
      sx={{ fontVariantNumeric: "tabular-nums", color: value >= 0 ? "success.main" : "error.main" }}
    >
      {fmt(value)}
    </TableCell>
  );
}

export function StandardCostingPage() {
  const { company } = useCompany();
  const [products, setProducts] = useState<Product[]>([]);
  const [standards, setStandards] = useState<StandardCost[]>([]);
  const [fiscalYear, setFiscalYear] = useState(String(new Date().getFullYear()));
  const [variance, setVariance] = useState<StandardCostVariance[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [scProductId, setScProductId] = useState("");
  const [materialStdPrice, setMaterialStdPrice] = useState("");
  const [materialStdQty, setMaterialStdQty] = useState("");
  const [laborStdRate, setLaborStdRate] = useState("");
  const [laborStdHours, setLaborStdHours] = useState("");
  const [voHStdRate, setVoHStdRate] = useState("");
  const [foHStdRate, setFoHStdRate] = useState("");
  const [foHBudgeted, setFoHBudgeted] = useState("");

  const [paProductId, setPaProductId] = useState("");
  const [paPeriod, setPaPeriod] = useState("");
  const [unitsProduced, setUnitsProduced] = useState("");
  const [materialActualPrice, setMaterialActualPrice] = useState("");
  const [materialActualQty, setMaterialActualQty] = useState("");
  const [laborActualRate, setLaborActualRate] = useState("");
  const [laborActualHours, setLaborActualHours] = useState("");
  const [actualVOH, setActualVOH] = useState("");
  const [actualFOH, setActualFOH] = useState("");

  const loadAll = async () => {
    if (!company) return;
    setError(null);
    try {
      const [prods, stds, vr] = await Promise.all([
        listProducts(company.id),
        listStandardCosts(company.id),
        getStandardCostVariance(company.id, Number(fiscalYear)),
      ]);
      setProducts(prods);
      setStandards(stds);
      setVariance(vr);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load standard costing data");
    }
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id, fiscalYear]);

  const productName = (id: string) => {
    const p = products.find((p) => p.id === id);
    return p ? `${p.sku} — ${p.name}` : id;
  };

  const handleSaveStandard = async () => {
    if (!company || !scProductId) return;
    setError(null);
    try {
      await upsertStandardCost(company.id, {
        product_id: scProductId,
        material_std_price: Number(materialStdPrice),
        material_std_qty: Number(materialStdQty),
        labor_std_rate: Number(laborStdRate),
        labor_std_hours: Number(laborStdHours),
        variable_overhead_std_rate: Number(voHStdRate),
        fixed_overhead_std_rate: Number(foHStdRate),
        fixed_overhead_budgeted: Number(foHBudgeted),
      });
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save standard cost");
    }
  };

  const handlePostActual = async () => {
    if (!company || !paProductId || !paPeriod) return;
    setError(null);
    try {
      await createProductionActual(company.id, {
        product_id: paProductId,
        period: `${paPeriod}-01`,
        units_produced: Number(unitsProduced),
        material_actual_price: Number(materialActualPrice),
        material_actual_qty: Number(materialActualQty),
        labor_actual_rate: Number(laborActualRate),
        labor_actual_hours: Number(laborActualHours),
        actual_variable_overhead: Number(actualVOH),
        actual_fixed_overhead: Number(actualFOH),
      });
      setUnitsProduced("");
      setMaterialActualPrice("");
      setMaterialActualQty("");
      setLaborActualRate("");
      setLaborActualHours("");
      setActualVOH("");
      setActualFOH("");
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to post production actual");
    }
  };

  const requiredStdFieldsMissing = !scProductId || !materialStdPrice || !materialStdQty || !laborStdRate || !laborStdHours || !voHStdRate || !foHStdRate || !foHBudgeted;
  const requiredActualFieldsMissing = !paProductId || !paPeriod || !unitsProduced || !materialActualPrice || !materialActualQty || !laborActualRate || !laborActualHours || !actualVOH || !actualFOH;

  return (
    <Stack spacing={3}>
      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center" }}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>
          Standard Costing
        </Typography>
        <TextField label="Fiscal year" size="small" value={fiscalYear} onChange={(e) => setFiscalYear(e.target.value)} sx={{ width: 140 }} />
      </Stack>
      {error && <Alert severity="error">{error}</Alert>}

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Standard Cost Sheet
              </Typography>
              <Stack spacing={1}>
                <TextField select label="Product" size="small" value={scProductId} onChange={(e) => setScProductId(e.target.value)}>
                  {products.map((p) => (
                    <MenuItem key={p.id} value={p.id}>
                      {p.sku} — {p.name}
                    </MenuItem>
                  ))}
                </TextField>
                <Stack direction="row" spacing={1}>
                  <TextField label="Material std price" type="number" size="small" value={materialStdPrice} onChange={(e) => setMaterialStdPrice(e.target.value)} />
                  <TextField label="Material std qty/unit" type="number" size="small" value={materialStdQty} onChange={(e) => setMaterialStdQty(e.target.value)} />
                </Stack>
                <Stack direction="row" spacing={1}>
                  <TextField label="Labor std rate/hr" type="number" size="small" value={laborStdRate} onChange={(e) => setLaborStdRate(e.target.value)} />
                  <TextField label="Labor std hrs/unit" type="number" size="small" value={laborStdHours} onChange={(e) => setLaborStdHours(e.target.value)} />
                </Stack>
                <Stack direction="row" spacing={1}>
                  <TextField label="Variable OH std rate/hr" type="number" size="small" value={voHStdRate} onChange={(e) => setVoHStdRate(e.target.value)} />
                  <TextField label="Fixed OH std rate/hr" type="number" size="small" value={foHStdRate} onChange={(e) => setFoHStdRate(e.target.value)} />
                </Stack>
                <TextField label="Fixed OH budgeted (total)" type="number" size="small" value={foHBudgeted} onChange={(e) => setFoHBudgeted(e.target.value)} />
                <Button variant="contained" size="small" onClick={handleSaveStandard} disabled={requiredStdFieldsMissing}>
                  Save standard cost
                </Button>
              </Stack>

              <Stack spacing={0.5} sx={{ mt: 2 }}>
                {standards.map((s) => (
                  <Typography variant="body2" key={s.id} color="text.secondary">
                    {productName(s.product_id)}: material {s.material_std_price}×{s.material_std_qty}, labor {s.labor_std_rate}×{s.labor_std_hours}
                  </Typography>
                ))}
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Production Actual
              </Typography>
              <Stack spacing={1}>
                <TextField select label="Product" size="small" value={paProductId} onChange={(e) => setPaProductId(e.target.value)}>
                  {products.map((p) => (
                    <MenuItem key={p.id} value={p.id}>
                      {p.sku} — {p.name}
                    </MenuItem>
                  ))}
                </TextField>
                <Stack direction="row" spacing={1}>
                  <TextField label="Period" type="month" size="small" value={paPeriod} onChange={(e) => setPaPeriod(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
                  <TextField label="Units produced" type="number" size="small" value={unitsProduced} onChange={(e) => setUnitsProduced(e.target.value)} />
                </Stack>
                <Stack direction="row" spacing={1}>
                  <TextField label="Material actual price" type="number" size="small" value={materialActualPrice} onChange={(e) => setMaterialActualPrice(e.target.value)} />
                  <TextField label="Material actual qty" type="number" size="small" value={materialActualQty} onChange={(e) => setMaterialActualQty(e.target.value)} />
                </Stack>
                <Stack direction="row" spacing={1}>
                  <TextField label="Labor actual rate" type="number" size="small" value={laborActualRate} onChange={(e) => setLaborActualRate(e.target.value)} />
                  <TextField label="Labor actual hours" type="number" size="small" value={laborActualHours} onChange={(e) => setLaborActualHours(e.target.value)} />
                </Stack>
                <Stack direction="row" spacing={1}>
                  <TextField label="Actual variable OH" type="number" size="small" value={actualVOH} onChange={(e) => setActualVOH(e.target.value)} />
                  <TextField label="Actual fixed OH" type="number" size="small" value={actualFOH} onChange={(e) => setActualFOH(e.target.value)} />
                </Stack>
                <Button variant="contained" size="small" onClick={handlePostActual} disabled={requiredActualFieldsMissing}>
                  Post production actual
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Typography variant="h6">Variance</Typography>
      <Box sx={{ overflowX: "auto" }}>
        <TableContainer component={Card} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Product</TableCell>
                <TableCell>Period</TableCell>
                <TableCell align="right">Material Price</TableCell>
                <TableCell align="right">Material Qty</TableCell>
                <TableCell align="right">Labor Rate</TableCell>
                <TableCell align="right">Labor Efficiency</TableCell>
                <TableCell align="right">VOH Spending</TableCell>
                <TableCell align="right">VOH Efficiency</TableCell>
                <TableCell align="right">FOH Budget</TableCell>
                <TableCell align="right">FOH Volume</TableCell>
                <TableCell align="right">Total Variance</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {variance.map((row, i) => (
                <TableRow key={i}>
                  <TableCell>{row.product_sku} — {row.product_name}</TableCell>
                  <TableCell>{row.period}</TableCell>
                  <VarianceCell value={row.material_price_variance} />
                  <VarianceCell value={row.material_quantity_variance} />
                  <VarianceCell value={row.labor_rate_variance} />
                  <VarianceCell value={row.labor_efficiency_variance} />
                  <VarianceCell value={row.variable_overhead_spending_variance} />
                  <VarianceCell value={row.variable_overhead_efficiency_variance} />
                  <VarianceCell value={row.fixed_overhead_budget_variance} />
                  <VarianceCell value={row.fixed_overhead_volume_variance} />
                  <VarianceCell value={row.total_cost_variance} />
                </TableRow>
              ))}
              {variance.length === 0 && (
                <TableRow>
                  <TableCell colSpan={11}>
                    <Typography variant="body2" color="text.secondary">
                      No variance to show yet — set a standard cost and post a production actual for the same product.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    </Stack>
  );
}
