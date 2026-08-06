import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  CardContent,
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
import { useCompany } from "../context/CompanyContext";
import { listGLAccounts } from "../api/budgets";
import { listTaxCodes } from "../api/taxCodes";
import { listTdsSections } from "../api/tds";
import {
  applyCustomerReceipt,
  applyVendorPayment,
  createCustomer,
  createCustomerInvoice,
  createCustomerReceipt,
  createVendor,
  createVendorBill,
  createVendorPayment,
  getApAging,
  getArAging,
  listCustomerInvoices,
  listCustomerReceipts,
  listCustomers,
  listVendorBills,
  listVendorPayments,
  listVendors,
} from "../api/receivablesPayables";
import type {
  AgingReport,
  CustomerInvoice,
  CustomerParty,
  CustomerReceipt,
  GLAccount,
  InvoiceStatus,
  TaxCode,
  TdsSection,
  VendorBill,
  VendorParty,
  VendorPayment,
} from "../api/types";

function todayValue() {
  return new Date().toISOString().slice(0, 10);
}

const fmt = (v: number) => v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const STATUS_COLOR: Record<InvoiceStatus, "default" | "warning" | "success" | "error"> = {
  open: "default",
  partially_paid: "warning",
  paid: "success",
  void: "error",
};

const BUCKET_COLOR: Record<string, "success" | "info" | "warning" | "error"> = {
  current: "success",
  "1-30": "info",
  "31-60": "warning",
  "61-90": "warning",
  "90+": "error",
};

