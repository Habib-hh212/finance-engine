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

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: <DashboardIcon /> },
  { to: "/sales-forecast", label: "Sales Forecast", icon: <ShowChartIcon /> },
  { to: "/budgets", label: "Budget Planning", icon: <AccountBalanceIcon /> },
  { to: "/cash-flow", label: "Cash Flow", icon: <WaterDropIcon /> },
  { to: "/controlling", label: "Cost Controlling", icon: <RuleIcon /> },
  { to: "/profitability", label: "Profitability", icon: <PieChartIcon /> },
  { to: "/financial-statements", label: "Financial Statements", icon: <DescriptionIcon /> },
  { to: "/standard-costing", label: "Standard Costing", icon: <PrecisionManufacturingIcon /> },
  { to: "/scenarios", label: "Scenario Planning", icon: <TimelineIcon /> },
  { to: "/contact", label: "Contact", icon: <ContactMailIcon /> },
];

export function Layout({ children }: { children: ReactNode }) {
  const { companies, company, selectCompany } = useCompany();
  const { user, logout } = useAuth();
  const location = useLocation();
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);

  return (
    <Box sx={{ display: "flex" }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }} color="default" elevation={1}>
        <Toolbar sx={{ gap: 2 }}>
          <Typography variant="h6" noWrap sx={{ fontWeight: 700, color: "primary.main" }}>
            Finance Engine
          </Typography>
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
        <Box sx={{ overflow: "auto" }}>
          <List>
            {NAV_ITEMS.map((item) => (
              <ListItemButton
                key={item.to}
                component={NavLink}
                to={item.to}
                selected={location.pathname === item.to}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItemButton>
            ))}
          </List>
          <Divider />
        </Box>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3, bgcolor: "background.default", minHeight: "100vh" }}>
        <Toolbar />
        {children}
      </Box>
    </Box>
  );
}
