import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
  IconButton,
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
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import UndoIcon from "@mui/icons-material/Undo";
import DownloadIcon from "@mui/icons-material/Download";
import { useCompany } from "../context/CompanyContext";
import { listGLAccounts } from "../api/budgets";
import { closeFiscalYear, createAccrual, getPeriodCloseStatus, listAccruals, reverseAccrual } from "../api/periodClose";
import { downloadAllBooks } from "../api/financialStatements";
import type { Accrual, GLAccount, PeriodCloseStatus, YearEndCloseResult } from "../api/types";

function todayValue() {
  return new Date().toISOString().slice(0, 10);
}

const fmt = (v: number) => v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function CheckRow({ ok, label, detail }: { ok: boolean; label: string; detail?: string }) {
  return (
    <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
      {ok ? <CheckCircleIcon fontSize="small" color="success" /> : <CancelIcon fontSize="small" color="error" />}
      <Typography variant="body2">{label}</Typography>
      {detail && (
        <Typography variant="caption" color="text.secondary">
          {detail}
        </Typography>
      )}
    </Stack>
  );
}

export function PeriodClosePage() {
  const { company } = useCompany();
  const [glAccounts, setGlAccounts] = useState<GLAccount[]>([]);
  const [accruals, setAccruals] = useState<Accrual[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Accrual form
  const [entryDate, setEntryDate] = useState(todayValue());
  const [debitAccount, setDebitAccount] = useState("");
  const [creditAccount, setCreditAccount] = useState("");
  const [amount, setAmount] = useState("");
  const [reversalDate, setReversalDate] = useState(todayValue());
  const [reference, setReference] = useState("");

  // Cockpit
  const [cockpitPeriod, setCockpitPeriod] = useState(todayValue().slice(0, 7) + "-01");
  const [status, setStatus] = useState<PeriodCloseStatus | null>(null);

  // Year-end close
  const [yearStart, setYearStart] = useState(`${new Date().getFullYear()}-01-01`);
  const [yearEnd, setYearEnd] = useState(`${new Date().getFullYear()}-12-31`);
  const [retainedEarningsAccount, setRetainedEarningsAccount] = useState("");
  const [closeResult, setCloseResult] = useState<YearEndCloseResult | null>(null);
  const [closeError, setCloseError] = useState<string | null>(null);

  const load = async () => {
    if (!company) return;
    setError(null);
    try {
      const [accounts, accrualList] = await Promise.all([listGLAccounts(company.id), listAccruals(company.id)]);
      setGlAccounts(accounts);
      setAccruals(accrualList);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load period-close data");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);

  const loadStatus = async () => {
    if (!company) return;
    try {
      setStatus(await getPeriodCloseStatus(company.id, cockpitPeriod));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load period-close status");
    }
  };

  useEffect(() => {
    loadStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id, cockpitPeriod, accruals]);

  const handleCreateAccrual = async () => {
    if (!company || !debitAccount || !creditAccount || !amount) return;
    setError(null);
    try {
      await createAccrual(company.id, entryDate, debitAccount, creditAccount, Number(amount), reversalDate, reference || undefined);
      setDebitAccount("");
      setCreditAccount("");
      setAmount("");
      setReference("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create the accrual");
    }
  };

  const handleReverse = async (id: string) => {
    if (!company) return;
    setError(null);
    try {
      await reverseAccrual(company.id, id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reverse the accrual");
    }
  };

  const handleCloseYear = async () => {
    if (!company || !retainedEarningsAccount) return;
    setCloseError(null);
    setCloseResult(null);
    try {
      setCloseResult(await closeFiscalYear(company.id, yearStart, yearEnd, retainedEarningsAccount));
      await loadStatus();
    } catch (err) {
      setCloseError(err instanceof Error ? err.message : "Failed to close the fiscal year");
    }
  };

  const glLabel = (id: string) => {
    const g = glAccounts.find((a) => a.id === id);
    return g ? `${g.code} ${g.name}` : id;
  };

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Period Close
      </Typography>
      <Typography variant="caption" color="text.secondary">
        Accrue an expense or revenue now and schedule its reversal, check whether a month is ready to close, and run the
        year-end close that zeroes revenue and expense into retained earnings. Balance sheet accounts need no separate
        "carry forward" step -- the ledger already sums a company's entire posted history, so they carry forward
        automatically.
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            New Accrual
          </Typography>
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center" }}>
            <TextField label="Entry date" type="date" size="small" value={entryDate} onChange={(e) => setEntryDate(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
            <TextField select label="Debit account" size="small" value={debitAccount} onChange={(e) => setDebitAccount(e.target.value)} sx={{ minWidth: 180 }}>
              {glAccounts.map((g) => (
                <MenuItem key={g.id} value={g.id}>
                  {g.code} {g.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField select label="Credit account" size="small" value={creditAccount} onChange={(e) => setCreditAccount(e.target.value)} sx={{ minWidth: 180 }}>
              {glAccounts.map((g) => (
                <MenuItem key={g.id} value={g.id}>
                  {g.code} {g.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Amount" type="number" size="small" value={amount} onChange={(e) => setAmount(e.target.value)} sx={{ width: 130 }} />
            <TextField
              label="Reversal date"
              type="date"
              size="small"
              value={reversalDate}
              onChange={(e) => setReversalDate(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField label="Reference" size="small" value={reference} onChange={(e) => setReference(e.target.value)} sx={{ minWidth: 180 }} />
            <Button variant="contained" onClick={handleCreateAccrual} disabled={!debitAccount || !creditAccount || !amount}>
              Post accrual
            </Button>
          </Stack>

          <TableContainer sx={{ mt: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell>Reference</TableCell>
                  <TableCell>Debit</TableCell>
                  <TableCell>Credit</TableCell>
                  <TableCell align="right">Amount</TableCell>
                  <TableCell>Reversal Date</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {accruals.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell>{a.entry_date}</TableCell>
                    <TableCell>{a.reference ?? "—"}</TableCell>
                    <TableCell>{a.debit_gl_account_code}</TableCell>
                    <TableCell>{a.credit_gl_account_code}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(a.amount)}</TableCell>
                    <TableCell>{a.reversal_date}</TableCell>
                    <TableCell>
                      {a.reversed ? (
                        <Chip size="small" label="reversed" color="default" />
                      ) : a.due_for_reversal ? (
                        <Chip size="small" label="due" color="warning" />
                      ) : (
                        <Chip size="small" label="open" color="info" />
                      )}
                    </TableCell>
                    <TableCell align="right">
                      {!a.reversed && (
                        <IconButton size="small" onClick={() => handleReverse(a.id)} aria-label="Reverse accrual">
                          <UndoIcon fontSize="small" />
                        </IconButton>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                {accruals.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={8}>
                      <Typography variant="body2" color="text.secondary">
                        No accruals yet.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", mb: 2 }}>
            <Typography variant="subtitle1">Month-End Cockpit</Typography>
            <TextField
              label="Period"
              type="date"
              size="small"
              value={cockpitPeriod}
              onChange={(e) => setCockpitPeriod(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
            />
          </Stack>
          {status && (
            <Stack spacing={1}>
              <CheckRow ok={status.trial_balance_is_balanced} label="Trial balance is balanced" />
              <CheckRow ok={status.draft_entries_count === 0} label="No draft journal entries pending" detail={status.draft_entries_count > 0 ? `${status.draft_entries_count} draft(s)` : undefined} />
              <CheckRow ok={status.depreciation_run_done} label="Depreciation run for this period" />
              <CheckRow
                ok={status.assets_missing_depreciation.length === 0}
                label="No active assets missing this period's depreciation"
                detail={status.assets_missing_depreciation.length > 0 ? status.assets_missing_depreciation.map((g) => g.code).join(", ") : undefined}
              />
              <CheckRow ok={status.accruals_due_for_reversal === 0} label="No accruals overdue for reversal" detail={status.accruals_due_for_reversal > 0 ? `${status.accruals_due_for_reversal} due` : undefined} />
              <Chip
                sx={{ alignSelf: "flex-start", mt: 1 }}
                label={status.ready_to_close ? "Ready to close" : "Not ready to close"}
                color={status.ready_to_close ? "success" : "warning"}
              />
            </Stack>
          )}
          <Button
            size="small"
            variant="outlined"
            startIcon={<DownloadIcon />}
            sx={{ mt: 2 }}
            onClick={() => downloadAllBooks(company!.id, `${cockpitPeriod.slice(0, 7)}-01`, cockpitPeriod)}
            disabled={!company}
          >
            Download all books for this period
          </Button>
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Year-End Close
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 2 }}>
            Posts one balanced entry zeroing every revenue and expense account's net activity for the range into the
            retained earnings account below. Asset, liability, and equity balances already carry forward automatically.
          </Typography>
          <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap" }}>
            <TextField label="Start" type="date" size="small" value={yearStart} onChange={(e) => setYearStart(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
            <TextField label="End" type="date" size="small" value={yearEnd} onChange={(e) => setYearEnd(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
            <TextField select label="Retained earnings account" size="small" value={retainedEarningsAccount} onChange={(e) => setRetainedEarningsAccount(e.target.value)} sx={{ minWidth: 220 }}>
              {glAccounts
                .filter((g) => g.category === "equity")
                .map((g) => (
                  <MenuItem key={g.id} value={g.id}>
                    {g.code} {g.name}
                  </MenuItem>
                ))}
            </TextField>
            <Button variant="contained" onClick={handleCloseYear} disabled={!retainedEarningsAccount}>
              Close fiscal year
            </Button>
          </Stack>
          {closeError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {closeError}
            </Alert>
          )}
          {closeResult && (
            <Alert severity="success" sx={{ mt: 2 }}>
              Closed. Net income of {fmt(closeResult.net_income)} moved to {glLabel(retainedEarningsAccount)} across {closeResult.lines_closed} line(s).
            </Alert>
          )}
        </CardContent>
      </Card>
    </Stack>
  );
}