export function ReceivablesPayablesPage() {
  const { company } = useCompany();
  const [glAccounts, setGlAccounts] = useState<GLAccount[]>([]);
  const [taxCodes, setTaxCodes] = useState<TaxCode[]>([]);
  const [tdsSections, setTdsSections] = useState<TdsSection[]>([]);
  const [customers, setCustomers] = useState<CustomerParty[]>([]);
  const [vendors, setVendors] = useState<VendorParty[]>([]);
  const [invoices, setInvoices] = useState<CustomerInvoice[]>([]);
  const [receipts, setReceipts] = useState<CustomerReceipt[]>([]);
  const [bills, setBills] = useState<VendorBill[]>([]);
  const [payments, setPayments] = useState<VendorPayment[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Quick-add party
  const [newCustomerName, setNewCustomerName] = useState("");
  const [newVendorName, setNewVendorName] = useState("");

  // New invoice
  const [invCustomer, setInvCustomer] = useState("");
  const [invNumber, setInvNumber] = useState("");
  const [invDate, setInvDate] = useState(todayValue());
  const [invDueDate, setInvDueDate] = useState(todayValue());
  const [invRevenueAccount, setInvRevenueAccount] = useState("");
  const [invAmount, setInvAmount] = useState("");
  const [invTaxCode, setInvTaxCode] = useState("");

  // New receipt
  const [rcCustomer, setRcCustomer] = useState("");
  const [rcDate, setRcDate] = useState(todayValue());
  const [rcCashAccount, setRcCashAccount] = useState("");
  const [rcAmount, setRcAmount] = useState("");
  const [rcReference, setRcReference] = useState("");

  // Apply receipt
  const [applyReceiptId, setApplyReceiptId] = useState("");
  const [applyInvoiceId, setApplyInvoiceId] = useState("");
  const [applyReceiptAmount, setApplyReceiptAmount] = useState("");

  // New bill
  const [billVendor, setBillVendor] = useState("");
  const [billNumber, setBillNumber] = useState("");
  const [billDate, setBillDate] = useState(todayValue());
  const [billDueDate, setBillDueDate] = useState(todayValue());
  const [billExpenseAccount, setBillExpenseAccount] = useState("");
  const [billAmount, setBillAmount] = useState("");
  const [billTaxCode, setBillTaxCode] = useState("");
  const [billTdsSection, setBillTdsSection] = useState("");

  // New payment
  const [pmVendor, setPmVendor] = useState("");
  const [pmDate, setPmDate] = useState(todayValue());
  const [pmCashAccount, setPmCashAccount] = useState("");
  const [pmAmount, setPmAmount] = useState("");
  const [pmReference, setPmReference] = useState("");

  // Apply payment
  const [applyPaymentId, setApplyPaymentId] = useState("");
  const [applyBillId, setApplyBillId] = useState("");
  const [applyPaymentAmount, setApplyPaymentAmount] = useState("");

  // Aging
  const [arAsOf, setArAsOf] = useState(todayValue());
  const [apAsOf, setApAsOf] = useState(todayValue());
  const [arAging, setArAging] = useState<AgingReport | null>(null);
  const [apAging, setApAging] = useState<AgingReport | null>(null);

  const load = async () => {
    if (!company) return;
    setError(null);
    try {
      const [accounts, codes, sections, cust, vend, inv, rcpt, bl, pay] = await Promise.all([
        listGLAccounts(company.id),
        listTaxCodes(company.id),
        listTdsSections(company.id),
        listCustomers(company.id),
        listVendors(company.id),
        listCustomerInvoices(company.id),
        listCustomerReceipts(company.id),
        listVendorBills(company.id),
        listVendorPayments(company.id),
      ]);
      setGlAccounts(accounts);
      setTaxCodes(codes);
      setTdsSections(sections);
      setCustomers(cust);
      setVendors(vend);
      setInvoices(inv);
      setReceipts(rcpt);
      setBills(bl);
      setPayments(pay);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load receivables/payables");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);

  const loadAging = async () => {
    if (!company) return;
    try {
      const [ar, ap] = await Promise.all([getArAging(company.id, arAsOf), getApAging(company.id, apAsOf)]);
      setArAging(ar);
      setApAging(ap);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load aging reports");
    }
  };

  useEffect(() => {
    loadAging();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id, arAsOf, apAsOf, invoices, bills]);

  const handleAddCustomer = async () => {
    if (!company || !newCustomerName) return;
    setError(null);
    try {
      await createCustomer(company.id, newCustomerName);
      setNewCustomerName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add customer");
    }
  };

  const handleAddVendor = async () => {
    if (!company || !newVendorName) return;
    setError(null);
    try {
      await createVendor(company.id, newVendorName);
      setNewVendorName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add vendor");
    }
  };

  const handleCreateInvoice = async () => {
    if (!company || !invCustomer || !invNumber || !invRevenueAccount || !invAmount) return;
    setError(null);
    try {
      await createCustomerInvoice(company.id, {
        customer_id: invCustomer,
        invoice_number: invNumber,
        invoice_date: invDate,
        due_date: invDueDate,
        revenue_gl_account_id: invRevenueAccount,
        net_amount: Number(invAmount),
        tax_code_id: invTaxCode || undefined,
      });
      setInvNumber("");
      setInvAmount("");
      setInvTaxCode("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create the invoice");
    }
  };

  const handleCreateReceipt = async () => {
    if (!company || !rcCustomer || !rcCashAccount || !rcAmount) return;
    setError(null);
    try {
      await createCustomerReceipt(company.id, rcCustomer, rcDate, rcCashAccount, Number(rcAmount), rcReference || undefined);
      setRcAmount("");
      setRcReference("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to record the receipt");
    }
  };

  const handleApplyReceipt = async () => {
    if (!company || !applyReceiptId || !applyInvoiceId || !applyReceiptAmount) return;
    setError(null);
    try {
      await applyCustomerReceipt(company.id, applyReceiptId, applyInvoiceId, Number(applyReceiptAmount), todayValue());
      setApplyReceiptId("");
      setApplyInvoiceId("");
      setApplyReceiptAmount("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to apply the receipt");
    }
  };

  const handleCreateBill = async () => {
    if (!company || !billVendor || !billNumber || !billExpenseAccount || !billAmount) return;
    setError(null);
    try {
      await createVendorBill(company.id, {
        vendor_id: billVendor,
        bill_number: billNumber,
        bill_date: billDate,
        due_date: billDueDate,
        expense_gl_account_id: billExpenseAccount,
        net_amount: Number(billAmount),
        tax_code_id: billTaxCode || undefined,
        tds_section_id: billTdsSection || undefined,
      });
      setBillNumber("");
      setBillAmount("");
      setBillTaxCode("");
      setBillTdsSection("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create the bill");
    }
  };

  const handleCreatePayment = async () => {
    if (!company || !pmVendor || !pmCashAccount || !pmAmount) return;
    setError(null);
    try {
      await createVendorPayment(company.id, pmVendor, pmDate, pmCashAccount, Number(pmAmount), pmReference || undefined);
      setPmAmount("");
      setPmReference("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to record the payment");
    }
  };

  const handleApplyPayment = async () => {
    if (!company || !applyPaymentId || !applyBillId || !applyPaymentAmount) return;
    setError(null);
    try {
      await applyVendorPayment(company.id, applyPaymentId, applyBillId, Number(applyPaymentAmount), todayValue());
      setApplyPaymentId("");
      setApplyBillId("");
      setApplyPaymentAmount("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to apply the payment");
    }
  };

  const openInvoices = invoices.filter((i) => i.status === "open" || i.status === "partially_paid");
  const unappliedReceipts = receipts.filter((r) => r.unapplied_balance > 0);
  const openBills = bills.filter((b) => b.status === "open" || b.status === "partially_paid");
  const unappliedPayments = payments.filter((p) => p.unapplied_balance > 0);

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Receivables &amp; Payables
      </Typography>
      <Typography variant="caption" color="text.secondary">
        Every invoice, bill, receipt, and payment posts a real journal entry through the General Ledger. A receipt or
        payment not yet linked to anything is a down payment -- an unapplied balance on the AR/AP control account --
        apply it to an invoice or bill whenever one shows up, no separate posting needed.
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Card variant="outlined">
        <CardContent>
          <Stack direction="row" spacing={4} sx={{ flexWrap: "wrap" }}>
            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
              <TextField label="New customer" size="small" value={newCustomerName} onChange={(e) => setNewCustomerName(e.target.value)} />
              <Button size="small" variant="outlined" onClick={handleAddCustomer} disabled={!newCustomerName}>
                Add
              </Button>
            </Stack>
            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
              <TextField label="New vendor" size="small" value={newVendorName} onChange={(e) => setNewVendorName(e.target.value)} />
              <Button size="small" variant="outlined" onClick={handleAddVendor} disabled={!newVendorName}>
                Add
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      <Typography variant="h6">Accounts Receivable</Typography>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            New Invoice
          </Typography>
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center" }}>
            <TextField select label="Customer" size="small" value={invCustomer} onChange={(e) => setInvCustomer(e.target.value)} sx={{ minWidth: 170 }}>
              {customers.map((c) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Invoice #" size="small" value={invNumber} onChange={(e) => setInvNumber(e.target.value)} sx={{ width: 130 }} />
            <TextField label="Date" type="date" size="small" value={invDate} onChange={(e) => setInvDate(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
            <TextField label="Due date" type="date" size="small" value={invDueDate} onChange={(e) => setInvDueDate(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
            <TextField select label="Revenue account" size="small" value={invRevenueAccount} onChange={(e) => setInvRevenueAccount(e.target.value)} sx={{ minWidth: 170 }}>
              {glAccounts.map((g) => (
                <MenuItem key={g.id} value={g.id}>
                  {g.code} {g.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Net amount" type="number" size="small" value={invAmount} onChange={(e) => setInvAmount(e.target.value)} sx={{ width: 130 }} />
            <TextField select label="Tax code" size="small" value={invTaxCode} onChange={(e) => setInvTaxCode(e.target.value)} sx={{ minWidth: 160 }}>
              <MenuItem value="">— none —</MenuItem>
              {taxCodes.filter((t) => t.is_active).map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.code} ({t.rate_pct}%)
                </MenuItem>
              ))}
            </TextField>
            <Button variant="contained" onClick={handleCreateInvoice} disabled={!invCustomer || !invNumber || !invRevenueAccount || !invAmount}>
              Create invoice
            </Button>
          </Stack>

          <TableContainer sx={{ mt: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Number</TableCell>
                  <TableCell>Customer</TableCell>
                  <TableCell>Due</TableCell>
                  <TableCell align="right">Amount</TableCell>
                  <TableCell align="right">Remaining</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {invoices.map((i) => (
                  <TableRow key={i.id}>
                    <TableCell>{i.invoice_number}</TableCell>
                    <TableCell>{i.customer_name}</TableCell>
                    <TableCell>{i.due_date}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(i.amount)}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(i.remaining_balance)}</TableCell>
                    <TableCell>
                      <Chip size="small" label={i.status.replace("_", " ")} color={STATUS_COLOR[i.status]} />
                    </TableCell>
                  </TableRow>
                ))}
                {invoices.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6}>
                      <Typography variant="body2" color="text.secondary">
                        No invoices yet.
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
          <Typography variant="subtitle1" gutterBottom>
            New Receipt
          </Typography>
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center" }}>
            <TextField select label="Customer" size="small" value={rcCustomer} onChange={(e) => setRcCustomer(e.target.value)} sx={{ minWidth: 170 }}>
              {customers.map((c) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Date" type="date" size="small" value={rcDate} onChange={(e) => setRcDate(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
            <TextField select label="Cash account" size="small" value={rcCashAccount} onChange={(e) => setRcCashAccount(e.target.value)} sx={{ minWidth: 170 }}>
              {glAccounts.map((g) => (
                <MenuItem key={g.id} value={g.id}>
                  {g.code} {g.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Amount" type="number" size="small" value={rcAmount} onChange={(e) => setRcAmount(e.target.value)} sx={{ width: 130 }} />
            <TextField label="Reference" size="small" value={rcReference} onChange={(e) => setRcReference(e.target.value)} sx={{ minWidth: 160 }} />
            <Button variant="contained" onClick={handleCreateReceipt} disabled={!rcCustomer || !rcCashAccount || !rcAmount}>
              Record receipt
            </Button>
          </Stack>

          <Typography variant="subtitle2" sx={{ mt: 3 }}>
            Apply a Receipt to an Invoice
          </Typography>
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center", mt: 1 }}>
            <TextField select label="Receipt (unapplied)" size="small" value={applyReceiptId} onChange={(e) => setApplyReceiptId(e.target.value)} sx={{ minWidth: 220 }}>
              {unappliedReceipts.map((r) => (
                <MenuItem key={r.id} value={r.id}>
                  {r.customer_name} — {fmt(r.unapplied_balance)} unapplied
                </MenuItem>
              ))}
            </TextField>
            <TextField select label="Invoice" size="small" value={applyInvoiceId} onChange={(e) => setApplyInvoiceId(e.target.value)} sx={{ minWidth: 220 }}>
              {openInvoices.map((i) => (
                <MenuItem key={i.id} value={i.id}>
                  {i.invoice_number} ({i.customer_name}) — {fmt(i.remaining_balance)} remaining
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Amount" type="number" size="small" value={applyReceiptAmount} onChange={(e) => setApplyReceiptAmount(e.target.value)} sx={{ width: 130 }} />
            <Button variant="contained" onClick={handleApplyReceipt} disabled={!applyReceiptId || !applyInvoiceId || !applyReceiptAmount}>
              Apply
            </Button>
          </Stack>

          <TableContainer sx={{ mt: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell>Customer</TableCell>
                  <TableCell align="right">Amount</TableCell>
                  <TableCell align="right">Unapplied</TableCell>
                  <TableCell>Reference</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {receipts.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell>{r.receipt_date}</TableCell>
                    <TableCell>{r.customer_name}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(r.amount)}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(r.unapplied_balance)}</TableCell>
                    <TableCell>{r.reference ?? "—"}</TableCell>
                  </TableRow>
                ))}
                {receipts.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <Typography variant="body2" color="text.secondary">
                        No receipts yet.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap" }}>
        <Typography variant="h6">AR Aging</Typography>
        <TextField label="As of" type="date" size="small" value={arAsOf} onChange={(e) => setArAsOf(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
      </Stack>
      {arAging && (
        <>
          <Typography variant="body2">
            Total outstanding: <strong>{fmt(arAging.total_remaining)}</strong>
          </Typography>
          <TableContainer component={Card} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Customer</TableCell>
                  <TableCell>Invoice</TableCell>
                  <TableCell>Due</TableCell>
                  <TableCell align="right">Days Overdue</TableCell>
                  <TableCell>Bucket</TableCell>
                  <TableCell align="right">Remaining</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {arAging.rows.map((row) => (
                  <TableRow key={row.document_id}>
                    <TableCell>{row.party_name}</TableCell>
                    <TableCell>{row.number}</TableCell>
                    <TableCell>{row.due_date}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{row.days_overdue}</TableCell>
                    <TableCell>
                      <Chip size="small" label={row.bucket} color={BUCKET_COLOR[row.bucket]} />
                    </TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.remaining_balance)}</TableCell>
                  </TableRow>
                ))}
                {arAging.rows.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6}>
                      <Typography variant="body2" color="text.secondary">
                        Nothing outstanding.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}

      <Typography variant="h6">Accounts Payable</Typography>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            New Bill
          </Typography>
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center" }}>
            <TextField select label="Vendor" size="small" value={billVendor} onChange={(e) => setBillVendor(e.target.value)} sx={{ minWidth: 170 }}>
              {vendors.map((v) => (
                <MenuItem key={v.id} value={v.id}>
                  {v.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Bill #" size="small" value={billNumber} onChange={(e) => setBillNumber(e.target.value)} sx={{ width: 130 }} />
            <TextField label="Date" type="date" size="small" value={billDate} onChange={(e) => setBillDate(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
            <TextField label="Due date" type="date" size="small" value={billDueDate} onChange={(e) => setBillDueDate(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
            <TextField select label="Expense account" size="small" value={billExpenseAccount} onChange={(e) => setBillExpenseAccount(e.target.value)} sx={{ minWidth: 170 }}>
              {glAccounts.map((g) => (
                <MenuItem key={g.id} value={g.id}>
                  {g.code} {g.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Net amount" type="number" size="small" value={billAmount} onChange={(e) => setBillAmount(e.target.value)} sx={{ width: 130 }} />
            <TextField select label="Tax code" size="small" value={billTaxCode} onChange={(e) => setBillTaxCode(e.target.value)} sx={{ minWidth: 160 }}>
              <MenuItem value="">— none —</MenuItem>
              {taxCodes.filter((t) => t.is_active).map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.code} ({t.rate_pct}%)
                </MenuItem>
              ))}
            </TextField>
            <TextField select label="TDS section" size="small" value={billTdsSection} onChange={(e) => setBillTdsSection(e.target.value)} sx={{ minWidth: 160 }}>
              <MenuItem value="">— none —</MenuItem>
              {tdsSections.filter((s) => s.is_active).map((s) => (
                <MenuItem key={s.id} value={s.id}>
                  {s.section_code} ({s.rate_pct}%)
                </MenuItem>
              ))}
            </TextField>
            <Button variant="contained" onClick={handleCreateBill} disabled={!billVendor || !billNumber || !billExpenseAccount || !billAmount}>
              Create bill
            </Button>
          </Stack>

          <TableContainer sx={{ mt: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Number</TableCell>
                  <TableCell>Vendor</TableCell>
                  <TableCell>Due</TableCell>
                  <TableCell align="right">TDS</TableCell>
                  <TableCell align="right">Amount</TableCell>
                  <TableCell align="right">Remaining</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {bills.map((b) => (
                  <TableRow key={b.id}>
                    <TableCell>{b.bill_number}</TableCell>
                    <TableCell>{b.vendor_name}</TableCell>
                    <TableCell>{b.due_date}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{b.tds_amount > 0 ? fmt(b.tds_amount) : "—"}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(b.amount)}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(b.remaining_balance)}</TableCell>
                    <TableCell>
                      <Chip size="small" label={b.status.replace("_", " ")} color={STATUS_COLOR[b.status]} />
                    </TableCell>
                  </TableRow>
                ))}
                {bills.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7}>
                      <Typography variant="body2" color="text.secondary">
                        No bills yet.
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
          <Typography variant="subtitle1" gutterBottom>
            New Payment
          </Typography>
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center" }}>
            <TextField select label="Vendor" size="small" value={pmVendor} onChange={(e) => setPmVendor(e.target.value)} sx={{ minWidth: 170 }}>
              {vendors.map((v) => (
                <MenuItem key={v.id} value={v.id}>
                  {v.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Date" type="date" size="small" value={pmDate} onChange={(e) => setPmDate(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
            <TextField select label="Cash account" size="small" value={pmCashAccount} onChange={(e) => setPmCashAccount(e.target.value)} sx={{ minWidth: 170 }}>
              {glAccounts.map((g) => (
                <MenuItem key={g.id} value={g.id}>
                  {g.code} {g.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Amount" type="number" size="small" value={pmAmount} onChange={(e) => setPmAmount(e.target.value)} sx={{ width: 130 }} />
            <TextField label="Reference" size="small" value={pmReference} onChange={(e) => setPmReference(e.target.value)} sx={{ minWidth: 160 }} />
            <Button variant="contained" onClick={handleCreatePayment} disabled={!pmVendor || !pmCashAccount || !pmAmount}>
              Record payment
            </Button>
          </Stack>

          <Typography variant="subtitle2" sx={{ mt: 3 }}>
            Apply a Payment to a Bill
          </Typography>
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center", mt: 1 }}>
            <TextField select label="Payment (unapplied)" size="small" value={applyPaymentId} onChange={(e) => setApplyPaymentId(e.target.value)} sx={{ minWidth: 220 }}>
              {unappliedPayments.map((p) => (
                <MenuItem key={p.id} value={p.id}>
                  {p.vendor_name} — {fmt(p.unapplied_balance)} unapplied
                </MenuItem>
              ))}
            </TextField>
            <TextField select label="Bill" size="small" value={applyBillId} onChange={(e) => setApplyBillId(e.target.value)} sx={{ minWidth: 220 }}>
              {openBills.map((b) => (
                <MenuItem key={b.id} value={b.id}>
                  {b.bill_number} ({b.vendor_name}) — {fmt(b.remaining_balance)} remaining
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Amount" type="number" size="small" value={applyPaymentAmount} onChange={(e) => setApplyPaymentAmount(e.target.value)} sx={{ width: 130 }} />
            <Button variant="contained" onClick={handleApplyPayment} disabled={!applyPaymentId || !applyBillId || !applyPaymentAmount}>
              Apply
            </Button>
          </Stack>

          <TableContainer sx={{ mt: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell>Vendor</TableCell>
                  <TableCell align="right">Amount</TableCell>
                  <TableCell align="right">Unapplied</TableCell>
                  <TableCell>Reference</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {payments.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell>{p.payment_date}</TableCell>
                    <TableCell>{p.vendor_name}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(p.amount)}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(p.unapplied_balance)}</TableCell>
                    <TableCell>{p.reference ?? "—"}</TableCell>
                  </TableRow>
                ))}
                {payments.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <Typography variant="body2" color="text.secondary">
                        No payments yet.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap" }}>
        <Typography variant="h6">AP Aging</Typography>
        <TextField label="As of" type="date" size="small" value={apAsOf} onChange={(e) => setApAsOf(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
      </Stack>
      {apAging && (
        <>
          <Typography variant="body2">
            Total outstanding: <strong>{fmt(apAging.total_remaining)}</strong>
          </Typography>
          <TableContainer component={Card} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Vendor</TableCell>
                  <TableCell>Bill</TableCell>
                  <TableCell>Due</TableCell>
                  <TableCell align="right">Days Overdue</TableCell>
                  <TableCell>Bucket</TableCell>
                  <TableCell align="right">Remaining</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {apAging.rows.map((row) => (
                  <TableRow key={row.document_id}>
                    <TableCell>{row.party_name}</TableCell>
                    <TableCell>{row.number}</TableCell>
                    <TableCell>{row.due_date}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{row.days_overdue}</TableCell>
                    <TableCell>
                      <Chip size="small" label={row.bucket} color={BUCKET_COLOR[row.bucket]} />
                    </TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.remaining_balance)}</TableCell>
                  </TableRow>
                ))}
                {apAging.rows.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6}>
                      <Typography variant="body2" color="text.secondary">
                        Nothing outstanding.
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
