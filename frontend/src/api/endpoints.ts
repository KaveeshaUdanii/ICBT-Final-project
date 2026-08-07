import { api } from "./client";
import type {
  AuditLog,
  Block,
  ChainVerificationResult,
  DashboardData,
  DelayPredictionResult,
  DelayTrendPoint,
  DemandForecastResult,
  ModelPerformanceReport,
  MyDashboardData,
  Notification,
  PurchaseOrder,
  RawMaterial,
  Recommendation,
  RiskHeatmapCell,
  RiskPrediction,
  ScenarioResult,
  ScenarioType,
  Shipment,
  SmartContractRule,
  StockoutRiskResult,
  Supplier,
  SupplierRiskResult,
  User,
  WarehouseDashboardData,
} from "../types";

// --- Auth & Users -----------------------------------------------------------
export const authApi = {
  login: (email: string, password: string) =>
    api.post<{ access_token: string; user: User }>("/auth/login", { email, password }),
  register: (payload: { name: string; email: string; password: string; role: string }) =>
    api.post<{ access_token: string; user: User }>("/auth/register", payload),
  me: () => api.get<User>("/auth/me"),
};

export const usersApi = {
  list: () => api.get<User[]>("/users"),
  updateRole: (id: number, role: string) => api.patch<User>(`/users/${id}/role`, null, { params: { role } }),
  toggleActive: (id: number, is_active: boolean) =>
    api.patch<User>(`/users/${id}/status`, null, { params: { is_active } }),
};

// --- Suppliers ---------------------------------------------------------------
export const suppliersApi = {
  list: (params?: { q?: string; risk_level?: string }) => api.get<Supplier[]>("/suppliers", { params }),
  get: (id: number) => api.get<Supplier>(`/suppliers/${id}`),
  create: (payload: Partial<Supplier>) => api.post<Supplier>("/suppliers", payload),
  update: (id: number, payload: Partial<Supplier>) => api.put<Supplier>(`/suppliers/${id}`, payload),
  remove: (id: number) => api.delete(`/suppliers/${id}`),
};

// --- Raw Materials -------------------------------------------------------------
export const materialsApi = {
  list: (params?: { needs_reorder?: boolean; supplier_id?: number }) =>
    api.get<RawMaterial[]>("/raw-materials", { params }),
  get: (id: number) => api.get<RawMaterial>(`/raw-materials/${id}`),
  create: (payload: Partial<RawMaterial>) => api.post<RawMaterial>("/raw-materials", payload),
  update: (id: number, payload: Partial<RawMaterial>) => api.put<RawMaterial>(`/raw-materials/${id}`, payload),
  remove: (id: number) => api.delete(`/raw-materials/${id}`),
};

// --- Shipments -----------------------------------------------------------------
export const shipmentsApi = {
  list: (params?: { status_filter?: string; supplier_id?: number }) =>
    api.get<Shipment[]>("/shipments", { params }),
  get: (id: number) => api.get<Shipment>(`/shipments/${id}`),
  create: (payload: Partial<Shipment>) => api.post<Shipment>("/shipments", payload),
  update: (id: number, payload: Partial<Shipment>) => api.put<Shipment>(`/shipments/${id}`, payload),
  remove: (id: number) => api.delete(`/shipments/${id}`),
};

// --- Purchase Orders -------------------------------------------------------------
export const purchaseOrdersApi = {
  list: (params?: { status_filter?: string; supplier_id?: number }) =>
    api.get<PurchaseOrder[]>("/purchase-orders", { params }),
  get: (id: number) => api.get<PurchaseOrder>(`/purchase-orders/${id}`),
  create: (payload: Partial<PurchaseOrder>) => api.post<PurchaseOrder>("/purchase-orders", payload),
  update: (id: number, payload: Partial<PurchaseOrder>) => api.put<PurchaseOrder>(`/purchase-orders/${id}`, payload),
  approve: (id: number) => api.post<PurchaseOrder>(`/purchase-orders/${id}/approve`),
  reject: (id: number, reason: string) =>
    api.post<PurchaseOrder>(`/purchase-orders/${id}/reject`, null, { params: { reason } }),
  remove: (id: number) => api.delete(`/purchase-orders/${id}`),
};

