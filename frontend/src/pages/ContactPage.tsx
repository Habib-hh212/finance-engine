import { Card, CardContent, Chip, Link, Stack, Typography } from "@mui/material";
import SchoolIcon from "@mui/icons-material/School";
import PhoneIcon from "@mui/icons-material/Phone";

export function ContactPage() {
  return (
    <Stack spacing={3} sx={{ maxWidth: 520 }}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Contact
      </Typography>

      <Card variant="outlined">
        <CardContent>
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
              <Typography variant="h6">Habibullah</Typography>
              <Chip icon={<SchoolIcon />} label="University Project" size="small" color="primary" variant="outlined" />
            </Stack>
            <Typography variant="body2" color="text.secondary">
              Finance Engine is a university project built end-to-end as a multi-company financial forecasting and
              controlling platform.
            </Typography>
            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
              <PhoneIcon fontSize="small" color="action" />
              <Link href="tel:+91989198506" underline="hover">
                +91 98919 8506
              </Link>
            </Stack>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
