import DashboardIcon from "@mui/icons-material/Dashboard";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import AccountBalanceIcon from "@mui/icons-material/AccountBalance";
import WaterDropIcon from "@mui/icons-material/WaterDrop";
import RuleIcon from "@mui/icons-material/Rule";
import PieChartIcon from "@mui/icons-material/PieChart";
import DescriptionIcon from "@mui/icons-material/Description";
import PrecisionManufacturingIcon from "@mui/icons-material/PrecisionManufacturing";
import TimelineIcon from "@mui/icons-material/Timeline";
import ContactMailIcon from "@mui/icons-material/ContactMail";
import HistoryIcon from "@mui/icons-material/History";
import CurrencyExchangeIcon from "@mui/icons-material/CurrencyExchange";
import MenuBookIcon from "@mui/icons-material/MenuBook";
import ListAltIcon from "@mui/icons-material/ListAlt";
import ReceiptLongIcon from "@mui/icons-material/ReceiptLong";
import DomainIcon from "@mui/icons-material/Domain";
import EventAvailableIcon from "@mui/icons-material/EventAvailable";
import RequestQuoteIcon from "@mui/icons-material/RequestQuote";
import AccountBalanceWalletIcon from "@mui/icons-material/AccountBalanceWallet";
import PercentIcon from "@mui/icons-material/Percent";
import {
  AppBar,
  Box,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Select,
  Toolbar,
  Tooltip,
  Typography,
} from "@mui/material";
import LogoutIcon from "@mui/icons-material/Logout";
import { useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useCompany } from "../context/CompanyContext";

const DRAWER_WIDTH = 240;

const NAV_GROUPS: { heading: string | null; items: { to: string; label: string; icon: ReactNode }[] }[] = [
  {
    heading: null,
    items: [
      { to: "/", label: "Dashboard", icon: <DashboardIcon /> },
      { to: "/sales-forecast", label: "Sales Forecast", icon: <ShowChartIcon /> },
      { to: "/budgets", label: "Budget Planning", icon: <AccountBalanceIcon /> },
      { to: "/cash-flow", label: "Cash Flow", icon: <WaterDropIcon /> },
      { to: "/controlling", label: "Cost Controlling", icon: <RuleIcon /> },
      { to: "/profitability", label: "Profitability", icon: <PieChartIcon /> },
      { to: "/financial-statements", label: "Financial Statements", icon: <DescriptionIcon /> },
      { to: "/standard-costing", label: "Standard Costing", icon: <PrecisionManufacturingIcon /> },
      { to: "/scenarios", label: "Scenario Planning", icon: <TimelineIcon /> },
      { to: "/fx-scenario", label: "FX Scenario", icon: <CurrencyExchangeIcon /> },
    ],
  },
  {
    heading: "General Ledger",
    items: [
      { to: "/general-ledger", label: "Bookkeeping", icon: <MenuBookIcon /> },
      { to: "/chart-of-accounts", label: "Chart of Accounts", icon: <ListAltIcon /> },
      { to: "/tax-codes", label: "Tax Codes (VAT/GST)", icon: <ReceiptLongIcon /> },
      { to: "/tds", label: "TDS (India)", icon: <PercentIcon /> },
      { to: "/fixed-assets", label: "Fixed Assets", icon: <DomainIcon /> },
      { to: "/period-close", label: "Period Close", icon: <EventAvailableIcon /> },
      { to: "/receivables-payables", label: "Receivables & Payables", icon: <RequestQuoteIcon /> },
      { to: "/bank-reconciliation", label: "Bank Reconciliation", icon: <AccountBalanceWalletIcon /> },
    ],
  },
  {
    heading: "System",
    items: [
      { to: "/audit-trail", label: "Audit Trail", icon: <HistoryIcon /> },
      { to: "/contact", label: "Contact", icon: <ContactMailIcon /> },
    ],
  },
];

export function Layout({ children }: { children: ReactNode }) {
  const { companies, company, selectCompany } = useCompany();
  const { user, logout } = useAuth();
  const location = useLocation();
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);

  return (
    <Box sx={{ display: "flex" }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }} color="default" elevation={0}>
        <Toolbar sx={{ gap: 2 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.25 }}>
            <Box
              sx={{
                width: 10,
                height: 10,
                borderRadius: "3px",
                bgcolor: "primary.main",
                transform: "rotate(45deg)",
              }}
            />
            <Typography variant="h6" noWrap sx={{ color: "primary.dark", lineHeight: 1 }}>
              Finance Engine
            </Typography>
          </Box>
          <Box sx={{ flexGrow: 1 }} />
          {companies.length > 0 && (
            <Select
              size="small"
              value={company?.id ?? ""}
              onChange={(e) => selectCompany(e.target.value)}
              sx={{ minWidth: 220 }}
            >
              {companies.map((c) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.name} ({c.base_currency})
                </MenuItem>
              ))}
            </Select>
          )}
          <Tooltip title={user?.name ?? ""}>
            <IconButton onClick={(e) => setMenuAnchor(e.currentTarget)} size="small">
              <LogoutIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Menu anchorEl={menuAnchor} open={Boolean(menuAnchor)} onClose={() => setMenuAnchor(null)}>
            <MenuItem disabled sx={{ opacity: "1 !important" }}>
              {user?.email}
            </MenuItem>
            <Divider />
            <MenuItem onClick={logout}>Log out</MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: { width: DRAWER_WIDTH, boxSizing: "border-box" },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: "auto", pt: 1 }}>
          {NAV_GROUPS.map((group, groupIndex) => (
            <Box key={group.heading ?? `group-${groupIndex}`}>
              {group.heading && (
                <>
                  {groupIndex > 0 && <Divider sx={{ mx: 2, my: 1 }} />}
                  <Typography
                    variant="caption"
                    sx={{
                      display: "block",
                      px: 2.5,
                      pt: 0.5,
                      pb: 0.5,
                      fontWeight: 700,
                      letterSpacing: "0.06em",
                      textTransform: "uppercase",
                      color: "text.secondary",
                      fontSize: "0.68rem",
                    }}
                  >
                    {group.heading}
                  </Typography>
                </>
              )}
              <List sx={{ px: 0.5 }}>
                {group.items.map((item) => {
                  const active = location.pathname === item.to;
                  return (
                    <ListItemButton key={item.to} component={NavLink} to={item.to} selected={active} sx={{ py: 0.9 }}>
                      <ListItemIcon sx={{ minWidth: 38, color: active ? "primary.main" : "text.secondary" }}>
                        {item.icon}
                      </ListItemIcon>
                      <ListItemText
                        primary={item.label}
                        slotProps={{ primary: { sx: { fontSize: "0.9rem", fontWeight: active ? 600 : 500 } } }}
                      />
                    </ListItemButton>
                  );
                })}
              </List>
            </Box>
          ))}
          <Divider sx={{ mx: 2, my: 1 }} />
        </Box>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3, bgcolor: "background.default", minHeight: "100vh" }}>
        <Toolbar />
        {children}
      </Box>
    </Box>
  );
}
