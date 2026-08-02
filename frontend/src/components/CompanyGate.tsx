import { useState, type ReactNode } from "react";
import { Alert, Box, Button, Card, CardContent, CircularProgress, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useCompany } from "../context/CompanyContext";
import { createCompany } from "../api/companies";

const CURRENCIES = ["USD", "EUR", "GBP", "AED", "PKR", "INR"];

export function CompanyGate({ children }: { children: ReactNode }) {
  const { companies, company, loading, error, refresh, selectCompany } = useCompany();
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", p: 3 }}>
        <Alert severity="error" sx={{ maxWidth: 480 }}>
          Can't reach the API at the configured backend URL. Is the backend running? ({error})
        </Alert>
      </Box>
    );
  }

  if (companies.length === 0 || !company) {
    const handleCreate = async () => {
      if (!name.trim()) return;
      setSubmitting(true);
      setFormError(null);
      try {
        const created = await createCompany(name.trim(), currency);
        await refresh();
        selectCompany(created.id);
      } catch (err) {
        setFormError(err instanceof Error ? err.message : "Failed to create company");
      } finally {
        setSubmitting(false);
      }
    };

    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", bgcolor: "background.default" }}>
        <Card sx={{ width: 420 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Set up your company
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Everything in Finance Engine is scoped to a company. Create one to get started.
            </Typography>
            <Stack spacing={2}>
              <TextField
                label="Company name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
                fullWidth
              />
              <TextField select label="Base currency" value={currency} onChange={(e) => setCurrency(e.target.value)} fullWidth>
                {CURRENCIES.map((c) => (
                  <MenuItem key={c} value={c}>
                    {c}
                  </MenuItem>
                ))}
              </TextField>
              {formError && <Alert severity="error">{formError}</Alert>}
              <Button variant="contained" onClick={handleCreate} disabled={submitting || !name.trim()}>
                Create company
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Box>
    );
  }

  return <>{children}</>;
}
