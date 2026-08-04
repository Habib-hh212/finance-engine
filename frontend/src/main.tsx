import { CssBaseline, ThemeProvider, alpha, createTheme } from "@mui/material";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.tsx";
import { AuthProvider } from "./context/AuthContext";
import { CompanyProvider } from "./context/CompanyContext";

// A quiet, confident palette built around one deep forest-green brand color --
// everything else (neutrals, dividers, surfaces) is derived from it with a
// slight warm/sage tint rather than pure grey, so the app reads as designed
// rather than left at framework defaults.
const brand = {
  main: "#2f5d50",
  dark: "#1c3a30",
  light: "#4d7d6d",
};

const theme = createTheme({
  palette: {
    mode: "light",
    primary: brand,
    secondary: { main: "#a8632f" },
    background: { default: "#f6f7f4", paper: "#ffffff" },
    text: { primary: "#1b2420", secondary: "#5c6b63" },
    divider: "#dfe4df",
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: '"Inter", "Helvetica Neue", Arial, sans-serif',
    h1: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 600, letterSpacing: "-0.01em" },
    h2: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 600, letterSpacing: "-0.01em" },
    h3: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 600 },
    h4: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 600 },
    h5: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 600, letterSpacing: "-0.005em" },
    h6: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 600 },
    subtitle1: { fontWeight: 600 },
    subtitle2: { fontWeight: 600 },
    button: { fontWeight: 600, letterSpacing: "0.01em" },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { backgroundColor: "#f6f7f4" },
        "::selection": { backgroundColor: alpha(brand.main, 0.22) },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: { textTransform: "none", borderRadius: 8, paddingInline: 16 },
        contained: {
          "&.MuiButton-containedPrimary:hover": { backgroundColor: brand.dark },
        },
        outlined: { borderWidth: 1.4, "&:hover": { borderWidth: 1.4 } },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 600, borderRadius: 6 },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: "#fdfdfc",
          borderBottom: "1px solid #e4e8e3",
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: "#fbfbf9",
          borderRight: "1px solid #e4e8e3",
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          marginInline: 8,
          marginBottom: 2,
          width: "auto",
          "&.Mui-selected": {
            backgroundColor: alpha(brand.main, 0.1),
            color: brand.dark,
            "& .MuiListItemIcon-root": { color: brand.main },
            "&:hover": { backgroundColor: alpha(brand.main, 0.14) },
          },
        },
      },
    },
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          borderRadius: 12,
          borderColor: "#e4e8e3",
          boxShadow: "0 1px 2px rgba(20, 30, 25, 0.04)",
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        outlined: { borderColor: "#e4e8e3" },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          "& .MuiTableCell-root": {
            fontWeight: 700,
            fontSize: "0.72rem",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            color: "#5c6b63",
            backgroundColor: "#fafaf8",
          },
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: { borderRadius: 8 },
      },
    },
    MuiTableContainer: {
      styleOverrides: {
        root: { borderRadius: 12 },
      },
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AuthProvider>
          <CompanyProvider>
            <App />
          </CompanyProvider>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>,
);
