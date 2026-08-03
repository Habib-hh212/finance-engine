import { Suspense, lazy } from "react";
import { Route, Routes } from "react-router-dom";
import { CircularProgress, Box } from "@mui/material";
import { AuthGate } from "./components/AuthGate";
import { CompanyGate } from "./components/CompanyGate";
import { Layout } from "./components/Layout";

const DashboardPage = lazy(() => import("./pages/DashboardPage").then((m) => ({ default: m.DashboardPage })));
const SalesForecastPage = lazy(() => import("./pages/SalesForecastPage").then((m) => ({ default: m.SalesForecastPage })));
const BudgetPlanningPage = lazy(() => import("./pages/BudgetPlanningPage").then((m) => ({ default: m.BudgetPlanningPage })));
const CashFlowPage = lazy(() => import("./pages/CashFlowPage").then((m) => ({ default: m.CashFlowPage })));
const ControllingPage = lazy(() => import("./pages/ControllingPage").then((m) => ({ default: m.ControllingPage })));
const ProfitabilityPage = lazy(() => import("./pages/ProfitabilityPage").then((m) => ({ default: m.ProfitabilityPage })));
const FinancialStatementsPage = lazy(() =>
  import("./pages/FinancialStatementsPage").then((m) => ({ default: m.FinancialStatementsPage })),
);

function PageFallback() {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", pt: 8 }}>
      <CircularProgress size={28} />
    </Box>
  );
}

function App() {
  return (
    <AuthGate>
      <CompanyGate>
        <Layout>
          <Suspense fallback={<PageFallback />}>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/sales-forecast" element={<SalesForecastPage />} />
              <Route path="/budgets" element={<BudgetPlanningPage />} />
              <Route path="/cash-flow" element={<CashFlowPage />} />
              <Route path="/controlling" element={<ControllingPage />} />
              <Route path="/profitability" element={<ProfitabilityPage />} />
              <Route path="/financial-statements" element={<FinancialStatementsPage />} />
            </Routes>
          </Suspense>
        </Layout>
      </CompanyGate>
    </AuthGate>
  );
}

export default App;
