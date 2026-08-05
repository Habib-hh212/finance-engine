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
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import PublishIcon from "@mui/icons-material/Publish";
import UndoIcon from "@mui/icons-material/Undo";
import { useCompany } from "../context/CompanyContext";
import {
  createJournalEntry,
  deleteJournalEntry,
  getTrialBalance,
  listJournalEntries,
  postJournalEntry,
  reverseJournalEntry,
  type JournalEntryLineInput,
} from "../api/bookkeeping";
import { listCostCenters, listGLAccounts } from "../api/budgets";
import type { CostCenter, GLAccount, JournalEntry, TrialBalance } from "../api/types";

function todayValue() {
  return new Date().toISOString().slice(0, 10);
}

const fmt = (v: number) => v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const STATUS_COLOR: Record<string, "default" | "info" | "success" | "warning"> = {
  draft: "default",
  posted: "success",
  reversed: "warning",
};

interface DraftLine {
  key: number;
  gl_account_id: string;
  debit_amount: string;
  credit_amount: string;
  cost_center_id: string;
  description: string;
}

let lineKeySeq = 0;
const blankLine = (): DraftLine => ({
  key: lineKeySeq++,
  gl_account_id: "",
  debit_amount: "",
  credit_amount: "",
  cost_center_id: "",
  description: "",
});

