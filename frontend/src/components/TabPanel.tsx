import { Box } from "@mui/material";
import type { ReactNode } from "react";

export function TabPanel({ value, index, children }: { value: number; index: number; children: ReactNode }) {
  if (value !== index) return null;
  return (
    <Box role="tabpanel" sx={{ pt: 3 }}>
      {children}
    </Box>
  );
}
