import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
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
import { createTdsSection, getTdsReport, listTdsSections, updateTdsSection } from "../api/tds";
import type { TdsSection, TdsSummary } from "../api/types";

function todayValue() {
  return new Date().toISOString().slice(0, 10);
}

function firstOfYearValue() {
  return new Date(new Date().getFullYear(), 0, 1).toISOString().slice(0, 10);
}

const fmt = (v: number) => v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function TdsPage() {
  const { company } = useCompany();
  const [tab, setTab] = useState(0);
  const [sections, setSections] = useState<TdsSection[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [sectionCode, setSectionCode] = useState("");
  const [description, setDescription] = useState("");
  const [ratePct, setRatePct] = useState("");

  const [reportStart, setReportStart] = useState(firstOfYearValue());
  const [reportEnd, setReportEnd] = useState(todayValue());
  const [report, setReport] = useState<TdsSummary | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);

  const load = async () => {
    if (!company) return;
    setError(null);
    try {
      setSections(await listTdsSections(company.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load TDS sections");
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
      setReport(await getTdsReport(company.id, reportStart, reportEnd));
    } catch (err) {
      setReport(null);
      setReportError(err instanceof Error ? err.message : "Failed to load the TDS report");
    }
  };

  const handleCreate = async () => {
    if (!company || !sectionCode || !description || !ratePct) return;
    setError(null);
    try {
      await createTdsSection(company.id, sectionCode, description, Number(ratePct));
      setSectionCode("");
      setDescription("");
      setRatePct("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create the TDS section");
    }
  };

  const handleToggleActive = async (section: TdsSection) => {
    if (!company) return;
    setError(null);
    try {
      await updateTdsSection(company.id, section.id, { is_active: !section.is_active });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update the TDS section");
    }
  };

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        TDS (India) — Tax Deducted at Source
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)}>
          <Tab label="TDS Sections" />
          <Tab label="TDS Summary" />
          <Tab label="Help" />
        </Tabs>
      </Box>

      <TabPanel value={tab} index={0}>
        <Stack spacing={2}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                New TDS Section
              </Typography>
              <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center" }}>
                <TextField label="Section" size="small" placeholder="194J" value={sectionCode} onChange={(e) => setSectionCode(e.target.value)} sx={{ width: 140 }} />
                <TextField
                  label="Description"
                  size="small"
                  placeholder="Professional / technical fees"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  sx={{ minWidth: 260, flexGrow: 1 }}
                />
                <TextField label="Rate %" type="number" size="small" value={ratePct} onChange={(e) => setRatePct(e.target.value)} sx={{ width: 110 }} />
                <Button variant="contained" onClick={handleCreate} disabled={!sectionCode || !description || !ratePct}>
                  Add section
                </Button>
              </Stack>
            </CardContent>
          </Card>

          <TableContainer component={Card} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Section</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell align="right">Rate</TableCell>
                  <TableCell align="center">Active</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sections.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell>
                      <Chip size="small" label={s.section_code} />
                    </TableCell>
                    <TableCell>{s.description}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                      {s.rate_pct}%
                    </TableCell>
                    <TableCell align="center">
                      <Switch size="small" checked={s.is_active} onChange={() => handleToggleActive(s)} />
                    </TableCell>
                  </TableRow>
                ))}
                {sections.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4}>
                      <Typography variant="body2" color="text.secondary">
                        No TDS sections yet.
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
                <Typography variant="body2">
                  Total TDS deducted: <strong>{fmt(report.total_tds)}</strong>
                </Typography>

                <Typography variant="subtitle2">By section</Typography>
                <TableContainer component={Card} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Section</TableCell>
                        <TableCell>Description</TableCell>
                        <TableCell align="right">Rate</TableCell>
                        <TableCell align="right">Gross Amount</TableCell>
                        <TableCell align="right">TDS Deducted</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {report.section_rows.map((row) => (
                        <TableRow key={row.tds_section_id}>
                          <TableCell>{row.section_code}</TableCell>
                          <TableCell>{row.description}</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                            {row.rate_pct}%
                          </TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                            {fmt(row.gross_amount)}
                          </TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>
                            {fmt(row.tds_amount)}
                          </TableCell>
                        </TableRow>
                      ))}
                      {report.section_rows.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={5}>
                            <Typography variant="body2" color="text.secondary">
                              No TDS deductions in this period.
                            </Typography>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>

                <Typography variant="subtitle2">By deductee (vendor)</Typography>
                <TableContainer component={Card} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Vendor</TableCell>
                        <TableCell align="right">Gross Amount</TableCell>
                        <TableCell align="right">TDS Deducted</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {report.deductee_rows.map((row) => (
                        <TableRow key={row.vendor_id}>
                          <TableCell>{row.vendor_name}</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                            {fmt(row.gross_amount)}
                          </TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>
                            {fmt(row.tds_amount)}
                          </TableCell>
                        </TableRow>
                      ))}
                      {report.deductee_rows.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={3}>
                            <Typography variant="body2" color="text.secondary">
                              No TDS deductions in this period.
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
      </TabPanel>

      <TabPanel value={tab} index={2}>
        <Stack spacing={2}>
          <Typography variant="body2">
            Non-salary TDS under the Income Tax Act — 194C (contractors), 194J (professional/technical fees), 194H
            (commission), 194I (rent), 194Q (purchases), and similar sections. Set up the sections you actually
            deduct under on the TDS Sections tab, then pick one when creating a{" "}
            <Link to="/receivables-payables" style={{ color: "inherit" }}>
              vendor bill
            </Link>{" "}
            — the deduction is split off automatically into whichever G/L account is tagged <code>tds_payable</code>{" "}
            on the Chart of Accounts, and the vendor's payable is reduced accordingly.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Salary TDS (Section 192) works differently — it's slab-based per employee, calculated automatically each
            payroll run, not a flat rate here. See the{" "}
            <Link to="/payroll" style={{ color: "inherit" }}>
              Payroll
            </Link>{" "}
            page.
          </Typography>
          <Typography variant="subtitle2">TDS Summary</Typography>
          <Typography variant="body2" color="text.secondary">
            Section-wise and deductee-wise totals for the period — the data behind Form 26Q.
          </Typography>
        </Stack>
      </TabPanel>
    </Stack>
  );
}
