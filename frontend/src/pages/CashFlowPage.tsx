import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  CardContent,
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
import { EChart } from "../components/EChart";
import { useCompany } from "../context/CompanyContext";
import { createCashItem, getCashFlowForecast } from "../api/cashflow";
import type { CashCategory, CashFlowForecastResponse } from "../api/types";

function currentMonthValue() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

const CATEGORIES: CashCategory[] = ["receivable_collection", "payroll", "vendor_payment", "tax", "loan", "interest", "other"];

export function CashFlowPage() {
  const { company } = useCompany();
  const [startMonth, setStartMonth] = useState(currentMonthValue());
  const [periods, setPeriods] = useState(12);
  const [lagDays, setLagDays] = useState(30);
  const [openingBalance, setOpeningBalance] = useState("0");
  const [data, setData] = useState<CashFlowForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [itemCategory, setItemCategory] = useState<CashCategory>("payroll");
  const [itemDirection, setItemDirection] = useState<"in" | "out">("out");
  const [itemPeriod, setItemPeriod] = useState(currentMonthValue());
  const [itemAmount, setItemAmount] = useState("");
  const [itemDescription, setItemDescription] = useState("");

  const load = async () => {
    if (!company) return;
    setError(null);
    try {
      const result = await getCashFlowForecast(company.id, `${startMonth}-01`, periods, lagDays, Number(openingBalance) || 0);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cash flow forecast");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);

  const handleAddItem = async () => {
    if (!company || !itemAmount) return;
    await createCashItem(company.id, itemCategory, itemDirection, `${itemPeriod}-01`, Number(itemAmount), itemDescription || undefined);
    setItemAmount("");
    setItemDescription("");
    await load();
  };

  const chartOption = data
    ? {
        tooltip: { trigger: "axis" as const },
        legend: { data: ["Cash In", "Cash Out", "Closing Balance"], top: 0 },
        grid: { left: 70, right: 70, top: 60, bottom: 40 },
        xAxis: { type: "category" as const, data: data.rows.map((r) => r.period) },
        yAxis: [
          { type: "value" as const, name: "Flow" },
          { type: "value" as const, name: "Balance" },
        ],
        series: [
          {
            name: "Cash In",
            type: "bar" as const,
            yAxisIndex: 0,
            data: data.rows.map((r) => r.cash_in_total),
            itemStyle: { color: "#2f5d50" },
          },
          {
            name: "Cash Out",
            type: "bar" as const,
            yAxisIndex: 0,
            data: data.rows.map((r) => -r.cash_out_total),
            itemStyle: { color: "#b3541e" },
          },
          {
            name: "Closing Balance",
            type: "line" as const,
            yAxisIndex: 1,
            data: data.rows.map((r) => r.closing_balance),
            itemStyle: { color: "#1f3a5f" },
            lineStyle: { color: "#1f3a5f" },
            symbol: "circle",
          },
        ],
      }
    : null;

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Cash Flow Forecast
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center" }}>
        <TextField label="Start month" type="month" size="small" value={startMonth} onChange={(e) => setStartMonth(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
        <TextField label="Periods" type="number" size="small" value={periods} onChange={(e) => setPeriods(Number(e.target.value))} sx={{ width: 110 }} />
        <TextField label="Collection lag (days)" type="number" size="small" value={lagDays} onChange={(e) => setLagDays(Number(e.target.value))} sx={{ width: 170 }} />
        <TextField label="Opening balance" type="number" size="small" value={openingBalance} onChange={(e) => setOpeningBalance(e.target.value)} sx={{ width: 160 }} />
        <Button variant="contained" onClick={load}>
          Refresh
        </Button>
      </Stack>

      {chartOption && (
        <Card variant="outlined">
          <CardContent>
            <EChart option={chartOption} height={340} />
          </CardContent>
        </Card>
      )}

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle2" gutterBottom>
            Add manual cash item
          </Typography>
          <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", alignItems: "center" }}>
            <TextField select label="Category" size="small" value={itemCategory} onChange={(e) => setItemCategory(e.target.value as CashCategory)} sx={{ minWidth: 180 }}>
              {CATEGORIES.map((c) => (
                <MenuItem key={c} value={c}>
                  {c.replace("_", " ")}
                </MenuItem>
              ))}
            </TextField>
            <TextField select label="Direction" size="small" value={itemDirection} onChange={(e) => setItemDirection(e.target.value as "in" | "out")} sx={{ width: 110 }}>
              <MenuItem value="in">In</MenuItem>
              <MenuItem value="out">Out</MenuItem>
            </TextField>
            <TextField label="Period" type="month" size="small" value={itemPeriod} onChange={(e) => setItemPeriod(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
            <TextField label="Amount" type="number" size="small" value={itemAmount} onChange={(e) => setItemAmount(e.target.value)} sx={{ width: 140 }} />
            <TextField label="Description (optional)" size="small" value={itemDescription} onChange={(e) => setItemDescription(e.target.value)} />
            <Button variant="outlined" onClick={handleAddItem} disabled={!itemAmount}>
              Add
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {data && (
        <TableContainer component={Card} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Period</TableCell>
                <TableCell align="right">Cash In</TableCell>
                <TableCell align="right">Cash Out</TableCell>
                <TableCell align="right">Net</TableCell>
                <TableCell align="right">Opening</TableCell>
                <TableCell align="right">Closing</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.rows.map((r) => (
                <TableRow key={r.period}>
                  <TableCell>{r.period}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                    {r.cash_in_total.toLocaleString()}
                  </TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                    {r.cash_out_total.toLocaleString()}
                  </TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", color: r.net_cash_flow < 0 ? "error.main" : "success.main" }}>
                    {r.net_cash_flow.toLocaleString()}
                  </TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                    {r.opening_balance.toLocaleString()}
                  </TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600, color: r.closing_balance < 0 ? "error.main" : "text.primary" }}>
                    {r.closing_balance.toLocaleString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Stack>
  );
}
