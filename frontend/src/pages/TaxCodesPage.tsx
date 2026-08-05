import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
  MenuItem,
  Stack,
  Switch,
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
import { listGLAccounts } from "../api/budgets";
import { createTaxCode, getTaxReport, listTaxCodes, updateTaxCode } from "../api/taxCodes";
import type { GLAccount, TaxCode, TaxDirection, TaxReport, TaxType } from "../api/types";

function todayValue() {
  return new Date().toISOString().slice(0, 10);
}

function firstOfYearValue() {
  return new Date(new Date().getFullYear(), 0, 1).toISOString().slice(0, 10);
}

const fmt = (v: number) => v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const TAX_TYPES: TaxType[] = ["vat", "gst", "other"];
const DIRECTIONS: TaxDirection[] = ["output", "input"];

export function TaxCodesPage() {
  const { company } = useCompany();
  const [glAccounts, setGlAccounts] = useState<GLAccount[]>([]);
  const [taxCodes, setTaxCodes] = useState<TaxCode[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [country, setCountry] = useState("");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [taxType, setTaxType] = useState<TaxType>("vat");
  const [ratePct, setRatePct] = useState("");
  const [direction, setDirection] = useState<TaxDirection>("output");
  const [glAccountId, setGlAccountId] = useState("");

  const [reportStart, setReportStart] = useState(firstOfYearValue());
  const [reportEnd, setReportEnd] = useState(todayValue());
  const [report, setReport] = useState<TaxReport | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);

  const load = async () => {
    if (!company) return;
    setError(null);
    try {
      const [accounts, codes] = await Promise.all([listGLAccounts(company.id), listTaxCodes(company.id)]);
      setGlAccounts(accounts);
      setTaxCodes(codes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tax codes");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);

  const handleLoadReport = async () => {
    if (!company) return;
    setReportError(null);
    try {
      setReport(await getTaxReport(company.id, reportStart, reportEnd));
    } catch (err) {
      setReport(null);
      setReportError(err instanceof Error ? err.message : "Failed to load the tax report");
    }
  };

  const handleCreate = async () => {
    if (!company || !country || !code || !name || !ratePct || !glAccountId) return;
    setError(null);
    try {
      await createTaxCode(company.id, country, code, name, taxType, Number(ratePct), direction, glAccountId);
      setCountry("");
      setCode("");
      setName("");
      setRatePct("");
      setGlAccountId("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create the tax code");
    }
  };

  const handleToggleActive = async (taxCode: TaxCode) => {
    if (!company) return;
    setError(null);
    try {
      await updateTaxCode(company.id, taxCode.id, { is_active: !taxCode.is_active });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update the tax code");
    }
  };

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Tax Codes — VAT / GST
      </Typography>
      <Typography variant="caption" color="text.secondary">
        The same approach SAP FI uses for multi-country tax: rather than hard-coding every country's tax law (which
        changes constantly and no small system can keep authoritative), set up one tax code per rate you actually deal
        with — a country, a percentage, and whether it's <strong>output</strong> tax you collect on sales (owed to the
        tax authority) or <strong>input</strong> tax you pay on purchases (usually recoverable). Applying a tax code to
        a journal entry line on the{" "}
        <Link to="/general-ledger" style={{ color: "inherit" }}>
          Bookkeeping
        </Link>{" "}
        page auto-calculates and auto-posts the tax amount to the account you choose below.
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            New Tax Code
          </Typography>
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center" }}>
            <TextField label="Country" size="small" value={country} onChange={(e) => setCountry(e.target.value)} sx={{ width: 180 }} />
            <TextField label="Code" size="small" value={code} onChange={(e) => setCode(e.target.value)} sx={{ width: 140 }} />
            <TextField label="Name" size="small" value={name} onChange={(e) => setName(e.target.value)} sx={{ minWidth: 200, flexGrow: 1 }} />
            <TextField select label="Type" size="small" value={taxType} onChange={(e) => setTaxType(e.target.value as TaxType)} sx={{ width: 120 }}>
              {TAX_TYPES.map((t) => (
                <MenuItem key={t} value={t}>
                  {t.toUpperCase()}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Rate %"
              type="number"
              size="small"
              value={ratePct}
              onChange={(e) => setRatePct(e.target.value)}
              sx={{ width: 110 }}
            />
            <TextField
              select
              label="Direction"
              size="small"
              value={direction}
              onChange={(e) => setDirection(e.target.value as TaxDirection)}
              sx={{ width: 150 }}
            >
              {DIRECTIONS.map((d) => (
                <MenuItem key={d} value={d}>
                  {d === "output" ? "Output (on sales)" : "Input (on purchases)"}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Tax G/L Account"
              size="small"
              value={glAccountId}
              onChange={(e) => setGlAccountId(e.target.value)}
              sx={{ minWidth: 220 }}
            >
              {glAccounts.map((g) => (
                <MenuItem key={g.id} value={g.id}>
                  {g.code} {g.name}
                </MenuItem>
              ))}
            </TextField>
            <Button variant="contained" onClick={handleCreate} disabled={!country || !code || !name || !ratePct || !glAccountId}>
              Add tax code
            </Button>
          </Stack>
        </CardContent>
      </Card>

      <TableContainer component={Card} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Country</TableCell>
              <TableCell>Code</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell align="right">Rate</TableCell>
              <TableCell>Direction</TableCell>
              <TableCell>Posts to</TableCell>
              <TableCell align="center">Active</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {taxCodes.map((tc) => (
              <TableRow key={tc.id}>
                <TableCell>{tc.country}</TableCell>
                <TableCell>{tc.code}</TableCell>
                <TableCell>{tc.name}</TableCell>
                <TableCell>
                  <Chip size="small" label={tc.tax_type.toUpperCase()} />
                </TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                  {tc.rate_pct}%
                </TableCell>
                <TableCell>
                  <Chip size="small" label={tc.direction} color={tc.direction === "output" ? "warning" : "info"} variant="outlined" />
                </TableCell>
                <TableCell>
                  {tc.gl_account_code} {tc.gl_account_name}
                </TableCell>
                <TableCell align="center">
                  <Switch size="small" checked={tc.is_active} onChange={() => handleToggleActive(tc)} />
                </TableCell>
              </TableRow>
            ))}
            {taxCodes.length === 0 && (
              <TableRow>
                <TableCell colSpan={8}>
                  <Typography variant="body2" color="text.secondary">
                    No tax codes yet.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Typography variant="h6">VAT / GST Return</Typography>
      <Typography variant="caption" color="text.secondary">
        Summed straight off the actual tax G/L postings for the period — the same way a real return is built off the
        tax account's activity, not off a separate calculation that could drift from what was actually posted.
      </Typography>
      <Card variant="outlined">
        <CardContent>
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center" }}>
            <TextField
              label="Start"
              type="date"
              size="small"
              value={reportStart}
              onChange={(e) => setReportStart(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              label="End"
              type="date"
              size="small"
              value={reportEnd}
              onChange={(e) => setReportEnd(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <Button variant="contained" onClick={handleLoadReport}>
              Run report
            </Button>
          </Stack>
          {reportError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {reportError}
            </Alert>
          )}
          {report && (
            <Stack spacing={2} sx={{ mt: 2 }}>
              <Stack direction="row" spacing={3} sx={{ flexWrap: "wrap" }}>
                <Typography variant="body2">
                  Output tax collected: <strong>{fmt(report.total_output_tax)}</strong>
                </Typography>
                <Typography variant="body2">
                  Input tax paid: <strong>{fmt(report.total_input_tax)}</strong>
                </Typography>
                <Chip
                  label={
                    report.net_tax_payable >= 0
                      ? `Net payable: ${fmt(report.net_tax_payable)}`
                      : `Net refundable: ${fmt(Math.abs(report.net_tax_payable))}`
                  }
                  color={report.net_tax_payable >= 0 ? "warning" : "success"}
                />
              </Stack>
              <TableContainer component={Card} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Country</TableCell>
                      <TableCell>Code</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Direction</TableCell>
                      <TableCell align="right">Rate</TableCell>
                      <TableCell align="right">Taxable Base</TableCell>
                      <TableCell align="right">Tax Amount</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {report.rows.map((row) => (
                      <TableRow key={row.tax_code_id}>
                        <TableCell>{row.country}</TableCell>
                        <TableCell>{row.code}</TableCell>
                        <TableCell>{row.tax_type.toUpperCase()}</TableCell>
                        <TableCell>{row.direction}</TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                          {row.rate_pct}%
                        </TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                          {fmt(row.taxable_base)}
                        </TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>
                          {fmt(row.tax_amount)}
                        </TableCell>
                      </TableRow>
                    ))}
                    {report.rows.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={7}>
                          <Typography variant="body2" color="text.secondary">
                            No tax postings in this period.
                          </Typography>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </Stack>
          )}
        </CardContent>
      </Card>
    </Stack>
  );
}
