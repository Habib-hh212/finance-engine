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
import { createGLAccount, listGLAccounts, updateGLAccount } from "../api/budgets";
import type { GLAccount, GLCategory, GLForecastRole } from "../api/types";

const CATEGORIES: GLCategory[] = ["asset", "liability", "equity", "revenue", "expense"];

const CATEGORY_COLOR: Record<GLCategory, "info" | "warning" | "secondary" | "success" | "error"> = {
  asset: "info",
  liability: "warning",
  equity: "secondary",
  revenue: "success",
  expense: "error",
};

function rolesForCategory(category: GLCategory): GLForecastRole[] {
  if (category === "asset") return ["cash", "accounts_receivable"];
  if (category === "liability") return ["accounts_payable", "tds_payable"];
  return [];
}

export function ChartOfAccountsPage() {
  const { company } = useCompany();
  const [accounts, setAccounts] = useState<GLAccount[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState<GLCategory>("asset");

  const load = async () => {
    if (!company) return;
    setError(null);
    try {
      setAccounts(await listGLAccounts(company.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load the chart of accounts");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);

  const handleCreate = async () => {
    if (!company || !code || !name) return;
    setError(null);
    try {
      await createGLAccount(company.id, code, name, category);
      setCode("");
      setName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create the account");
    }
  };

  const handleChangeRole = async (accountId: string, role: GLForecastRole | "") => {
    setError(null);
    try {
      await updateGLAccount(accountId, role || null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update the account");
    }
  };

  const byCategory = CATEGORIES.map((cat) => ({ cat, rows: accounts.filter((a) => a.category === cat) }));

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Chart of Accounts
      </Typography>
      <Typography variant="caption" color="text.secondary">
        The master list of G/L accounts every journal entry, budget line, and actual posts against. Assets and
        expenses are debit-normal; liabilities, equity, and revenue are credit-normal — that's what signs the amount
        correctly everywhere else in the app once an account is created here.
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            New Account
          </Typography>
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center" }}>
            <TextField label="Code" size="small" value={code} onChange={(e) => setCode(e.target.value)} sx={{ width: 140 }} />
            <TextField label="Name" size="small" value={name} onChange={(e) => setName(e.target.value)} sx={{ minWidth: 240, flexGrow: 1 }} />
            <TextField
              select
              label="Category"
              size="small"
              value={category}
              onChange={(e) => setCategory(e.target.value as GLCategory)}
              sx={{ width: 160 }}
            >
              {CATEGORIES.map((c) => (
                <MenuItem key={c} value={c}>
                  {c}
                </MenuItem>
              ))}
            </TextField>
            <Button variant="contained" onClick={handleCreate} disabled={!code || !name}>
              Add account
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {byCategory.map(({ cat, rows }) => (
        <Stack key={cat} spacing={1}>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <Typography variant="h6" sx={{ textTransform: "capitalize" }}>
              {cat}
            </Typography>
            <Chip size="small" label={rows.length} color={CATEGORY_COLOR[cat]} variant="outlined" />
          </Stack>
          <TableContainer component={Card} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Code</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell>Forecast Role</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((a) => {
                  const options = rolesForCategory(a.category);
                  return (
                    <TableRow key={a.id}>
                      <TableCell sx={{ fontVariantNumeric: "tabular-nums" }}>{a.code}</TableCell>
                      <TableCell>{a.name}</TableCell>
                      <TableCell sx={{ minWidth: 200 }}>
                        {options.length > 0 ? (
                          <TextField
                            select
                            size="small"
                            fullWidth
                            value={a.forecast_role ?? ""}
                            onChange={(e) => handleChangeRole(a.id, e.target.value as GLForecastRole | "")}
                            slotProps={{ select: { displayEmpty: true } }}
                          >
                            <MenuItem value="">
                              <em>No forecast role</em>
                            </MenuItem>
                            {options.map((role) => (
                              <MenuItem key={role} value={role}>
                                {role.replace(/_/g, " ")}
                              </MenuItem>
                            ))}
                          </TextField>
                        ) : (
                          <Typography variant="caption" color="text.secondary">
                            —
                          </Typography>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
                {rows.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3}>
                      <Typography variant="body2" color="text.secondary">
                        No {cat} accounts yet.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Stack>
      ))}
    </Stack>
  );
}
