import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Alert, Box, Button, Card, CardContent, Stack, TextField, Typography } from "@mui/material";
import { resetPassword } from "../api/auth";
import { ApiError } from "../api/client";

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const navigate = useNavigate();

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  if (!token) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", p: 3 }}>
        <Alert severity="error" sx={{ maxWidth: 480 }}>
          This reset link is missing its token. Request a new one from the login page.
        </Alert>
      </Box>
    );
  }

  if (done) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", bgcolor: "background.default" }}>
        <Card sx={{ width: 420 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Password reset
            </Typography>
            <Alert severity="success" sx={{ mb: 2 }}>
              Your password has been changed. You can now log in with it.
            </Alert>
            <Button variant="contained" fullWidth onClick={() => navigate("/")}>
              Go to login
            </Button>
          </CardContent>
        </Card>
      </Box>
    );
  }

  const canSubmit = password.length >= 8 && password === confirmPassword;

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", bgcolor: "background.default" }}>
      <Card sx={{ width: 420 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Choose a new password
          </Typography>
          <Stack spacing={2} sx={{ mt: 2 }}>
            <TextField
              label="New password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              helperText="At least 8 characters"
              autoFocus
              fullWidth
            />
            <TextField
              label="Confirm new password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              error={confirmPassword.length > 0 && confirmPassword !== password}
              helperText={confirmPassword.length > 0 && confirmPassword !== password ? "Passwords don't match" : " "}
              fullWidth
            />
            {error && <Alert severity="error">{error}</Alert>}
            <Button variant="contained" onClick={handleSubmit} disabled={submitting || !canSubmit}>
              Reset password
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
