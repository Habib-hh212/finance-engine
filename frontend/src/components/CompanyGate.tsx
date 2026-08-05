import { useState, type ReactNode } from "react";
import { Alert, Autocomplete, Box, Button, Card, CardContent, CircularProgress, Stack, TextField, Typography } from "@mui/material";
import { useCompany } from "../context/CompanyContext";
import { createCompany } from "../api/companies";
import { CURRENCIES, type CurrencyOption } from "../data/currencies";

export function CompanyGate({ children }: { children: ReactNode }) {
  const { companies, company, loading, error, refresh, selectCompany } = useCompany();
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState<CurrencyOption>(CURRENCIES[0]);
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
        const created = await createCompany(name.trim(), currency.code);
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
              <Autocomplete
                options={CURRENCIES}
                getOptionLabel={(c) => `${c.code} – ${c.name}`}
                value={currency}
                onChange={(_, value) => value && setCurrency(value)}
                disableClearable
                isOptionEqualToValue={(a, b) => a.code === b.code}
                renderInput={(params) => <TextField {...params} label="Base currency" />}
              />
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
