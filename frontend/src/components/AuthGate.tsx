import { useState, type ReactNode } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";

export function AuthGate({ children }: { children: ReactNode }) {
  const { user, loading, login, register } = useAuth();
  const [tab, setTab] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!user) {
    const handleSubmit = async () => {
      setSubmitting(true);
      setError(null);
      try {
        if (tab === "login") {
          await login(email, password);
        } else {
          await register(email, password, name);
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Something went wrong");
      } finally {
        setSubmitting(false);
      }
    };

    const canSubmit = tab === "login" ? email && password : email && password && name;

    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", bgcolor: "background.default" }}>
        <Card sx={{ width: 420 }}>
          <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="fullWidth">
            <Tab label="Log in" value="login" />
            <Tab label="Create account" value="register" />
          </Tabs>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              {tab === "login" ? "Welcome back" : "Create your account"}
            </Typography>
            <Stack spacing={2} sx={{ mt: 2 }}>
              {tab === "register" && <TextField label="Your name" value={name} onChange={(e) => setName(e.target.value)} autoFocus fullWidth />}
              <TextField label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} fullWidth autoFocus={tab === "login"} />
              <TextField label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} fullWidth />
              {error && <Alert severity="error">{error}</Alert>}
              <Button variant="contained" onClick={handleSubmit} disabled={submitting || !canSubmit}>
                {tab === "login" ? "Log in" : "Create account"}
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Box>
    );
  }

  return <>{children}</>;
}