export function BookkeepingPage() {
  const { company } = useCompany();
  const [glAccounts, setGlAccounts] = useState<GLAccount[]>([]);
  const [costCenters, setCostCenters] = useState<CostCenter[]>([]);
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [trialBalance, setTrialBalance] = useState<TrialBalance | null>(null);
  const [asOf, setAsOf] = useState(todayValue());
  const [error, setError] = useState<string | null>(null);

  const [entryDate, setEntryDate] = useState(todayValue());
  const [reference, setReference] = useState("");
  const [description, setDescription] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([blankLine(), blankLine()]);

  const load = async () => {
    if (!company) return;
    setError(null);
    try {
      const [gls, centers, entryList, tb] = await Promise.all([
        listGLAccounts(company.id),
        listCostCenters(company.id),
        listJournalEntries(company.id),
        getTrialBalance(company.id, asOf),
      ]);
      setGlAccounts(gls);
      setCostCenters(centers);
      setEntries(entryList);
      setTrialBalance(tb);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load the general ledger");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id, asOf]);

  const glNameFor = (id: string) => {
    const g = glAccounts.find((a) => a.id === id);
    return g ? `${g.code} ${g.name}` : id;
  };

  const totalDebit = lines.reduce((sum, l) => sum + (Number(l.debit_amount) || 0), 0);
  const totalCredit = lines.reduce((sum, l) => sum + (Number(l.credit_amount) || 0), 0);
  const difference = Math.round((totalDebit - totalCredit) * 100) / 100;
  const isBalanced = Math.abs(difference) < 0.01 && totalDebit > 0;

  const updateLine = (key: number, changes: Partial<DraftLine>) =>
    setLines((prev) => prev.map((l) => (l.key === key ? { ...l, ...changes } : l)));

  const addLine = () => setLines((prev) => [...prev, blankLine()]);
  const removeLine = (key: number) => setLines((prev) => (prev.length > 2 ? prev.filter((l) => l.key !== key) : prev));

  const resetForm = () => {
    setReference("");
    setDescription("");
    setLines([blankLine(), blankLine()]);
  };

  const handleCreateEntry = async () => {
    if (!company) return;
    setError(null);
    const payload: JournalEntryLineInput[] = lines
      .filter((l) => l.gl_account_id && (Number(l.debit_amount) || Number(l.credit_amount)))
      .map((l) => ({
        gl_account_id: l.gl_account_id,
        debit_amount: Number(l.debit_amount) || 0,
        credit_amount: Number(l.credit_amount) || 0,
        cost_center_id: l.cost_center_id || undefined,
        description: l.description || undefined,
      }));
    try {
      await createJournalEntry(company.id, entryDate, payload, reference || undefined, description || undefined, company.base_currency);
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create the journal entry");
    }
  };

  const handlePost = async (id: string) => {
    setError(null);
    try {
      await postJournalEntry(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to post the journal entry");
    }
  };

  const handleReverse = async (id: string) => {
    setError(null);
    try {
      await reverseJournalEntry(id, todayValue());
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reverse the journal entry");
    }
  };

  const handleDelete = async (id: string) => {
    setError(null);
    try {
      await deleteJournalEntry(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete the journal entry");
    }
  };

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        General Ledger
      </Typography>
      <Typography variant="caption" color="text.secondary">
        Real double-entry bookkeeping: every journal entry must balance — total debits equal total credits — before it
        can be posted. A posted entry automatically feeds Financial Statements, Cost Controlling, KPIs, and the
        Dashboard the same way a manual actuals-post already does; nothing else in the app needs to change to pick it
        up. The quick "Post an actual" form on Cost Controlling still works too — this is a more rigorous front door
        alongside it, not a replacement.
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            New Journal Entry
          </Typography>
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center", mb: 2 }}>
            <TextField
              label="Date"
              type="date"
              size="small"
              value={entryDate}
              onChange={(e) => setEntryDate(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField label="Reference" size="small" value={reference} onChange={(e) => setReference(e.target.value)} sx={{ width: 220 }} />
            <TextField
              label="Description (optional)"
              size="small"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              sx={{ minWidth: 260, flexGrow: 1 }}
            />
          </Stack>

          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>GL Account</TableCell>
                <TableCell>Cost Center</TableCell>
                <TableCell align="right">Debit</TableCell>
                <TableCell align="right">Credit</TableCell>
                <TableCell>Description</TableCell>
                <TableCell align="right" />
              </TableRow>
            </TableHead>
            <TableBody>
              {lines.map((line) => (
                <TableRow key={line.key}>
                  <TableCell sx={{ minWidth: 200 }}>
                    <TextField
                      select
                      size="small"
                      fullWidth
                      value={line.gl_account_id}
                      onChange={(e) => updateLine(line.key, { gl_account_id: e.target.value })}
                    >
                      {glAccounts.map((g) => (
                        <MenuItem key={g.id} value={g.id}>
                          {g.code} {g.name}
                        </MenuItem>
                      ))}
                    </TextField>
                  </TableCell>
                  <TableCell sx={{ minWidth: 160 }}>
                    <TextField
                      select
                      size="small"
                      fullWidth
                      value={line.cost_center_id}
                      onChange={(e) => updateLine(line.key, { cost_center_id: e.target.value })}
                    >
                      <MenuItem value="">— none —</MenuItem>
                      {costCenters.map((c) => (
                        <MenuItem key={c.id} value={c.id}>
                          {c.code} {c.name}
                        </MenuItem>
                      ))}
                    </TextField>
                  </TableCell>
                  <TableCell align="right" sx={{ width: 130 }}>
                    <TextField
                      type="number"
                      size="small"
                      value={line.debit_amount}
                      onChange={(e) => updateLine(line.key, { debit_amount: e.target.value, credit_amount: "" })}
                      sx={{ width: 120 }}
                    />
                  </TableCell>
                  <TableCell align="right" sx={{ width: 130 }}>
                    <TextField
                      type="number"
                      size="small"
                      value={line.credit_amount}
                      onChange={(e) => updateLine(line.key, { credit_amount: e.target.value, debit_amount: "" })}
                      sx={{ width: 120 }}
                    />
                  </TableCell>
                  <TableCell sx={{ minWidth: 160 }}>
                    <TextField
                      size="small"
                      fullWidth
                      value={line.description}
                      onChange={(e) => updateLine(line.key, { description: e.target.value })}
                    />
                  </TableCell>
                  <TableCell align="right">
                    <IconButton size="small" onClick={() => removeLine(line.key)} disabled={lines.length <= 2} aria-label="Remove line">
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <Stack direction="row" spacing={2} sx={{ alignItems: "center", mt: 2, flexWrap: "wrap" }}>
            <Button size="small" startIcon={<AddIcon />} onClick={addLine}>
              Add line
            </Button>
            <Typography variant="body2" sx={{ ml: "auto" }}>
              Total Debit: <strong>{fmt(totalDebit)}</strong> &nbsp;&nbsp; Total Credit: <strong>{fmt(totalCredit)}</strong>
            </Typography>
            <Chip
              size="small"
              label={isBalanced ? "Balanced" : `Off by ${fmt(Math.abs(difference))}`}
              color={isBalanced ? "success" : "warning"}
            />
            <Button variant="contained" onClick={handleCreateEntry} disabled={!isBalanced}>
              Save as draft
            </Button>
          </Stack>
        </CardContent>
      </Card>

      <Typography variant="h6">Journal Entries</Typography>
      <TableContainer component={Card} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell>Reference</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Lines</TableCell>
              <TableCell align="right">Amount</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {entries.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell>{entry.entry_date}</TableCell>
                <TableCell>{entry.reference ?? "—"}</TableCell>
                <TableCell>
                  <Chip size="small" label={entry.status} color={STATUS_COLOR[entry.status]} />
                </TableCell>
                <TableCell>
                  {entry.lines.map((l) => (
                    <Typography key={l.id} variant="caption" sx={{ display: "block" }}>
                      {glNameFor(l.gl_account_id)}: {l.debit_amount ? `Dr ${fmt(l.debit_amount)}` : `Cr ${fmt(l.credit_amount)}`}
                    </Typography>
                  ))}
                </TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                  {fmt(entry.lines.reduce((sum, l) => sum + l.debit_amount, 0))} {entry.currency}
                </TableCell>
                <TableCell align="right">
                  {entry.status === "draft" && (
                    <>
                      <IconButton size="small" onClick={() => handlePost(entry.id)} aria-label="Post entry">
                        <PublishIcon fontSize="small" />
                      </IconButton>
                      <IconButton size="small" onClick={() => handleDelete(entry.id)} aria-label="Delete entry">
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </>
                  )}
                  {entry.status === "posted" && (
                    <IconButton size="small" onClick={() => handleReverse(entry.id)} aria-label="Reverse entry">
                      <UndoIcon fontSize="small" />
                    </IconButton>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {entries.length === 0 && (
              <TableRow>
                <TableCell colSpan={6}>
                  <Typography variant="body2" color="text.secondary">
                    No journal entries yet.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap" }}>
        <Typography variant="h6">Trial Balance</Typography>
        <TextField
          label="As of"
          type="date"
          size="small"
          value={asOf}
          onChange={(e) => setAsOf(e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
        />
      </Stack>
      <Typography variant="caption" color="text.secondary">
        Only entries that have been posted count here — draft entries are excluded. Total Debit across every account
        should equal Total Credit; that equality is the actual proof the books balance, not an assumption.
      </Typography>
      {trialBalance && (
        <>
          <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
            <Typography variant="body2">
              Total Debit: <strong>{fmt(trialBalance.total_debit)}</strong> &nbsp;&nbsp; Total Credit:{" "}
              <strong>{fmt(trialBalance.total_credit)}</strong>
            </Typography>
            <Chip
              size="small"
              label={trialBalance.is_balanced ? "Balanced" : "Not balanced"}
              color={trialBalance.is_balanced ? "success" : "error"}
            />
          </Stack>
          <TableContainer component={Card} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>GL Account</TableCell>
                  <TableCell>Category</TableCell>
                  <TableCell align="right">Total Debit</TableCell>
                  <TableCell align="right">Total Credit</TableCell>
                  <TableCell align="right">Net Balance</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {trialBalance.rows.map((row) => (
                  <TableRow key={row.gl_account_id}>
                    <TableCell>
                      {row.gl_account_code} {row.gl_account_name}
                    </TableCell>
                    <TableCell>{row.category}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.total_debit)}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.total_credit)}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>
                      {fmt(row.net_balance)}
                    </TableCell>
                  </TableRow>
                ))}
                {trialBalance.rows.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <Typography variant="body2" color="text.secondary">
                        No posted journal entries on or before this date.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}
    </Stack>
  );
}
