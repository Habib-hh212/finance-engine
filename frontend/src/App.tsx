import { Suspense, lazy } from "react";
import { Route, Routes } from "react-router-dom";
import { CircularProgress, Box } from "@mui/material";
import { AuthGate } from "./components/AuthGate";
import { CompanyGate } from "./components/CompanyGate";
import { Layout } from "./components/Layout";
import { ResetPasswordPage } from "./pages/ResetPasswordPage";

const DashboardPage = lazy(() => import("./pages/DashboardPage").then((m) => ({ default: m.DashboardPage })));
const SalesForecastPage = lazy(() => import("./pages/SalesForecastPage").then((m) => ({ default: m.SalesForecastPage })));
const BudgetPlanningPage = lazy(() => import("./pages/BudgetPlanningPage").then((m) => ({ default: m.BudgetPlanningPage })));
const CashFlowPage = lazy(() => import("./pages/CashFlowPage").then((m) => ({ default: m.CashFlowPage })));
const ControllingPage = lazy(() => import("./pages/ControllingPage").then((m) => ({ default: m.ControllingPage })));
const ProfitabilityPage = lazy(() => import("./pages/ProfitabilityPage").then((m) => ({ default: m.ProfitabilityPage })));
const FinancialStatementsPage = lazy(() =>
  import("./pages/FinancialStatementsPage").then((m) => ({ default: m.FinancialStatementsPage })),
);
const StandardCostingPage = lazy(() =>
  import("./pages/StandardCostingPage").then((m) => ({ default: m.StandardCostingPage })),
);
const ScenarioPlanningPage = lazy(() =>
  import("./pages/ScenarioPlanningPage").then((m) => ({ default: m.ScenarioPlanningPage })),
);
const ContactPage = lazy(() => import("./pages/ContactPage").then((m) => ({ default: m.ContactPage })));
const AuditTrailPage = lazy(() => import("./pages/AuditTrailPage").then((m) => ({ default: m.AuditTrailPage })));
const FxScenarioPage = lazy(() => import("./pages/FxScenarioPage").then((m) => ({ default: m.FxScenarioPage })));
const BookkeepingPage = lazy(() => import("./pages/BookkeepingPage").then((m) => ({ default: m.BookkeepingPage })));
const ChartOfAccountsPage = lazy(() =>
  import("./pages/ChartOfAccountsPage").then((m) => ({ default: m.ChartOfAccountsPage })),
);
const TaxCodesPage = lazy(() => import("./pages/TaxCodesPage").then((m) => ({ default: m.TaxCodesPage })));
const TdsPage = lazy(() => import("./pages/TdsPage").then((m) => ({ default: m.TdsPage })));
const FixedAssetsPage = lazy(() => import("./pages/FixedAssetsPage").then((m) => ({ default: m.FixedAssetsPage })));
const PeriodClosePage = lazy(() => import("./pages/PeriodClosePage").then((m) => ({ default: m.PeriodClosePage })));
const ReceivablesPayablesPage = lazy(() =>
  import("./pages/ReceivablesPayablesPage").then((m) => ({ default: m.ReceivablesPayablesPage })),
);
const BankReconciliationPage = lazy(() =>
  import("./pages/BankReconciliationPage").then((m) => ({ default: m.BankReconciliationPage })),
);

function PageFallback() {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", pt: 8 }}>
      <CircularProgress size={28} />
    </Box>
  );
}

function AuthenticatedApp() {
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
              <Route path="/standard-costing" element={<StandardCostingPage />} />
              <Route path="/scenarios" element={<ScenarioPlanningPage />} />
              <Route path="/contact" element={<ContactPage />} />
              <Route path="/audit-trail" element={<AuditTrailPage />} />
              <Route path="/fx-scenario" element={<FxScenarioPage />} />
              <Route path="/general-ledger" element={<BookkeepingPage />} />
              <Route path="/chart-of-accounts" element={<ChartOfAccountsPage />} />
              <Route path="/tax-codes" element={<TaxCodesPage />} />
              <Route path="/tds" element={<TdsPage />} />
              <Route path="/fixed-assets" element={<FixedAssetsPage />} />
              <Route path="/period-close" element={<PeriodClosePage />} />
              <Route path="/receivables-payables" element={<ReceivablesPayablesPage />} />
              <Route path="/bank-reconciliation" element={<BankReconciliationPage />} />
            </Routes>
          </Suspense>
        </Layout>
      </CompanyGate>
    </AuthGate>
  );
}

function App() {
  return (
    <Routes>
      {/* Reached from an emailed link while logged out -- must stay outside
          AuthGate, which would otherwise hide it behind the login form. */}
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/*" element={<AuthenticatedApp />} />
    </Routes>
  );
}

export default App;
