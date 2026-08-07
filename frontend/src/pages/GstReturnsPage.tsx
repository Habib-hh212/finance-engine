import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  MenuItem,
  Stack,
  Switch,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { TabPanel } from "../components/TabPanel";
import { useCompany } from "../context/CompanyContext";
import { listGLAccounts } from "../api/budgets";
import { createGstRate, getGstr1Report, getGstr3bReport, listGstRates, updateGstRate } from "../api/gst";
import { updateCompany } from "../api/companies";
import type { GLAccount, GstDirection, GstRate, Gstr1Report, Gstr3bReport } from "../api/types";

function todayValue() {
  return new Date().toISOString().slice(0, 10);
}

function firstOfYearValue() {
  return new Date(new Date().getFullYear(), 0, 1).toISOString().slice(0, 10);
}

const fmt = (v: number) => v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const DIRECTIONS: GstDirection[] = ["output", "input"];

export function GstReturnsPage() {
  const { company, refresh } = useCompany();
  const [tab, setTab] = useState(0);
  const [glAccounts, setGlAccounts] = useState<GLAccount[]>([]);
  const [rates, setRates] = useState<GstRate[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [homeState, setHomeState] = useState("");
  const [homeStateSaving, setHomeStateSaving] = useState(false);

  const [description, setDescription] = useState("");
  const [ratePct, setRatePct] = useState("");
  const [direction, setDirection] = useState<GstDirection>("output");
  const [cgstAccount, setCgstAccount] = useState("");
  const [sgstAccount, setSgstAccount] = useState("");
  const [igstAccount, setIgstAccount] = useState("");

  const [reportStart, setReportStart] = useState(firstOfYearValue());
  const [reportEnd, setReportEnd] = useState(todayValue());
  const [gstr1, setGstr1] = useState<Gstr1Report | null>(null);
  const [gstr3b, setGstr3b] = useState<Gstr3bReport | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);

  const load = async () => {
    if (!company) return;
    setError(null);
    setHomeState(company.home_state ?? "");
    try {
      const [accounts, gstRates] = await Promise.all([listGLAccounts(company.id), listGstRates(company.id)]);
      setGlAccounts(accounts);
      setRates(gstRates);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load GST setup");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);

  const handleSaveHomeState = async () => {
    if (!company) return;
    setHomeStateSaving(true);
    setError(null);
    try {
      await updateCompany(company.id, { home_state: homeState || null });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save the home state");
    } finally {
      setHomeStateSaving(false);
    }
  };

  const handleLoadReports = async () => {
    if (!company) return;
    setReportError(null);
    try {
      const [r1, r3b] = await Promise.all([
        getGstr1Report(company.id, reportStart, reportEnd),
        getGstr3bReport(company.id, reportStart, reportEnd),
      ]);
      setGstr1(r1);
      setGstr3b(r3b);
    } catch (err) {
      setGstr1(null);
      setGstr3b(null);
      setReportError(err instanceof Error ? err.message : "Failed to load the GST returns");
    }
  };

  const handleCreate = async () => {
    if (!company || !description || !ratePct || !cgstAccount || !sgstAccount || !igstAccount) return;
    setError(null);
    try {
      await createGstRate(company.id, description, Number(ratePct), direction, cgstAccount, sgstAccount, igstAccount);
      setDescription("");
      setRatePct("");
      setCgstAccount("");
      setSgstAccount("");
      setIgstAccount("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create the GST rate");
    }
  };

  const handleToggleActive = async (rate: GstRate) => {
    if (!company) return;
    setError(null);
    try {
      await updateGstRate(company.id, rate.id, { is_active: !rate.is_active });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update the GST rate");
    }
  };

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        GST Returns (India)
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)}>
          <Tab label="GST Rates" />
          <Tab label="GSTR-1 / GSTR-3B" />
          <Tab label="Help" />
        </Tabs>
      </Box>

      <TabPanel value={tab} index={0}>
        <Stack spacing={2}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Company Home State
              </Typography>
              <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
                <TextField label="Home state" size="small" value={homeState} onChange={(e) => setHomeState(e.target.value)} sx={{ width: 220 }} />
                <Button variant="outlined" onClick={handleSaveHomeState} disabled={homeStateSaving}>
                  Save
                </Button>
              </Stack>
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                New GST Rate
              </Typography>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <TextField label="Description" size="small" fullWidth placeholder="Standard 18%" value={description} onChange={(e) => setDescription(e.target.value)} />
                </Grid>
                <Grid size={{ xs: 6, sm: 3, md: 1.5 }}>
                  <TextField label="Rate %" type="number" size="small" fullWidth value={ratePct} onChange={(e) => setRatePct(e.target.value)} />
                </Grid>
                <Grid size={{ xs: 6, sm: 3, md: 2.5 }}>
                  <TextField select label="Direction" size="small" fullWidth value={direction} onChange={(e) => setDirection(e.target.value as GstDirection)}>
                    {DIRECTIONS.map((d) => (
                      <MenuItem key={d} value={d}>
                        {d === "output" ? "Output (on sales)" : "Input (on purchases)"}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
                <Grid size={{ xs: 12, sm: 4, md: 1.67 }}>
                  <TextField select label="CGST account" size="small" fullWidth value={cgstAccount} onChange={(e) => setCgstAccount(e.target.value)}>
                    {glAccounts.map((g) => (
                      <MenuItem key={g.id} value={g.id}>
                        {g.code} {g.name}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
                <Grid size={{ xs: 12, sm: 4, md: 1.67 }}>
                  <TextField select label="SGST account" size="small" fullWidth value={sgstAccount} onChange={(e) => setSgstAccount(e.target.value)}>
                    {glAccounts.map((g) => (
                      <MenuItem key={g.id} value={g.id}>
                        {g.code} {g.name}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
                <Grid size={{ xs: 12, sm: 4, md: 1.66 }}>
                  <TextField select label="IGST account" size="small" fullWidth value={igstAccount} onChange={(e) => setIgstAccount(e.target.value)}>
                    {glAccounts.map((g) => (
                      <MenuItem key={g.id} value={g.id}>
                        {g.code} {g.name}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
              </Grid>
              <Button variant="contained" sx={{ mt: 2 }} onClick={handleCreate} disabled={!description || !ratePct || !cgstAccount || !sgstAccount || !igstAccount}>
                Add rate
              </Button>
            </CardContent>
          </Card>

          <TableContainer component={Card} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Description</TableCell>
                  <TableCell align="right">Rate</TableCell>
                  <TableCell>Direction</TableCell>
                  <TableCell align="center">Active</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rates.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell>{r.description}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                      {r.rate_pct}%
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={r.direction} color={r.direction === "output" ? "warning" : "info"} variant="outlined" />
                    </TableCell>
                    <TableCell align="center">
                      <Switch size="small" checked={r.is_active} onChange={() => handleToggleActive(r)} />
                    </TableCell>
                  </TableRow>
                ))}
                {rates.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4}>
                      <Typography variant="body2" color="text.secondary">
                        No GST rates yet.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Stack>
      </TabPanel>

      <TabPanel value={tab} index={1}>
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
              <Button variant="contained" onClick={handleLoadReports}>
                Run reports
              </Button>
            </Stack>
            {reportError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {reportError}
              </Alert>
            )}

            {gstr3b && (
              <Stack spacing={2} sx={{ mt: 3 }}>
                <Typography variant="subtitle1">GSTR-3B (summary return)</Typography>
                <Stack direction="row" spacing={3} sx={{ flexWrap: "wrap" }}>
                  <Typography variant="body2">
                    Outward taxable value: <strong>{fmt(gstr3b.outward_taxable_value)}</strong>
                  </Typography>
                  <Typography variant="body2">
                    Inward taxable value: <strong>{fmt(gstr3b.inward_taxable_value)}</strong>
                  </Typography>
                  <Chip
                    label={
                      gstr3b.net_tax_payable >= 0
                        ? `Net payable: ${fmt(gstr3b.net_tax_payable)}`
                        : `Net refundable: ${fmt(Math.abs(gstr3b.net_tax_payable))}`
                    }
                    color={gstr3b.net_tax_payable >= 0 ? "warning" : "success"}
                  />
                </Stack>
                <TableContainer component={Card} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Head</TableCell>
                        <TableCell align="right">Output</TableCell>
                        <TableCell align="right">Input (ITC)</TableCell>
                        <TableCell align="right">Net Payable</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      <TableRow>
                        <TableCell>CGST</TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(gstr3b.output_cgst)}</TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(gstr3b.input_cgst)}</TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>{fmt(gstr3b.net_cgst_payable)}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>SGST</TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(gstr3b.output_sgst)}</TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(gstr3b.input_sgst)}</TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>{fmt(gstr3b.net_sgst_payable)}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>IGST</TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(gstr3b.output_igst)}</TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(gstr3b.input_igst)}</TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>{fmt(gstr3b.net_igst_payable)}</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>
              </Stack>
            )}

            {gstr1 && (
              <Stack spacing={2} sx={{ mt: 3 }}>
                <Typography variant="subtitle1">GSTR-1 (outward supplies)</Typography>

                <Typography variant="subtitle2">B2B invoices</Typography>
                <TableContainer component={Card} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Invoice #</TableCell>
                        <TableCell>Date</TableCell>
                        <TableCell>Customer</TableCell>
                        <TableCell>GSTIN</TableCell>
                        <TableCell align="right">Taxable Value</TableCell>
                        <TableCell align="right">Rate</TableCell>
                        <TableCell align="right">CGST</TableCell>
                        <TableCell align="right">SGST</TableCell>
                        <TableCell align="right">IGST</TableCell>
                        <TableCell align="right">Invoice Value</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {gstr1.b2b_rows.map((row) => (
                        <TableRow key={row.invoice_id}>
                          <TableCell>{row.invoice_number}</TableCell>
                          <TableCell>{row.invoice_date}</TableCell>
                          <TableCell>{row.customer_name}</TableCell>
                          <TableCell>{row.customer_gstin}</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.taxable_value)}</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{row.rate_pct}%</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.cgst_amount)}</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.sgst_amount)}</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.igst_amount)}</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>{fmt(row.invoice_value)}</TableCell>
                        </TableRow>
                      ))}
                      {gstr1.b2b_rows.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={10}>
                            <Typography variant="body2" color="text.secondary">No B2B invoices in this period.</Typography>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>

                <Typography variant="subtitle2">B2C (aggregated by place of supply &amp; rate)</Typography>
                <TableContainer component={Card} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Place of Supply</TableCell>
                        <TableCell align="right">Rate</TableCell>
                        <TableCell align="right">Taxable Value</TableCell>
                        <TableCell align="right">CGST</TableCell>
                        <TableCell align="right">SGST</TableCell>
                        <TableCell align="right">IGST</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {gstr1.b2c_rows.map((row, idx) => (
                        <TableRow key={`${row.place_of_supply}-${row.rate_pct}-${idx}`}>
                          <TableCell>{row.place_of_supply}</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{row.rate_pct}%</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.taxable_value)}</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.cgst_amount)}</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.sgst_amount)}</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.igst_amount)}</TableCell>
                        </TableRow>
                      ))}
                      {gstr1.b2c_rows.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={6}>
                            <Typography variant="body2" color="text.secondary">No B2C invoices in this period.</Typography>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>

                <Typography variant="subtitle2">HSN/SAC summary</Typography>
                <TableContainer component={Card} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>HSN/SAC</TableCell>
                        <TableCell align="right">Taxable Value</TableCell>
                        <TableCell align="right">CGST</TableCell>
                        <TableCell align="right">SGST</TableCell>
                        <TableCell align="right">IGST</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {gstr1.hsn_rows.map((row) => (
                        <TableRow key={row.hsn_sac_code}>
                          <TableCell>{row.hsn_sac_code}</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.taxable_value)}</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.cgst_amount)}</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.sgst_amount)}</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.igst_amount)}</TableCell>
                        </TableRow>
                      ))}
                      {gstr1.hsn_rows.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={5}>
                            <Typography variant="body2" color="text.secondary">No HSN activity in this period.</Typography>
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
      </TabPanel>

      <TabPanel value={tab} index={2}>
        <Stack spacing={2}>
          <Typography variant="body2">
            A GST rate splits into CGST + SGST when the counterparty is in your own state, or IGST alone when
            they're not — decided automatically by comparing your company's home state against the customer's or
            vendor's state whenever you apply a rate on the{" "}
            <Link to="/receivables-payables" style={{ color: "inherit" }}>
              Receivables &amp; Payables
            </Link>{" "}
            page.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Set your home state and create rates on the GST Rates tab first. Tag HSN/SAC codes on the{" "}
            <Link to="/chart-of-accounts" style={{ color: "inherit" }}>
              Chart of Accounts
            </Link>{" "}
            for the GSTR-1 HSN summary. GSTR-3B is the summary return (net tax payable per head); GSTR-1 is the
            detailed outward-supply return (per invoice, per HSN).
          </Typography>
        </Stack>
      </TabPanel>
    </Stack>
  );
}