// --- AI Risk Engine & XAI ----------------------------------------------------
export const aiApi = {
  scoreSupplier: (id: number) => api.post<SupplierRiskResult>(`/ai/suppliers/${id}/score`),
  scoreAllSuppliers: () => api.post<SupplierRiskResult[]>("/ai/suppliers/score-all"),
  predictShipment: (id: number) => api.post<DelayPredictionResult>(`/ai/shipments/${id}/predict`),
  predictAllShipments: () => api.post<DelayPredictionResult[]>("/ai/shipments/predict-all"),
  predictions: (params?: { entity_type?: string; entity_id?: number; model_name?: string }) =>
    api.get<RiskPrediction[]>("/ai/predictions", { params }),
  modelPerformance: () => api.get<ModelPerformanceReport>("/ai/model-performance"),
  forecastDemand: (materialId: number) =>
    api.post<DemandForecastResult>(`/ai/raw-materials/${materialId}/forecast-demand`),
  forecastAllDemand: () => api.post<DemandForecastResult[]>("/ai/raw-materials/forecast-all"),
  predictStockout: (materialId: number) =>
    api.post<StockoutRiskResult>(`/ai/raw-materials/${materialId}/predict-stockout`),
  predictAllStockout: () => api.post<StockoutRiskResult[]>("/ai/raw-materials/predict-stockout-all"),
};

// --- Recommendations -----------------------------------------------------------
export const recommendationsApi = {
  list: (params?: { include_dismissed?: boolean; entity_type?: string }) =>
    api.get<Recommendation[]>("/recommendations", { params }),
  dismiss: (id: number) => api.post<Recommendation>(`/recommendations/${id}/dismiss`),
};

// --- Blockchain & Audit ----------------------------------------------------------
export const blockchainApi = {
  blocks: (params?: { limit?: number; event_type?: string }) => api.get<Block[]>("/blockchain/blocks", { params }),
  block: (index: number) => api.get<Block>(`/blockchain/blocks/${index}`),
  verify: () => api.get<ChainVerificationResult>("/blockchain/verify"),
  rules: () => api.get<SmartContractRule[]>("/blockchain/rules"),
};

export const auditApi = {
  list: (params?: { entity_type?: string; entity_id?: number; limit?: number }) =>
    api.get<AuditLog[]>("/audit-logs", { params }),
};

// --- Notifications -----------------------------------------------------------------
export const notificationsApi = {
  list: (params?: { unread_only?: boolean; limit?: number }) => api.get<Notification[]>("/notifications", { params }),
  unreadCount: () => api.get<{ unread_count: number }>("/notifications/unread-count"),
  markRead: (id: number) => api.post<Notification>(`/notifications/${id}/read`),
  markAllRead: () => api.post<{ marked_read: number }>("/notifications/read-all"),
};

// --- Scenario Simulation -------------------------------------------------------------
export const scenariosApi = {
  simulate: (payload: { name: string; scenario_type: ScenarioType; input_params: Record<string, unknown> }) =>
    api.post<ScenarioResult>("/scenarios/simulate", payload),
  list: (limit?: number) => api.get<ScenarioResult[]>("/scenarios", { params: { limit } }),
};

// --- Analytics & Dashboard -------------------------------------------------------------
export const analyticsApi = {
  dashboard: () => api.get<DashboardData>("/analytics/dashboard"),
  riskHeatmap: () => api.get<{ cells: RiskHeatmapCell[] }>("/analytics/risk-heatmap"),
  delayTrend: () => api.get<{ points: DelayTrendPoint[] }>("/analytics/delay-trend"),
  warehouseDashboard: () => api.get<WarehouseDashboardData>("/analytics/warehouse-dashboard"),
  myDashboard: () => api.get<MyDashboardData>("/analytics/my-dashboard"),
};
