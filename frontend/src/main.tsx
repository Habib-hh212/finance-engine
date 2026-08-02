import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.tsx";
import { CompanyProvider } from "./context/CompanyContext";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#2f5d50" },
    background: { default: "#f5f6f4" },
  },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: '"Inter", "Helvetica Neue", Arial, sans-serif',
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <CompanyProvider>
          <App />
        </CompanyProvider>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>,
);
