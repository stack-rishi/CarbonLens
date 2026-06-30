import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./store/useAuthStore";
import { MainLayout } from "./components/MainLayout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Suppliers from "./pages/Suppliers";
import Emissions from "./pages/Emissions";
import SupplyChain from "./pages/SupplyChain";
import Reports from "./pages/Reports";
import Chat from "./pages/Chat";
import Onboarding from "./pages/Onboarding";
import Compliance from "./pages/Compliance";
import { Toaster } from "./components/ui/toaster";
import { ErrorBoundary } from "./components/ErrorBoundary";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <MainLayout><ErrorBoundary>{children}</ErrorBoundary></MainLayout>;
}

export default function App() {
  const token = useAuthStore((s) => s.token);

  return (
    <BrowserRouter>
      <Routes>
        {/* Root redirect */}
        <Route
          path="/"
          element={token ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />}
        />

        {/* Public */}
        <Route
          path="/login"
          element={token ? <Navigate to="/dashboard" replace /> : <Login />}
        />

        {/* Onboarding — protected but without full MainLayout sidebar */}
        <Route
          path="/onboarding"
          element={
            token ? <Onboarding /> : <Navigate to="/login" replace />
          }
        />

        {/* Protected pages */}
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/compliance" element={<ProtectedRoute><Compliance /></ProtectedRoute>} />
        <Route path="/supply-chain" element={<ProtectedRoute><SupplyChain /></ProtectedRoute>} />
        <Route path="/emissions" element={<ProtectedRoute><Emissions /></ProtectedRoute>} />
        <Route path="/suppliers" element={<ProtectedRoute><Suppliers /></ProtectedRoute>} />
        <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
        <Route path="/chat" element={<ProtectedRoute><Chat /></ProtectedRoute>} />

        {/* Catch-all */}
        <Route path="*" element={<Navigate to={token ? "/dashboard" : "/login"} replace />} />
      </Routes>
      <Toaster />
    </BrowserRouter>
  );
}
