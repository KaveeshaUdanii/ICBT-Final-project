import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    SUPPLY_CHAIN_MANAGER = "supply_chain_manager"
    WAREHOUSE_MANAGER = "warehouse_manager"
    SUPPLIER = "supplier"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ShipmentStatus(str, enum.Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class PurchaseOrderStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class NotificationSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class MaterialCategory(str, enum.Enum):
    FABRIC = "fabric"
    BUTTONS = "buttons"
    ZIPPERS = "zippers"
    THREAD = "thread"
    PACKAGING = "packaging"
    TRIMS = "trims"
    DYE_CHEMICALS = "dye_chemicals"


class ScenarioType(str, enum.Enum):
    SUPPLIER_FAILURE = "supplier_failure"
    DEMAND_SPIKE = "demand_spike"
    LEAD_TIME_INCREASE = "lead_time_increase"
    RAW_MATERIAL_SHORTAGE = "raw_material_shortage"
