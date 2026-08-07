import { useEffect, useState } from "react";
import {
  Alert,
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
import { useCompany } from "../context/CompanyContext";
import { getAuditLog } from "../api/audit";
import type { AuditLogEntry } from "../api/types";

const ENTITY_TYPES = [
  { value: "", label: "All entities" },
  { value: "budget", label: "Budget" },
  { value: "budget_line", label: "Budget Line" },
  { value: "actual_line", label: "Actual" },
  { value: "cash_item", label: "Cash Item" },
  { value: "gl_account", label: "GL Account" },
  { value: "cost_center", label: "Cost Center" },
  { value: "scenario", label: "Scenario" },
];

const ACTION_COLOR: Record<string, "success" | "info" | "warning" | "error" | "default"> = {
  create: "success",
  update: "info",
  submit: "info",
  approve: "success",
  reject: "error",
  delete: "warning",
};

const fmtTimestamp = (iso: string) => new Date(iso).toLocaleString();

export function AuditTrailPage() {
  const { company } = useCompany();
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [entityType, setEntityType] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!company) return;
    setError(null);
    try {
      setEntries(await getAuditLog(company.id, entityType || undefined));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load the audit trail");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id, entityType]);

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Audit Trail
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <TextField
        select
        label="Entity type"
        size="small"
        value={entityType}
        onChange={(e) => setEntityType(e.target.value)}
        sx={{ width: 220 }}
      >
        {ENTITY_TYPES.map((t) => (
          <MenuItem key={t.value} value={t.value}>
            {t.label}
          </MenuItem>
        ))}
      </TextField>

      <TableContainer component={Card} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>When</TableCell>
              <TableCell>Entity</TableCell>
              <TableCell>Action</TableCell>
              <TableCell>Actor</TableCell>
              <TableCell>Summary</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {entries.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell sx={{ whiteSpace: "nowrap" }}>{fmtTimestamp(entry.created_at)}</TableCell>
                <TableCell>{entry.entity_type}</TableCell>
                <TableCell>
                  <Chip size="small" label={entry.action} color={ACTION_COLOR[entry.action] ?? "default"} />
                </TableCell>
                <TableCell>{entry.actor_name}</TableCell>
                <TableCell>{entry.summary}</TableCell>
              </TableRow>
            ))}
            {entries.length === 0 && (
              <TableRow>
                <TableCell colSpan={5}>
                  <Typography variant="body2" color="text.secondary">
                    No audit entries yet.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Stack>
  );
}
