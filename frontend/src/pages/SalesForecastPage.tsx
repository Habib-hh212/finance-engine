import { useEffect, useRef, useState } from "react";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
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
import UploadFileIcon from "@mui/icons-material/UploadFile";
import DownloadIcon from "@mui/icons-material/Download";
import { EChart } from "../components/EChart";
import { useCompany } from "../context/CompanyContext";
import {
  compareForecastModels,
  downloadForecast,
  getDemandForecast,
  getForecast,
  listProducts,
  setProductCost,
  uploadSalesCsv,
} from "../api/sales";
import type { DemandForecastResponse, ForecastModel, ForecastResponse, ModelComparison, Product } from "../api/types";

const MODELS: { value: ForecastModel; label: string }[] = [
  { value: "exponential_smoothing", label: "Exponential Smoothing" },
  { value: "moving_average", label: "Moving Average" },
  { value: "weighted_average", label: "Weighted Average" },
  { value: "random_forest", label: "Random Forest (ML)" },
  { value: "gradient_boosting", label: "Gradient Boosting (ML)" },
];

const MODEL_LABEL: Record<string, string> = Object.fromEntries(MODELS.map((m) => [m.value, m.label]));

export function SalesForecastPage() {
  const { company } = useCompany();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [productId, setProductId] = useState("");
  const [model, setModel] = useState<ForecastModel>("exponential_smoothing");
  const [periods, setPeriods] = useState(3);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [costInput, setCostInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [comparison, setComparison] = useState<ModelComparison | null>(null);
  const [comparisonError, setComparisonError] = useState<string | null>(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [demand, setDemand] = useState<DemandForecastResponse | null>(null);
  const [demandError, setDemandError] = useState<string | null>(null);
  const [demandLoading, setDemandLoading] = useState(false);

  const loadProducts = async () => {
    if (!company) return;
    const list = await listProducts(company.id);
    setProducts(list);
    if (list.length > 0 && !list.some((p) => p.id === productId)) {
      setProductId(list[0].id);
    }
  };

  useEffect(() => {
    loadProducts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);

  useEffect(() => {
    const selected = products.find((p) => p.id === productId);
    setCostInput(selected?.unit_variable_cost != null ? String(selected.unit_variable_cost) : "");
  }, [productId, products]);

  const loadForecast = async () => {
    if (!company || !productId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getForecast(company.id, productId, model, periods);
      setForecast(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load forecast");
      setForecast(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (productId) loadForecast();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId, model, periods]);

  const loadComparison = async () => {
    if (!company || !productId) return;
    setComparisonLoading(true);
    setComparisonError(null);
    try {
      const result = await compareForecastModels(company.id, productId);
      setComparison(result);
    } catch (err) {
      setComparisonError(err instanceof Error ? err.message : "Failed to compare models");
      setComparison(null);
    } finally {
      setComparisonLoading(false);
    }
  };

  useEffect(() => {
    setComparison(null);
    setComparisonError(null);
    setDemand(null);
    setDemandError(null);
  }, [productId]);

  const loadDemand = async () => {
    if (!company || !productId) return;
    setDemandLoading(true);
    setDemandError(null);
    try {
      const result = await getDemandForecast(company.id, productId, model, periods);
      setDemand(result);
    } catch (err) {
      setDemandError(err instanceof Error ? err.message : "Failed to load demand forecast");
      setDemand(null);
    } finally {
      setDemandLoading(false);
    }
  };

  const handleUpload = async (file: File) => {
    if (!company) return;
    setUploadMessage(null);
    setError(null);
    try {
      const result = await uploadSalesCsv(company.id, file);
      setUploadMessage(
        `Imported ${result.rows_imported} rows (${result.products_created} new product(s), ${result.customers_created} new customer(s)).`,
      );
      await loadProducts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  };

  const handleSaveCost = async () => {
    if (!productId || costInput === "") return;
    await setProductCost(productId, Number(costInput));
    await loadProducts();
  };

  const chartOption = forecast
    ? {
        tooltip: { trigger: "axis" as const },
        grid: { left: 60, right: 30, top: 30, bottom: 40 },
        xAxis: { type: "category" as const, data: forecast.points.map((p) => p.period) },
        yAxis: { type: "value" as const },
        series: [
          {
            name: "Upper bound",
            type: "line" as const,
            data: forecast.points.map((p) => p.upper_bound),
            lineStyle: { opacity: 0 },
            areaStyle: { color: "#2f5d5022" },
            stack: "band",
            symbol: "none",
          },
          {
            name: "Lower bound",
            type: "line" as const,
            data: forecast.points.map((p) => p.lower_bound - p.upper_bound),
            lineStyle: { opacity: 0 },
            areaStyle: { color: "#f5f6f4" },
            stack: "band",
            symbol: "none",
          },
          {
            name: "Forecast",
            type: "line" as const,
            data: forecast.points.map((p) => p.forecast),
            color: "#2f5d50",
            symbol: "circle",
          },
        ],
      }
    : null;

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Sales Forecasting
      </Typography>

      <Card variant="outlined">
        <CardContent>
          <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap" }}>
            <Button
              variant="outlined"
              startIcon={<UploadFileIcon />}
              onClick={() => fileInputRef.current?.click()}
            >
              Upload sales CSV or Excel
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              hidden
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleUpload(file);
                e.target.value = "";
              }}
            />
            <Typography variant="caption" color="text.secondary">
              Columns: sku, period (YYYY-MM), quantity, amount, currency — optional product_name, customer_name
            </Typography>
          </Stack>
          {uploadMessage && (
            <Alert severity="success" sx={{ mt: 2 }}>
              {uploadMessage}
            </Alert>
          )}
        </CardContent>
      </Card>

      {error && <Alert severity="error">{error}</Alert>}

      {products.length === 0 ? (
        <Alert severity="info">Upload a sales CSV to see a forecast.</Alert>
      ) : (
        <>
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center" }}>
            <TextField select label="Product" size="small" value={productId} onChange={(e) => setProductId(e.target.value)} sx={{ minWidth: 220 }}>
              {products.map((p) => (
                <MenuItem key={p.id} value={p.id}>
                  {p.sku} — {p.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField select label="Model" size="small" value={model} onChange={(e) => setModel(e.target.value as ForecastModel)} sx={{ minWidth: 220 }}>
              {MODELS.map((m) => (
                <MenuItem key={m.value} value={m.value}>
                  {m.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Periods"
              type="number"
              size="small"
              value={periods}
              onChange={(e) => setPeriods(Math.max(1, Math.min(24, Number(e.target.value))))}
              sx={{ width: 110 }}
            />
            <TextField
              label="Unit variable cost"
              type="number"
              size="small"
              value={costInput}
              onChange={(e) => setCostInput(e.target.value)}
              sx={{ width: 170 }}
            />
            <Button variant="contained" onClick={handleSaveCost} disabled={costInput === ""}>
              Save cost
            </Button>
            <Button
              variant="outlined"
              startIcon={<DownloadIcon />}
              onClick={() => downloadForecast(company!.id, productId, model, periods)}
              disabled={!productId}
            >
              Download Excel
            </Button>
          </Stack>

          {loading && <CircularProgress size={24} />}

          {chartOption && (
            <Card variant="outlined">
              <CardContent>
                <EChart option={chartOption} height={360} />
              </CardContent>
            </Card>
          )}

          {forecast && (
            <Grid container spacing={2}>
              {forecast.points.map((p) => (
                <Grid size={{ xs: 12, sm: 6, md: 3 }} key={p.period}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        {p.period}
                      </Typography>
                      <Typography variant="h6" sx={{ fontVariantNumeric: "tabular-nums" }}>
                        {p.forecast.toLocaleString()} {p.currency}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {p.lower_bound.toLocaleString()} – {p.upper_bound.toLocaleString()}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}

          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap" }} spacing={1}>
                <Typography variant="subtitle1">Model accuracy comparison</Typography>
                <Button variant="outlined" size="small" onClick={loadComparison} disabled={!productId || comparisonLoading}>
                  {comparisonLoading ? "Comparing…" : "Compare models"}
                </Button>
              </Stack>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
                Walk-forward backtest: for each historical month, forecasts one period ahead using only the data available
                up to that point, then compares to what actually happened. Lower MAPE is more accurate. The ML models need
                at least 6 months of history to produce a result.
              </Typography>
              {comparisonError && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {comparisonError}
                </Alert>
              )}
              {comparison && (
                <TableContainer sx={{ mt: 2 }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Model</TableCell>
                        <TableCell align="right">MAPE</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {Object.entries(comparison.mape_by_model)
                        .sort(([, a], [, b]) => (a ?? Infinity) - (b ?? Infinity))
                        .map(([modelName, mape], i) => (
                          <TableRow key={modelName}>
                            <TableCell>
                              {MODEL_LABEL[modelName] ?? modelName}
                              {i === 0 && mape !== null && <Chip size="small" color="success" label="Best" sx={{ ml: 1 }} />}
                            </TableCell>
                            <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                              {mape === null ? "—" : `${mape}%`}
                            </TableCell>
                          </TableRow>
                        ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap" }} spacing={1}>
                <Typography variant="subtitle1">Demand prediction (units)</Typography>
                <Button variant="outlined" size="small" onClick={loadDemand} disabled={!productId || demandLoading}>
                  {demandLoading ? "Forecasting…" : "Forecast demand"}
                </Button>
              </Stack>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
                The same models above, applied to units sold instead of revenue — price mix can move independently of
                volume, so a demand forecast (for production/inventory planning) is a different question than a revenue
                forecast, using the currently selected model and periods.
              </Typography>
              {demandError && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {demandError}
                </Alert>
              )}
              {demand && (
                <Grid container spacing={2} sx={{ mt: 0.5 }}>
                  {demand.points.map((p) => (
                    <Grid size={{ xs: 12, sm: 6, md: 3 }} key={p.period}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="body2" color="text.secondary">
                            {p.period}
                          </Typography>
                          <Typography variant="h6" sx={{ fontVariantNumeric: "tabular-nums" }}>
                            {p.forecast_units.toLocaleString()} units
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {p.lower_bound.toLocaleString()} – {p.upper_bound.toLocaleString()}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </Stack>
  );
}
