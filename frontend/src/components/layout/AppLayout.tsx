import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { ChatWidget } from "./ChatWidget";

const TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/suppliers": "Supplier Management",
  "/raw-materials": "Raw Material Management",
  "/shipments": "Shipment Management",
  "/purchase-orders": "Purchase Order Management",
  "/ai-risk-center": "AI Risk Prediction Engine",
  "/model-explorer": "Model Explorer",
  "/recommendations": "Recommendation Engine",
  "/blockchain": "Blockchain Explorer",
  "/audit-trail": "Blockchain Audit Trail",
  "/scenarios": "Scenario Simulation",
  "/notifications": "Notification System",
  "/users": "User & Role Management",
};

function titleFor(pathname: string): string {
  if (TITLES[pathname]) return TITLES[pathname];
  const base = "/" + pathname.split("/")[1];
  return TITLES[base] ?? "SupplyChain AI";
}

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="flex min-h-screen">
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <Sidebar mobileOpen={mobileOpen} onNavigate={() => setMobileOpen(false)} />
      <div className="flex-1 min-w-0 flex flex-col lg:pl-72">
        <Topbar onMenuClick={() => setMobileOpen((v) => !v)} title={titleFor(location.pathname)} />
        <main className="flex-1 px-4 sm:px-8 pb-10">
          <Outlet />
        </main>
      </div>
      <ChatWidget />
    </div>
  );
}
