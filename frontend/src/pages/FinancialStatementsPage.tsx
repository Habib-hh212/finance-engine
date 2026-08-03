import { useEffect, useState } from "react";
import {
  Alert,
  Card,
  Chip,
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
import { getBalanceSheet, getIncomeStatement } from "../api/financialStatements";
import type { AccountAmount, BalanceSheet, IncomeStatement } from "../api/types";

function currentMonthValue() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
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
  const [startMonth, setStartMonth] = useState(currentMonthValue());
  const [endMonth, setEndMonth] = useState(currentMonthValue());
  const [asOfMonth, setAsOfMonth] = useState(currentMonthValue());
  const [incomeStatement, setIncomeStatement] = useState<IncomeStatement | null>(null);
  const [balanceSheet, setBalanceSheet] = useState<BalanceSheet | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!company) return;
    setError(null);
    try {
      const [is, bs] = await Promise.all([
        getIncomeStatement(company.id, `${startMonth}-01`, `${endMonth}-01`),
        getBalanceSheet(company.id, `${asOfMonth}-28`),
      ]);
      setIncomeStatement(is);
      setBalanceSheet(bs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load financial statements");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Financial Statements
      </Typography>
      <Typography variant="caption" color="text.secondary">
        Built from actuals already posted on the Cost Controlling page. There's no double-entry enforcement here, so the
        Balance Sheet shows whether assets equal liabilities + equity rather than assuming it.
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Typography variant="h6">Income Statement</Typography>
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

      <Typography variant="h6">Balance Sheet</Typography>
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
    </Stack>
  );
}
