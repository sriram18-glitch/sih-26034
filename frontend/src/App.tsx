import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import { AppModeProvider } from "./store/appMode";
import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import Scan from "./pages/Scan";
import Result from "./pages/Result";
import Details from "./pages/Details";
import History from "./pages/History";
import Product from "./pages/Product";
import Rules from "./pages/Rules";
import Reports from "./pages/Reports";
import Audit from "./pages/Audit";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <BrowserRouter>
      <AppModeProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/scan" element={<Scan />} />
          <Route path="/inspections/:id/result" element={<Result />} />
          <Route path="/inspections/:id" element={<Details />} />
          <Route path="/product/:id" element={<Product />} />
          <Route path="/history" element={<History />} />
          <Route path="/rules" element={<Rules />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/audit" element={<Audit />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </Layout>
      </AppModeProvider>
    </BrowserRouter>
  );
}
