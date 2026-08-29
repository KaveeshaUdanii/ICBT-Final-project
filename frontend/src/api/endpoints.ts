import { api } from "./client";
import type {
  AuditLog,
  Block,
  ChainVerificationResult,
  ChatReply,
  CsvImportResult,
  DashboardData,
  DelayPredictionResult,
  DelayTrendPoint,
  DemandForecastResult,
  Document,
  DocumentVerifyResult,
  Message,
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
  SupplierRiskHistoryEntry,
  SupplierRiskResult,
  User,
  WarehouseDashboardData,
} from "../types";

function importCsvRequest(url: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return api.post<CsvImportResult>(url, formData);
}

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
  linkSupplier: (id: number, supplier_id: number | null) =>
    api.patch<User>(`/users/${id}/supplier`, null, { params: supplier_id === null ? {} : { supplier_id } }),
};

// --- Suppliers ---------------------------------------------------------------
export const suppliersApi = {
  list: (params?: { q?: string; risk_level?: string }) => api.get<Supplier[]>("/suppliers", { params }),
  get: (id: number) => api.get<Supplier>(`/suppliers/${id}`),
  create: (payload: Partial<Supplier>) => api.post<Supplier>("/suppliers", payload),
  update: (id: number, payload: Partial<Supplier>) => api.put<Supplier>(`/suppliers/${id}`, payload),
  remove: (id: number) => api.delete(`/suppliers/${id}`),
  importCsv: (file: File) => importCsvRequest("/suppliers/import-csv", file),
  updateMyProfile: (payload: { contact_email?: string; contact_phone?: string }) =>
    api.patch<Supplier>("/suppliers/me/profile", payload),
  riskHistory: (id: number) => api.get<SupplierRiskHistoryEntry[]>(`/suppliers/${id}/risk-history`),
};

// --- Messages (per-PO/shipment thread) ----------------------------------------------
export const messagesApi = {
  list: (entity_type: "purchase_order" | "shipment", entity_id: number) =>
    api.get<Message[]>("/messages", { params: { entity_type, entity_id } }),
  create: (entity_type: "purchase_order" | "shipment", entity_id: number, body: string) =>
    api.post<Message>("/messages", { entity_type, entity_id, body }),
};

// --- Documents (blockchain hash-anchored uploads) -----------------------------------
export const documentsApi = {
  list: (entity_type: "purchase_order" | "shipment", entity_id: number) =>
    api.get<Document[]>("/documents", { params: { entity_type, entity_id } }),
  upload: (entity_type: "purchase_order" | "shipment", entity_id: number, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post<Document>("/documents", formData, { params: { entity_type, entity_id } });
  },
  // The download endpoint requires the same Bearer auth as every other request -- a plain
  // <a href> wouldn't carry it -- so this fetches the file as a blob (through the same
  // axios instance/interceptor as everything else) rather than exposing a raw URL.
  download: (id: number) => api.get(`/documents/${id}/download`, { responseType: "blob" }),
  verify: (id: number) => api.get<DocumentVerifyResult>(`/documents/${id}/verify`),
};

// --- Supplier Portal Chatbot (local, no external API) -------------------------------
export const chatbotApi = {
  send: (message: string) => api.post<ChatReply>("/chatbot/message", { message }),
};

// --- Raw Materials -------------------------------------------------------------
export const materialsApi = {
  list: (params?: { needs_reorder?: boolean; supplier_id?: number }) =>
    api.get<RawMaterial[]>("/raw-materials", { params }),
  get: (id: number) => api.get<RawMaterial>(`/raw-materials/${id}`),
  create: (payload: Partial<RawMaterial>) => api.post<RawMaterial>("/raw-materials", payload),
  update: (id: number, payload: Partial<RawMaterial>) => api.put<RawMaterial>(`/raw-materials/${id}`, payload),
  remove: (id: number) => api.delete(`/raw-materials/${id}`),
  importCsv: (file: File) => importCsvRequest("/raw-materials/import-csv", file),
};

// --- Shipments -----------------------------------------------------------------
export const shipmentsApi = {
  list: (params?: { status_filter?: string; supplier_id?: number }) =>
    api.get<Shipment[]>("/shipments", { params }),
  get: (id: number) => api.get<Shipment>(`/shipments/${id}`),
  create: (payload: Partial<Shipment>) => api.post<Shipment>("/shipments", payload),
  update: (id: number, payload: Partial<Shipment>) => api.put<Shipment>(`/shipments/${id}`, payload),
  remove: (id: number) => api.delete(`/shipments/${id}`),
  importCsv: (file: File) => importCsvRequest("/shipments/import-csv", file),
  ship: (id: number, carrier: string, tracking_number: string) =>
    api.post<Shipment>(`/shipments/${id}/ship`, { carrier, tracking_number }),
  confirmDelivery: (id: number) => api.post<Shipment>(`/shipments/${id}/confirm-delivery`),
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
  importCsv: (file: File) => importCsvRequest("/purchase-orders/import-csv", file),
  respond: (id: number, response: "accepted" | "declined", reason = "") =>
    api.post<PurchaseOrder>(`/purchase-orders/${id}/respond`, { response, reason }),
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
