export type UserRole = "admin" | "supply_chain_manager" | "warehouse_manager" | "supplier";
export type RiskLevel = "low" | "medium" | "high";
export type ShipmentStatus = "pending" | "in_transit" | "delivered" | "delayed" | "cancelled";
export type PurchaseOrderStatus = "draft" | "pending_approval" | "approved" | "rejected" | "completed";
export type NotificationSeverity = "info" | "warning" | "critical";
export type MaterialCategory =
  | "fabric"
  | "buttons"
  | "zippers"
  | "thread"
  | "packaging"
  | "trims"
  | "dye_chemicals";
export type ScenarioType =
  | "supplier_failure"
  | "demand_spike"
  | "lead_time_increase"
  | "raw_material_shortage";

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  supplier_id: number | null;
}

export interface Supplier {
  id: number;
  name: string;
  contact_email: string;
  contact_phone: string;
  country: string;
  category: string;
  on_time_delivery_rate: number;
  defect_rate: number;
  cancellation_rate: number;
  avg_lead_time_days: number;
  order_volume_last_year: number;
  // Absent (not just null) when fetched by a Supplier-portal account viewing its own record --
  // the backend never sends the AI Risk Engine's internal classification of a supplier back
  // to that supplier. See SupplierExternalRead in app/schemas/supplier.py.
  risk_score?: number;
  risk_level?: RiskLevel;
  last_scored_at?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RawMaterial {
  id: number;
  name: string;
  category: MaterialCategory;
  unit: string;
  quantity_on_hand: number;
  reorder_level: number;
  unit_cost: number;
  lead_time_days: number;
  supplier_id: number;
  needs_reorder: boolean;
  predicted_demand_next_30_days: number | null;
  stockout_risk_probability: number | null;
  last_forecasted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Shipment {
  id: number;
  shipment_code: string;
  supplier_id: number;
  purchase_order_id: number | null;
  origin: string;
  destination: string;
  quantity: number;
  order_date: string;
  expected_delivery_date: string;
  actual_delivery_date: string | null;
  status: ShipmentStatus;
  // Absent for a Supplier-portal account -- the AI Delay Prediction / Anomaly Detection
  // models' outputs are an internal risk signal, never returned to the supplier being
  // scored. See ShipmentExternalRead in app/schemas/shipment.py.
  predicted_delay_days?: number | null;
  delay_probability?: number | null;
  is_anomaly?: boolean;
  anomaly_score?: number | null;
  actual_delay_days: number | null;
  carrier: string;
  tracking_number: string;
  supplier_confirmed_delivery: boolean;
  supplier_confirmed_delivery_at: string | null;
  staff_confirmed_delivery: boolean;
  staff_confirmed_delivery_at: string | null;
  data_entry_flag: boolean;
  data_entry_warning: string;
  created_at: string;
  updated_at: string;
}

export interface PurchaseOrder {
  id: number;
  po_number: string;
  supplier_id: number;
  raw_material_id: number;
  quantity: number;
  unit_price: number;
  order_date: string;
  expected_delivery_date: string;
  // Denormalized server-side so every caller (including a Supplier account, which has no
  // access to the Raw Materials catalog endpoint) can render the material name without a
  // second request.
  raw_material_name: string;
  status: PurchaseOrderStatus;
  // Absent for a Supplier-portal account -- these are the smart-contract engine's internal
  // auto-flagging notes (which name the supplier's own risk score) and an internal user id.
  // See PurchaseOrderExternalRead in app/schemas/purchase_order.py.
  approved_by?: number | null;
  risk_flag?: boolean;
  risk_notes?: string;
  total_value: number;
  penalty_rate_pct: number;
  penalty_exposure: number | null;
  supplier_response: "pending" | "accepted" | "declined";
  decline_reason: string;
  data_entry_flag: boolean;
  data_entry_warning: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  entity_type: "purchase_order" | "shipment";
  entity_id: number;
  sender_user_id: number;
  sender_name: string;
  sender_role: string;
  body: string;
  created_at: string;
}

export interface Document {
  id: number;
  entity_type: "purchase_order" | "shipment";
  entity_id: number;
  filename: string;
  content_type: string;
  file_size: number;
  sha256_hash: string;
  uploaded_by_name: string;
  block_id: number | null;
  created_at: string;
}

export interface DocumentVerifyResult {
  document_id: number;
  is_verified: boolean;
  sha256_hash: string;
  message: string;
}

export interface SupplierRiskHistoryEntry {
  risk_score: number;
  risk_level: string | null;
  scored_at: string;
}

export interface ChatReply {
  reply: string;
  intent: string;
  confidence: number;
}

export interface FeatureContribution {
  feature: string;
  label: string;
  value: number;
  display_value: string;
  typical_display_value: string;
  contribution: number;
  direction: "increases_risk" | "decreases_risk";
  explanation: string;
}

export interface ExplanationResult {
  model_name: string;
  base_value: number;
  prediction: number;
  top_factors: FeatureContribution[];
  plain_language_summary: string;
}

export interface SupplierRiskResult {
  supplier_id: number;
  risk_score: number;
  risk_level: string;
  explanation: ExplanationResult;
}

export interface DelayPredictionResult {
  shipment_id: number;
  predicted_delay_days: number;
  delay_probability: number;
  is_anomaly: boolean;
  anomaly_score: number;
  explanation: ExplanationResult;
}

export interface DemandForecastResult {
  raw_material_id: number;
  predicted_demand_next_30_days: number;
  explanation: ExplanationResult;
}

export interface StockoutRiskResult {
  raw_material_id: number;
  stockout_risk_probability: number;
  predicted_demand_next_30_days: number;
  explanation: ExplanationResult;
}

export interface RiskPrediction {
  id: number;
  entity_type: string;
  entity_id: number;
  model_name: string;
  prediction_value: number;
  probability: number | null;
  explanation: Record<string, unknown>;
  created_at: string;
}

export interface Recommendation {
  id: number;
  entity_type: string;
  entity_id: number;
  recommendation_text: string;
  recommended_supplier_id: number | null;
  confidence: number;
  is_dismissed: boolean;
  created_at: string;
}

export interface Notification {
  id: number;
  user_id: number | null;
  title: string;
  message: string;
  severity: NotificationSeverity;
  related_entity_type: string | null;
  related_entity_id: number | null;
  is_read: boolean;
  source: string;
  created_at: string;
}

export interface Block {
  id: number;
  block_index: number;
  timestamp: string;
  event_type: string;
  payload: Record<string, unknown>;
  performed_by: string;
  previous_hash: string;
  nonce: number;
  hash: string;
}

export interface ChainVerificationResult {
  is_valid: boolean;
  total_blocks: number;
  broken_at_index: number | null;
  message: string;
}

export interface SmartContractRule {
  id: number;
  name: string;
  trigger_event: string;
  condition_description: string;
  action_description: string;
  is_active: boolean;
  times_triggered: number;
  last_triggered_at: string | null;
}

export interface AuditLog {
  id: number;
  action: string;
  entity_type: string;
  entity_id: number | null;
  performed_by: string;
  details: Record<string, unknown>;
  block_id: number | null;
  created_at: string;
}

export interface ScenarioResult {
  id: number;
  name: string;
  scenario_type: ScenarioType;
  input_params: Record<string, unknown>;
  result: Record<string, unknown>;
  created_by: string;
  created_at: string;
}

export interface DashboardData {
  totals: {
    suppliers: number;
    raw_materials: number;
    shipments: number;
    purchase_orders: number;
  };
  supplier_risk: {
    low: number;
    medium: number;
    high: number;
    average_risk_score: number;
  };
  shipments: {
    by_status: Record<string, number>;
    average_delay_probability_pct: number;
    anomaly_count: number;
  };
  purchase_orders: {
    by_status: Record<string, number>;
    flagged_high_risk: number;
    pending_approval: number;
  };
  inventory: {
    materials_needing_reorder: number;
  };
  blockchain: {
    total_blocks: number;
    chain_valid: boolean;
  };
  notifications: {
    unread_count: number;
  };
}

export interface WarehouseDashboardData {
  totals: {
    materials: number;
    needing_reorder: number;
    incoming_shipments: number;
  };
  materials_by_category: Record<string, number>;
  reorder_list: {
    id: number;
    name: string;
    unit: string;
    quantity_on_hand: number;
    reorder_level: number;
  }[];
}

export interface MyDashboardData {
  supplier: {
    id: number;
    name: string;
    on_time_delivery_rate: number;
    defect_rate: number;
    cancellation_rate: number;
    avg_lead_time_days: number;
    order_volume_last_year: number;
    contact_email: string;
    contact_phone: string;
  } | null;
  shipments: { total: number; by_status: Record<string, number> };
  purchase_orders: { total: number; by_status: Record<string, number>; total_value: number };
  upcoming_shipments: {
    shipment_code: string;
    status: ShipmentStatus;
    expected_delivery_date: string;
    quantity: number;
  }[];
  recent_purchase_orders: {
    po_number: string;
    status: PurchaseOrderStatus;
    order_date: string;
    expected_delivery_date: string;
    total_value: number;
  }[];
  pending_response_purchase_orders: {
    id: number;
    po_number: string;
    status: PurchaseOrderStatus;
    expected_delivery_date: string;
    total_value: number;
  }[];
  performance_trend: {
    month: string;
    on_time_rate: number;
    average_delay_days: number;
    shipment_count: number;
  }[];
  materials_demand_forecast: {
    total_next_30_days: number;
    by_material: { name: string; unit: string; predicted_demand_next_30_days: number }[];
  };
}

export interface RiskHeatmapCell {
  category: string;
  country: string;
  average_risk_score: number;
  supplier_count: number;
}

export interface DelayTrendPoint {
  month: string;
  average_predicted_delay_days: number;
  shipment_count: number;
}

export interface ModelPerformanceReport {
  generated_at: string;
  dataset: string;
  supplier_risk_scoring_model: Record<string, unknown>;
  delay_prediction_model: Record<string, unknown>;
  anomaly_detection_model: Record<string, unknown>;
}

export interface CsvImportResult {
  imported: number;
  failed: number;
  errors: { row: number; error: string }[];
}
