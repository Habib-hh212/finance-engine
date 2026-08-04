import { Avatar, Box, Card, CardContent, Chip, Link, Stack, Typography } from "@mui/material";
import SchoolIcon from "@mui/icons-material/School";
import EmailIcon from "@mui/icons-material/Email";

const EMAIL = "stu162703@ardenuniversity.ac.uk";

export function ContactPage() {
  return (
    <Stack spacing={3} sx={{ maxWidth: 560 }}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Contact
      </Typography>

      <Card variant="outlined" sx={{ overflow: "hidden" }}>
        <Box
          sx={{
            height: 72,
            background: "linear-gradient(135deg, #2f5d50 0%, #1f3a30 100%)",
          }}
        />
        <CardContent sx={{ pt: 0 }}>
          <Stack direction="row" spacing={2} sx={{ alignItems: "flex-end", mt: "-32px", mb: 2 }}>
            <Avatar
              sx={{
                width: 72,
                height: 72,
                bgcolor: "background.paper",
                color: "primary.main",
                border: "3px solid",
                borderColor: "background.paper",
                fontSize: 28,
                fontWeight: 700,
                boxShadow: 1,
              }}
            >
              H
            </Avatar>
          </Stack>

          <Stack spacing={0.5} sx={{ mb: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              Habibullah
            </Typography>
            <Chip
              icon={<SchoolIcon />}
              label="University Project"
              size="small"
              color="primary"
              variant="outlined"
              sx={{ width: "fit-content" }}
            />
          </Stack>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5, lineHeight: 1.6 }}>
            Finance Engine is a university project built end-to-end as a multi-company financial forecasting and
            controlling platform.
          </Typography>

          <Stack
            direction="row"
            spacing={1.5}
            sx={{
              alignItems: "center",
              p: 1.5,
              borderRadius: 2,
              bgcolor: "action.hover",
            }}
          >
            <EmailIcon fontSize="small" color="primary" />
            <Link href={`mailto:${EMAIL}`} underline="hover" sx={{ fontWeight: 500 }}>
              {EMAIL}
            </Link>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
