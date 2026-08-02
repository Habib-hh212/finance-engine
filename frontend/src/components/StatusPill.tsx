import { Chip } from "@mui/material";
import type { TrafficLight } from "../api/types";

const CONFIG: Record<TrafficLight, { label: string; color: "success" | "warning" | "error" }> = {
  green: { label: "Green", color: "success" },
  yellow: { label: "Watch", color: "warning" },
  red: { label: "Action", color: "error" },
};

export function StatusPill({ status }: { status: TrafficLight }) {
  const { label, color } = CONFIG[status];
  return <Chip size="small" label={label} color={color} variant={status === "green" ? "outlined" : "filled"} />;
}
