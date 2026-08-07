import { useEffect, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  IconButton,
  MenuItem,
  Stack,
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
import UploadFileIcon from "@mui/icons-material/UploadFile";
import LinkIcon from "@mui/icons-material/Link";
import LinkOffIcon from "@mui/icons-material/LinkOff";
import DeleteIcon from "@mui/icons-material/Delete";
import { TabPanel } from "../components/TabPanel";
import { useCompany } from "../context/CompanyContext";
import { listGLAccounts } from "../api/budgets";
import {
  deleteBankStatementLine,
  getReconciliationSummary,
  listBankStatementLines,
  listUnmatchedGLLines,
  matchBankStatementLine,
  unmatchBankStatementLine,
  uploadBankStatement,
} from "../api/bankReconciliation";
import type { BankStatementLine, GLAccount, ReconciliationSummary, UnmatchedGLLine } from "../api/types";

function todayValue() {
  return new Date().toISOString().slice(0, 10);
}

const fmt = (v: number) => v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function BankReconciliationPage() {
  const { company } = useCompany();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [tab, setTab] = useState(0);
  const [glAccounts, setGlAccounts] = useState<GLAccount[]>([]);
  const [cashAccount, setCashAccount] = useState("");
  const [lines, setLines] = useState<BankStatementLine[]>([]);
  const [unmatchedGL, setUnmatchedGL] = useState<UnmatchedGLLine[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  const [manageLineId, setManageLineId] = useState<string | null>(null);
  const [manageActualId, setManageActualId] = useState("");

  const [asOf, setAsOf] = useState(todayValue());
  const [bankEndingBalance, setBankEndingBalance] = useState("");
  const [summary, setSummary] = useState<ReconciliationSummary | null>(null);

  const loadAccounts = async () => {
    if (!company) return;
    try {
      setGlAccounts(await listGLAccounts(company.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load G/L accounts");
    }
  };

  useEffect(() => {
    loadAccounts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);

  const loadLines = async () => {
    if (!company || !cashAccount) {
      setLines([]);
      setUnmatchedGL([]);
      return;
    }
    setError(null);
    try {
      const [statementLines, glLines] = await Promise.all([
        listBankStatementLines(company.id, cashAccount),
        listUnmatchedGLLines(company.id, cashAccount),
      ]);
      setLines(statementLines);
      setUnmatchedGL(glLines);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load bank statement lines");
    }
  };

  useEffect(() => {
    loadLines();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id, cashAccount]);

  const handleUpload = async (file: File) => {
    if (!company || !cashAccount) return;
    setError(null);
    setUploadMessage(null);
    try {
      const result = await uploadBankStatement(company.id, cashAccount, file);
      setUploadMessage(`Imported ${result.rows_imported} line(s), ${result.auto_matched} auto-matched.`);
      await loadLines();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  };

  const openMatch = (lineId: string) => {
    setManageLineId(lineId);
    setManageActualId("");
  };

  const handleConfirmMatch = async () => {
    if (!company || !manageLineId || !manageActualId) return;
    setError(null);
    try {
      await matchBankStatementLine(company.id, manageLineId, manageActualId);
      setManageLineId(null);
      setManageActualId("");
      await loadLines();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to match the line");
    }
  };

  const handleUnmatch = async (lineId: string) => {
    if (!company) return;
    setError(null);
    try {
      await unmatchBankStatementLine(company.id, lineId);
      await loadLines();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to unmatch the line");
    }
  };

  const handleDelete = async (lineId: string) => {
    if (!company) return;
    setError(null);
    try {
      await deleteBankStatementLine(company.id, lineId);
      await loadLines();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete the line");
    }
  };

  const handleRunSummary = async () => {
    if (!company || !cashAccount || !bankEndingBalance) return;
    setError(null);
    try {
      setSummary(await getReconciliationSummary(company.id, cashAccount, asOf, Number(bankEndingBalance)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load the reconciliation summary");
    }
  };

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Bank Reconciliation
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)}>
          <Tab label="Import & Match" />
          <Tab label="Reconciliation Summary" />
          <Tab label="Help" />
        </Tabs>
      </Box>

      <TabPanel value={tab} index={0}>
        <Stack spacing={2}>
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap" }}>
                <TextField select label="Cash account" size="small" value={cashAccount} onChange={(e) => setCashAccount(e.target.value)} sx={{ minWidth: 220 }}>
                  {glAccounts.filter((g) => g.category === "asset").map((g) => (
                    <MenuItem key={g.id} value={g.id}>
                      {g.code} {g.name}
                    </MenuItem>
                  ))}
                </TextField>
                <Button variant="outlined" startIcon={<UploadFileIcon />} onClick={() => fileInputRef.current?.click()} disabled={!cashAccount}>
                  Upload statement
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  hidden
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleUpload(file);
                    e.target.value = "";
                  }}
                />
                <Typography variant="caption" color="text.secondary">
                  Columns: date, description, amount (positive = money in, negative = money out), reference (optional)
                </Typography>
              </Stack>
              {uploadMessage && (
                <Alert severity="success" sx={{ mt: 2 }}>
                  {uploadMessage}
                </Alert>
              )}
            </CardContent>
          </Card>

          {cashAccount && (
            <TableContainer component={Card} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell align="right">Amount</TableCell>
                    <TableCell>Reference</TableCell>
                    <TableCell>Match</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {lines.map((line) => (
                    <TableRow key={line.id}>
                      <TableCell>{line.statement_date}</TableCell>
                      <TableCell>{line.description}</TableCell>
                      <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(line.amount)}</TableCell>
                      <TableCell>{line.reference ?? "—"}</TableCell>
                      <TableCell>
                        {line.matched_actual_line_id ? (
                          <Chip size="small" label={line.match_type ?? "matched"} color={line.match_type === "auto" ? "success" : "info"} />
                        ) : (
                          <Chip size="small" label="unmatched" color="warning" />
                        )}
                      </TableCell>
                      <TableCell align="right">
                        {line.matched_actual_line_id ? (
                          <IconButton size="small" onClick={() => handleUnmatch(line.id)} aria-label="Unmatch">
                            <LinkOffIcon fontSize="small" />
                          </IconButton>
                        ) : (
                          <>
                            <IconButton size="small" onClick={() => openMatch(line.id)} aria-label="Match">
                              <LinkIcon fontSize="small" />
                            </IconButton>
                            <IconButton size="small" onClick={() => handleDelete(line.id)} aria-label="Delete">
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                  {lines.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6}>
                        <Typography variant="body2" color="text.secondary">
                          No bank statement lines imported for this account yet.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          {manageLineId && (
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle1" gutterBottom>
                  Match to a G/L transaction
                </Typography>
                <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap" }}>
                  <TextField select label="Unmatched G/L line" size="small" value={manageActualId} onChange={(e) => setManageActualId(e.target.value)} sx={{ minWidth: 320 }}>
                    {unmatchedGL.map((g) => (
                      <MenuItem key={g.actual_line_id} value={g.actual_line_id}>
                        {g.effective_date} — {fmt(g.amount)} — {g.description ?? "no description"}
                      </MenuItem>
                    ))}
                  </TextField>
                  <Button variant="contained" onClick={handleConfirmMatch} disabled={!manageActualId}>
                    Confirm match
                  </Button>
                  <Button variant="text" onClick={() => setManageLineId(null)}>
                    Cancel
                  </Button>
                </Stack>
              </CardContent>
            </Card>
          )}
        </Stack>
      </TabPanel>

      <TabPanel value={tab} index={1}>
        {cashAccount ? (
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Reconciliation Summary
              </Typography>
              <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap" }}>
                <TextField label="As of" type="date" size="small" value={asOf} onChange={(e) => setAsOf(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
                <TextField
                  label="Bank statement ending balance"
                  type="number"
                  size="small"
                  value={bankEndingBalance}
                  onChange={(e) => setBankEndingBalance(e.target.value)}
                  sx={{ minWidth: 220 }}
                />
                <Button variant="contained" onClick={handleRunSummary} disabled={!bankEndingBalance}>
                  Reconcile
                </Button>
              </Stack>
              {summary && (
                <TableContainer sx={{ mt: 2 }}>
                  <Table size="small">
                    <TableBody>
                      <TableRow>
                        <TableCell>Balance per books</TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(summary.book_balance)}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>+ Bank-only items not yet in books</TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(summary.unmatched_bank_lines_total)}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600 }}>Adjusted book balance</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>{fmt(summary.adjusted_book_balance)}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell sx={{ pt: 2 }}>Balance per bank statement</TableCell>
                        <TableCell align="right" sx={{ pt: 2, fontVariantNumeric: "tabular-nums" }}>{fmt(summary.bank_statement_ending_balance)}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>+ Deposits/checks in transit (in books, not yet on bank statement)</TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(summary.unmatched_gl_lines_total)}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600 }}>Adjusted bank balance</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>{fmt(summary.adjusted_bank_balance)}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell colSpan={2} sx={{ pt: 2 }}>
                          <Chip
                            label={summary.is_reconciled ? "Reconciled: adjusted balances match" : "Not reconciled -- check unmatched items"}
                            color={summary.is_reconciled ? "success" : "error"}
                          />
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
        ) : (
          <Typography variant="body2" color="text.secondary">
            Pick a cash account on the Import &amp; Match tab first.
          </Typography>
        )}
      </TabPanel>

      <TabPanel value={tab} index={2}>
        <Stack spacing={2}>
          <Typography variant="body2">
            Upload a bank statement and it's matched automatically against what's already posted to this cash
            account — only when exactly one candidate has the same amount within a few days of the transaction
            date. Anything ambiguous or missing is left for you to match by hand, or points at a transaction (a
            bank fee, interest) that still needs a real posting on the Bookkeeping page.
          </Typography>
          <Typography variant="subtitle2">Reconciliation Summary</Typography>
          <Typography variant="body2" color="text.secondary">
            Adjusts both the book balance (adding bank-only items like fees not yet posted) and the bank balance
            (adding deposits/checks in transit) so they should land on the same adjusted number — that equality is
            what "reconciled" means.
          </Typography>
        </Stack>
      </TabPanel>
    </Stack>
  );
}
