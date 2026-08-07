import { Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { LoginPage } from "./pages/Login";
import { RegisterPage } from "./pages/Register";
import { DashboardPage } from "./pages/Dashboard";
import { SuppliersPage } from "./pages/Suppliers";
import { RawMaterialsPage } from "./pages/RawMaterials";
import { ShipmentsPage } from "./pages/Shipments";
import { PurchaseOrdersPage } from "./pages/PurchaseOrders";
import { AIRiskCenterPage } from "./pages/AIRiskCenter";
import { RecommendationsPage } from "./pages/Recommendations";
import { BlockchainExplorerPage } from "./pages/BlockchainExplorer";
import { AuditTrailPage } from "./pages/AuditTrail";
import { ScenarioSimulationPage } from "./pages/ScenarioSimulation";
import { NotificationsPage } from "./pages/Notifications";
import { UserManagementPage } from "./pages/UserManagement";
import { NotFoundPage } from "./pages/NotFound";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route
          path="/suppliers"
          element={
            <ProtectedRoute roles={["admin", "supply_chain_manager"]}>
              <SuppliersPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/raw-materials"
          element={
            <ProtectedRoute roles={["admin", "supply_chain_manager", "warehouse_manager"]}>
              <RawMaterialsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/shipments"
          element={
            <ProtectedRoute roles={["admin", "supply_chain_manager", "warehouse_manager", "supplier"]}>
              <ShipmentsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/purchase-orders"
          element={
            <ProtectedRoute roles={["admin", "supply_chain_manager", "supplier"]}>
              <PurchaseOrdersPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/ai-risk-center"
          element={
            <ProtectedRoute roles={["admin", "supply_chain_manager"]}>
              <AIRiskCenterPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/recommendations"
          element={
            <ProtectedRoute roles={["admin", "supply_chain_manager"]}>
              <RecommendationsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/blockchain"
          element={
            <ProtectedRoute roles={["admin", "supply_chain_manager"]}>
              <BlockchainExplorerPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/audit-trail"
          element={
            <ProtectedRoute roles={["admin", "supply_chain_manager"]}>
              <AuditTrailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/scenarios"
          element={
            <ProtectedRoute roles={["admin", "supply_chain_manager"]}>
              <ScenarioSimulationPage />
            </ProtectedRoute>
          }
        />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route
          path="/users"
          element={
            <ProtectedRoute roles={["admin"]}>
              <UserManagementPage />
            </ProtectedRoute>
          }
        />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
