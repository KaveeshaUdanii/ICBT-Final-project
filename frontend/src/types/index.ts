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
  risk_score: number;
  risk_level: RiskLevel;
  last_scored_at: string | null;
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
  predicted_delay_days: number | null;
  delay_probability: number | null;
  is_anomaly: boolean;
  anomaly_score: number | null;
  actual_delay_days: number | null;
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
  status: PurchaseOrderStatus;
  approved_by: number | null;
  risk_flag: boolean;
  risk_notes: string;
  total_value: number;
  created_at: string;
  updated_at: string;
}

export interface FeatureContribution {
  feature: string;
  value: number;
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
    avg_lead_time_days: number;
  } | null;
  shipments: { total: number; by_status: Record<string, number> };
  purchase_orders: { total: number; by_status: Record<string, number> };
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
