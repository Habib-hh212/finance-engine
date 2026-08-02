import { useEffect, useState } from "react";
import {
  Alert,
  Card,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useCompany } from "../context/CompanyContext";
import { getProfitabilityByCustomer, getProfitabilityByProduct } from "../api/profitability";
import type { CustomerProfitability, ProductProfitability } from "../api/types";

const fmt = (v: number | null) => (v === null ? "—" : v.toLocaleString());
const fmtPct = (v: number | null) => (v === null ? "—" : `${v}%`);

export function ProfitabilityPage() {
  const { company } = useCompany();
  const [byProduct, setByProduct] = useState<ProductProfitability[]>([]);
  const [byCustomer, setByCustomer] = useState<CustomerProfitability[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!company) return;
    setError(null);
    Promise.all([getProfitabilityByProduct(company.id), getProfitabilityByCustomer(company.id)])
      .then(([products, customers]) => {
        setByProduct(products);
        setByCustomer(customers);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load profitability"));
  }, [company?.id]);

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Profitability Analysis
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}
      <Typography variant="caption" color="text.secondary">
        Contribution margin needs a unit variable cost set per product — set it on the Sales Forecast page. Products without
        one show revenue but a blank contribution, not a false zero.
      </Typography>

      <Typography variant="h6">By Product</Typography>
      <TableContainer component={Card} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Product</TableCell>
              <TableCell align="right">Qty</TableCell>
              <TableCell align="right">Revenue</TableCell>
              <TableCell align="right">Unit Price</TableCell>
              <TableCell align="right">Unit Cost</TableCell>
              <TableCell align="right">Contribution/Unit</TableCell>
              <TableCell align="right">Total Contribution</TableCell>
              <TableCell align="right">Margin %</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {byProduct.map((p) => (
              <TableRow key={p.product_id}>
                <TableCell>{p.sku} — {p.name}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(p.quantity)}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(p.revenue)}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(p.unit_price)}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(p.unit_variable_cost)}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(p.contribution_per_unit)}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(p.contribution_margin_total)}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmtPct(p.contribution_margin_pct)}</TableCell>
              </TableRow>
            ))}
            {byProduct.length === 0 && (
              <TableRow>
                <TableCell colSpan={8}>
                  <Typography variant="body2" color="text.secondary">
                    No sales data yet.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Typography variant="h6">By Customer</Typography>
      <TableContainer component={Card} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Customer</TableCell>
              <TableCell align="right">Revenue</TableCell>
              <TableCell align="right">Total Contribution</TableCell>
              <TableCell align="right">Margin %</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {byCustomer.map((c) => (
              <TableRow key={c.customer_id}>
                <TableCell>{c.name}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(c.revenue)}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(c.contribution_margin_total)}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmtPct(c.contribution_margin_pct)}</TableCell>
              </TableRow>
            ))}
            {byCustomer.length === 0 && (
              <TableRow>
                <TableCell colSpan={4}>
                  <Typography variant="body2" color="text.secondary">
                    No customer-attributed sales yet.
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
