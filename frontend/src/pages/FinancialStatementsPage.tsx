import { useEffect, useRef, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Chip,
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
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import SlideshowIcon from "@mui/icons-material/Slideshow";
import { EChart } from "../components/EChart";
import { useCompany } from "../context/CompanyContext";
import {
  downloadAllBooks,
  downloadBalanceSheet,
  downloadBoardReportPdf,
  downloadBoardReportPptx,
  downloadIncomeStatement,
  getBalanceSheet,
  getCashFlowStatement,
  getIncomeStatement,
  getIncomeStatementTrend,
  uploadStatements,
} from "../api/financialStatements";
import { downloadStatementForecast, getBalanceSheetForecast, getIncomeStatementForecast } from "../api/statementForecast";
import type {
  AccountAmount,
  BalanceSheet,
  BalanceSheetForecastPeriod,
  CashFlowStatement,
  IncomeStatement,
  IncomeStatementForecastPeriod,
  IncomeStatementTrendPoint,
  StatementForecastMethod,
} from "../api/types";

const TREND_HISTORY_FLOOR = "2000-01-01";

const TREND_MODELS: { value: string; label: string }[] = [
  { value: "exponential_smoothing", label: "Exponential Smoothing" },
  { value: "moving_average", label: "Moving Average" },
  { value: "weighted_average", label: "Weighted Average" },
  { value: "random_forest", label: "Random Forest (ML, picks up trend)" },
  { value: "gradient_boosting", label: "Gradient Boosting (ML, picks up trend)" },
];

function currentMonthValue() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function nextMonthValue() {
  const now = new Date();
  const next = new Date(now.getFullYear(), now.getMonth() + 1, 1);
  return `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}`;
}

const fmt = (v: number) => v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function AccountRows({ lines }: { lines: AccountAmount[] }) {
  if (lines.length === 0) {
    return (
      <TableRow>
        <TableCell colSpan={2}>
          <Typography variant="body2" color="text.secondary">
            No actuals posted to this category yet.
          </Typography>
        </TableCell>
      </TableRow>
    );
  }
  return (
    <>
      {lines.map((line) => (
        <TableRow key={line.gl_account_id}>
          <TableCell>
            {line.code} {line.name}
          </TableCell>
          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
            {fmt(line.amount)}
          </TableCell>
        </TableRow>
      ))}
    </>
  );
}

export function FinancialStatementsPage() {
  const { company } = useCompany();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [startMonth, setStartMonth] = useState(currentMonthValue());
  const [endMonth, setEndMonth] = useState(currentMonthValue());
  const [asOfMonth, setAsOfMonth] = useState(currentMonthValue());
  const [incomeStatement, setIncomeStatement] = useState<IncomeStatement | null>(null);
  const [balanceSheet, setBalanceSheet] = useState<BalanceSheet | null>(null);
  const [cashFlow, setCashFlow] = useState<CashFlowStatement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [trend, setTrend] = useState<IncomeStatementTrendPoint[]>([]);

  const [forecastStartMonth, setForecastStartMonth] = useState(nextMonthValue());
  const [forecastPeriods, setForecastPeriods] = useState("6");
  const [dsoDays, setDsoDays] = useState("45");
  const [dpoDays, setDpoDays] = useState("30");
  const [collectionLagDays, setCollectionLagDays] = useState("30");
  const [forecastMethod, setForecastMethod] = useState<StatementForecastMethod>("driver_based");
  const [trendModel, setTrendModel] = useState("exponential_smoothing");
  const [incomeForecast, setIncomeForecast] = useState<IncomeStatementForecastPeriod[]>([]);
  const [balanceForecast, setBalanceForecast] = useState<BalanceSheetForecastPeriod[]>([]);
  const [forecastError, setForecastError] = useState<string | null>(null);

  const load = async () => {
    if (!company) return;
    setError(null);
    try {
      const [is, bs, trendRows, cf] = await Promise.all([
        getIncomeStatement(company.id, `${startMonth}-01`, `${endMonth}-01`),
        getBalanceSheet(company.id, `${asOfMonth}-28`),
        // Deliberately not tied to the Income Statement's own from/to fields --
        // the trend chart's whole point is showing whatever multi-year history
        // exists, so it always asks for everything back to a floor date well
        // before any real company data would predate.
        getIncomeStatementTrend(company.id, TREND_HISTORY_FLOOR, `${endMonth}-01`),
        getCashFlowStatement(company.id, `${startMonth}-01`, `${endMonth}-01`),
      ]);
      setIncomeStatement(is);
      setBalanceSheet(bs);
      setTrend(trendRows);
      setCashFlow(cf);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load financial statements");
    }
  };

  const loadForecast = async () => {
    if (!company) return;
    setForecastError(null);
    try {
      const [incRows, balRows] = await Promise.all([
        getIncomeStatementForecast(company.id, `${forecastStartMonth}-01`, Number(forecastPeriods), forecastMethod, trendModel),
        forecastMethod === "historical_trend"
          ? Promise.resolve([])
          : getBalanceSheetForecast(
              company.id,
              `${forecastStartMonth}-01`,
              Number(forecastPeriods),
              Number(dsoDays),
              Number(dpoDays),
              Number(collectionLagDays),
            ),
      ]);
      setIncomeForecast(incRows);
      setBalanceForecast(balRows);
    } catch (err) {
      setForecastError(err instanceof Error ? err.message : "Failed to load statement forecast");
    }
  };

  useEffect(() => {
    load();
    loadForecast();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);

  const handleUploadStatements = async (file: File) => {
    if (!company) return;
    setUploadMessage(null);
    setError(null);
    try {
      const result = await uploadStatements(company.id, file);
      setUploadMessage(
        `Imported ${result.rows_imported} rows (${result.accounts_created} new GL account(s), ${result.cost_centers_created} new cost center(s)).`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  };

  const trendChartOption = trend.length
    ? {
        tooltip: { trigger: "axis" as const },
        legend: { data: ["Revenue", "Expense", "Net Profit"], top: 0 },
        grid: { left: 70, right: 30, top: 50, bottom: 40 },
        xAxis: { type: "category" as const, data: trend.map((p) => p.period) },
        yAxis: { type: "value" as const },
        series: [
          { name: "Revenue", type: "bar" as const, data: trend.map((p) => p.revenue), color: "#2f5d50" },
          { name: "Expense", type: "bar" as const, data: trend.map((p) => p.expense), color: "#b5533c" },
          { name: "Net Profit", type: "line" as const, data: trend.map((p) => p.net_profit), color: "#1f2937" },
        ],
      }
    : null;

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Financial Statements
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Card variant="outlined">
        <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap", p: 2 }}>
          <Button variant="outlined" startIcon={<UploadFileIcon />} onClick={() => fileInputRef.current?.click()}>
            Upload historical statements
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls,.csv"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleUploadStatements(file);
              e.target.value = "";
            }}
          />
          <Typography variant="caption" color="text.secondary">
            Excel or CSV columns: gl_account_code, category (revenue/expense/asset/liability/equity), period (YYYY-MM),
            amount — optional gl_account_name, currency, cost_center_code. Bulk-load however many years of history
            you have (three, four, more) in one upload; there's no cap on how much it stores.
          </Typography>
        </Stack>
        {uploadMessage && (
          <Alert severity="success" sx={{ mx: 2, mb: 2 }}>
            {uploadMessage}
          </Alert>
        )}
      </Card>

      {trendChartOption && (
        <Card variant="outlined">
          <Stack sx={{ p: 2 }} spacing={1}>
            <Typography variant="subtitle1">Revenue / Expense / Net Profit Trend</Typography>
            <EChart option={trendChartOption} height={320} />
          </Stack>
        </Card>
      )}

      <Card variant="outlined">
        <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap", p: 2 }}>
          <Typography variant="subtitle1" sx={{ mr: "auto" }}>
            Board Report
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ width: "100%", mb: 1 }}>
            KPIs, Income Statement, and Balance Sheet for the ranges above, as a formatted document instead of a raw
            export.
          </Typography>
          <Button
            variant="outlined"
            size="small"
            startIcon={<PictureAsPdfIcon />}
            onClick={() => downloadBoardReportPdf(company!.id, `${startMonth}-01`, `${endMonth}-01`, `${asOfMonth}-28`)}
            disabled={!company}
          >
            Download PDF
          </Button>
          <Button
            variant="outlined"
            size="small"
            startIcon={<SlideshowIcon />}
            onClick={() => downloadBoardReportPptx(company!.id, `${startMonth}-01`, `${endMonth}-01`, `${asOfMonth}-28`)}
            disabled={!company}
          >
            Download PowerPoint
          </Button>
        </Stack>
      </Card>

      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap" }}>
        <Typography variant="h6">Income Statement</Typography>
        <Button
          size="small"
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={() => downloadIncomeStatement(company!.id, `${startMonth}-01`, `${endMonth}-01`)}
          disabled={!company}
        >
          Download Excel
        </Button>
      </Stack>
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
      </Stack>
      {incomeStatement && (
        <TableContainer component={Card} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell colSpan={2}>
                  <Typography variant="subtitle2">Revenue</Typography>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <AccountRows lines={incomeStatement.revenue_lines} />
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Total Revenue</TableCell>
                <TableCell align="right" sx={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
                  {fmt(incomeStatement.total_revenue)}
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell colSpan={2} sx={{ pt: 2 }}>
                  <Typography variant="subtitle2">Expenses</Typography>
                </TableCell>
              </TableRow>
              <AccountRows lines={incomeStatement.expense_lines} />
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Total Expense</TableCell>
                <TableCell align="right" sx={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
                  {fmt(incomeStatement.total_expense)}
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell sx={{ fontWeight: 700, borderTop: "2px solid", borderColor: "divider" }}>Net Profit</TableCell>
                <TableCell
                  align="right"
                  sx={{
                    fontWeight: 700,
                    fontVariantNumeric: "tabular-nums",
                    borderTop: "2px solid",
                    borderColor: "divider",
                    color: incomeStatement.net_profit < 0 ? "error.main" : "success.main",
                  }}
                >
                  {fmt(incomeStatement.net_profit)}
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap" }}>
        <Typography variant="h6">Balance Sheet</Typography>
        <Button
          size="small"
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={() => downloadBalanceSheet(company!.id, `${asOfMonth}-28`)}
          disabled={!company}
        >
          Download Excel
        </Button>
      </Stack>
      <TextField
        label="As of"
        type="month"
        size="small"
        value={asOfMonth}
        onChange={(e) => setAsOfMonth(e.target.value)}
        slotProps={{ inputLabel: { shrink: true } }}
      />
      {balanceSheet && (
        <TableContainer component={Card} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell colSpan={2}>
                  <Typography variant="subtitle2">Assets</Typography>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <AccountRows lines={balanceSheet.asset_lines} />
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Total Assets</TableCell>
                <TableCell align="right" sx={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
                  {fmt(balanceSheet.total_assets)}
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell colSpan={2} sx={{ pt: 2 }}>
                  <Typography variant="subtitle2">Liabilities</Typography>
                </TableCell>
              </TableRow>
              <AccountRows lines={balanceSheet.liability_lines} />
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Total Liabilities</TableCell>
                <TableCell align="right" sx={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
                  {fmt(balanceSheet.total_liabilities)}
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell colSpan={2} sx={{ pt: 2 }}>
                  <Typography variant="subtitle2">Equity</Typography>
                </TableCell>
              </TableRow>
              <AccountRows lines={balanceSheet.equity_lines} />
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Total Equity</TableCell>
                <TableCell align="right" sx={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
                  {fmt(balanceSheet.total_equity)}
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell sx={{ fontWeight: 700, borderTop: "2px solid", borderColor: "divider" }}>
                  Assets vs. Liabilities + Equity
                </TableCell>
                <TableCell align="right" sx={{ borderTop: "2px solid", borderColor: "divider" }}>
                  <Chip
                    size="small"
                    label={balanceSheet.is_balanced ? "Balanced" : `Off by ${fmt(Math.abs(balanceSheet.difference))}`}
                    color={balanceSheet.is_balanced ? "success" : "error"}
                  />
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap" }}>
        <Typography variant="h6">Cash Flow Statement</Typography>
        <Button
          size="small"
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={() => downloadAllBooks(company!.id, `${startMonth}-01`, `${endMonth}-01`)}
          disabled={!company}
        >
          Download all books
        </Button>
      </Stack>
      <Typography variant="caption" color="text.secondary">
        The indirect method, built from what's already posted -- not the forward-looking Cash Flow Forecast elsewhere in
        this app. Financing activity is reported as 0: this system has no loan or equity-transaction model, so rather
        than fabricate a number, it's left untracked. Proves itself the same way the Balance Sheet does: opening cash +
        the net change computed here should equal the actual closing cash balance.
      </Typography>
      {cashFlow && (
        <TableContainer component={Card} variant="outlined">
          <Table size="small">
            <TableBody>
              <TableRow>
                <TableCell colSpan={2}>
                  <Typography variant="subtitle2">Operating Activities</Typography>
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Net income</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(cashFlow.net_income)}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Depreciation (add back)</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(cashFlow.depreciation_add_back)}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Increase in receivables</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>({fmt(cashFlow.increase_in_receivables)})</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Increase in payables</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(cashFlow.increase_in_payables)}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Net Operating Cash Flow</TableCell>
                <TableCell align="right" sx={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>{fmt(cashFlow.net_operating_cash_flow)}</TableCell>
              </TableRow>

              <TableRow>
                <TableCell colSpan={2} sx={{ pt: 2 }}>
                  <Typography variant="subtitle2">Investing Activities</Typography>
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Asset acquisitions</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>({fmt(cashFlow.asset_acquisitions)})</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Disposal proceeds</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(cashFlow.disposal_proceeds)}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Net Investing Cash Flow</TableCell>
                <TableCell align="right" sx={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>{fmt(cashFlow.net_investing_cash_flow)}</TableCell>
              </TableRow>

              <TableRow>
                <TableCell colSpan={2} sx={{ pt: 2 }}>
                  <Typography variant="subtitle2">Financing Activities</Typography>
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell>
                  <Typography variant="caption" color="text.secondary">Not tracked (no loan/equity model)</Typography>
                </TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(cashFlow.net_financing_cash_flow)}</TableCell>
              </TableRow>

              <TableRow>
                <TableCell sx={{ fontWeight: 700, borderTop: "2px solid", borderColor: "divider" }}>Net Change in Cash</TableCell>
                <TableCell align="right" sx={{ fontWeight: 700, borderTop: "2px solid", borderColor: "divider", fontVariantNumeric: "tabular-nums" }}>
                  {fmt(cashFlow.net_change_in_cash)}
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Opening cash balance</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(cashFlow.opening_cash_balance)}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Closing cash balance</TableCell>
                <TableCell align="right" sx={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>{fmt(cashFlow.closing_cash_balance)}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell colSpan={2}>
                  <Chip
                    size="small"
                    label={cashFlow.is_proven ? "Proven: opening + change = closing" : "Not proven -- check untagged cash/AR/AP accounts"}
                    color={cashFlow.is_proven ? "success" : "error"}
                  />
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap" }}>
        <Typography variant="h6">Financial Statement Forecast</Typography>
        <Button
          size="small"
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={() =>
            downloadStatementForecast(company!.id, `${forecastStartMonth}-01`, Number(forecastPeriods), forecastMethod, trendModel)
          }
          disabled={!company}
        >
          Download Excel
        </Button>
      </Stack>
      <Typography variant="caption" color="text.secondary">
        <strong>Driver-based</strong> (default): revenue from the existing Sales Forecast; expense from approved budget
        lines on expense-category GL accounts; Balance Sheet lines derived from those via DSO/DPO. <strong>Historical
        trend</strong>: revenue and expense projected straight from their own multi-year actuals history (the same
        approach as manually trend-extrapolating a few years of downloaded statements in a spreadsheet) — pick an ML
        model (Random Forest / Gradient Boosting) if you want it to actually pick up a growth or decline trend rather
        than a flat projection. Historical trend only produces an Income Statement; the Balance Sheet still needs the
        driver-based DSO/DPO method. Tag GL accounts with a forecast role (cash / accounts receivable / accounts
        payable) on the Budget Planning page to feed the driver-based Balance Sheet.
      </Typography>
      {forecastError && <Alert severity="error">{forecastError}</Alert>}
      <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap" }}>
        <TextField
          select
          label="Forecast method"
          size="small"
          value={forecastMethod}
          onChange={(e) => setForecastMethod(e.target.value as StatementForecastMethod)}
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="driver_based">Driver-based</MenuItem>
          <MenuItem value="historical_trend">Historical trend</MenuItem>
        </TextField>
        {forecastMethod === "historical_trend" && (
          <TextField
            select
            label="Trend model"
            size="small"
            value={trendModel}
            onChange={(e) => setTrendModel(e.target.value)}
            sx={{ minWidth: 240 }}
          >
            {TREND_MODELS.map((m) => (
              <MenuItem key={m.value} value={m.value}>
                {m.label}
              </MenuItem>
            ))}
          </TextField>
        )}
        <TextField
          label="Start"
          type="month"
          size="small"
          value={forecastStartMonth}
          onChange={(e) => setForecastStartMonth(e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <TextField label="Periods" type="number" size="small" value={forecastPeriods} onChange={(e) => setForecastPeriods(e.target.value)} sx={{ width: 100 }} />
        {forecastMethod === "driver_based" && (
          <>
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
          </>
        )}
        <Chip label="Refresh" onClick={loadForecast} color="primary" clickable />
      </Stack>

      {incomeForecast.length > 0 && (
        <TableContainer component={Card} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Period</TableCell>
                <TableCell align="right">Revenue</TableCell>
                <TableCell align="right">Expense</TableCell>
                <TableCell align="right">Net Profit</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {incomeForecast.map((row) => (
                <TableRow key={row.period}>
                  <TableCell>{row.period}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.revenue_forecast)}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.expense_forecast)}</TableCell>
                  <TableCell
                    align="right"
                    sx={{ fontVariantNumeric: "tabular-nums", color: row.net_profit_forecast < 0 ? "error.main" : "success.main" }}
                  >
                    {fmt(row.net_profit_forecast)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {balanceForecast.length > 0 && (
        <TableContainer component={Card} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Period</TableCell>
                <TableCell align="right">AR</TableCell>
                <TableCell align="right">Cash</TableCell>
                <TableCell align="right">Other Assets</TableCell>
                <TableCell align="right">Total Assets</TableCell>
                <TableCell align="right">AP</TableCell>
                <TableCell align="right">Other Liab.</TableCell>
                <TableCell align="right">Total Liab.</TableCell>
                <TableCell align="right">Equity</TableCell>
                <TableCell align="center">Financing Gap</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {balanceForecast.map((row) => (
                <TableRow key={row.period}>
                  <TableCell>{row.period}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.accounts_receivable)}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.cash)}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.other_assets)}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>{fmt(row.total_assets)}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.accounts_payable)}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.other_liabilities)}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>{fmt(row.total_liabilities)}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>{fmt(row.equity)}</TableCell>
                  <TableCell align="center">
                    <Chip
                      size="small"
                      label={row.is_balanced ? "None" : fmt(row.difference)}
                      color={row.is_balanced ? "success" : "warning"}
                    />
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
