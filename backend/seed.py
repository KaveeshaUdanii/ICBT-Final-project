"""
Populates the database with a realistic demo dataset spanning every module: users of
each role, suppliers with varied risk profiles, raw materials, purchase orders and
shipments (past and upcoming), then runs the real AI models over them so the dashboard,
blockchain explorer, and recommendation feed all have real content the first time the
app is opened.

Run from the backend/ directory:  python3 seed.py
"""

import random
import re
from datetime import date, timedelta

from faker import Faker

from app.ai import predict as ai_predict
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import *  # noqa: F401,F403
from app.models.enums import PurchaseOrderStatus, ShipmentStatus, UserRole
from app.models.purchase_order import PurchaseOrder
from app.models.raw_material import RawMaterial
from app.models.shipment import Shipment
from app.models.supplier import Supplier
from app.models.user import User
from app.routers.ai_risk import _predict_shipment, _score_supplier  # reuse real scoring logic
from app.services import recommendation_service, smart_contract_service
from app.services.smart_contract_service import ensure_rules_seeded

fake = Faker()
Faker.seed(99)
random.seed(99)

SUPPLIER_SEEDS = [
    # (name, category, country, on_time, defect, cancel, lead_time, volume)  -- deliberately spans low -> high risk
    ("Colombo Textile Mills", "fabric", "Sri Lanka", 0.96, 0.015, 0.01, 12, 180),
    ("Lanka Trims & Accessories", "trims", "Sri Lanka", 0.94, 0.02, 0.015, 10, 140),
    ("Ceylon Dye Works", "dye_chemicals", "Sri Lanka", 0.93, 0.025, 0.02, 14, 90),
    ("Guangzhou Zipper Co.", "zippers", "China", 0.90, 0.03, 0.02, 18, 220),
    ("Shenzhen Button Industries", "buttons", "China", 0.88, 0.035, 0.03, 20, 160),
    ("Dhaka Thread Works", "thread", "Bangladesh", 0.85, 0.04, 0.035, 22, 110),
    ("Mumbai Fabric Exports", "fabric", "India", 0.82, 0.05, 0.04, 25, 130),
    ("Hanoi Packaging Solutions", "packaging", "Vietnam", 0.91, 0.02, 0.015, 15, 95),
    ("Jakarta Trims Supply", "trims", "Indonesia", 0.80, 0.05, 0.045, 28, 70),
    ("Karachi Cotton Traders", "fabric", "Pakistan", 0.74, 0.07, 0.06, 32, 60),
    ("Kandy Zipper & Fasteners", "zippers", "Sri Lanka", 0.89, 0.03, 0.02, 16, 100),
    ("Chittagong Dye Supplies", "dye_chemicals", "Bangladesh", 0.68, 0.09, 0.08, 35, 45),
    ("Surat Thread Mills", "thread", "India", 0.71, 0.08, 0.07, 30, 55),
    ("Ho Chi Minh Packaging Co.", "packaging", "Vietnam", 0.60, 0.11, 0.10, 40, 35),
    ("Faisalabad Button Works", "buttons", "Pakistan", 0.58, 0.13, 0.12, 45, 30),
    ("Galle Fabric Exporters", "fabric", "Sri Lanka", 0.63, 0.10, 0.09, 38, 40),
    ("Bandung Trims International", "trims", "Indonesia", 0.55, 0.14, 0.13, 42, 25),
    ("Rajshahi Zipper Traders", "zippers", "Bangladesh", 0.52, 0.15, 0.14, 48, 20),
]

MATERIAL_NAMES = {
    "fabric": ["Cotton Fabric Roll", "Polyester Blend Fabric", "Denim Fabric Roll"],
    "trims": ["Woven Label Trim", "Elastic Waistband Trim"],
    "dye_chemicals": ["Reactive Dye Batch", "Fabric Softener Chemical"],
    "zippers": ["Metal Zipper Set", "Nylon Coil Zipper"],
    "buttons": ["Plastic Button Pack", "Metal Snap Button Pack"],
    "thread": ["Polyester Sewing Thread", "Cotton Sewing Thread"],
    "packaging": ["Poly Bag Packaging", "Corrugated Carton Box"],
}


def _email_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())[:20]


def seed_users(db) -> None:
    demo_users = [
        ("Admin User", "admin@supplychain.ai", "admin123", UserRole.ADMIN),
        ("Nadeesha Perera", "manager@supplychain.ai", "manager123", UserRole.SUPPLY_CHAIN_MANAGER),
        ("Kasun Silva", "warehouse@supplychain.ai", "warehouse123", UserRole.WAREHOUSE_MANAGER),
    ]
    for name, email, password, role in demo_users:
        if db.query(User).filter(User.email == email).first():
            continue
        db.add(User(name=name, email=email, password_hash=hash_password(password), role=role))
    db.commit()
    print(f"Seeded {len(demo_users)} demo users (see README for credentials).")


def seed_supplier_portal_user(db, suppliers: list[Supplier]) -> None:
    """The Supplier role is an external-party login, so unlike the internal roles above
    it must be linked to exactly one Supplier record -- that link is what the API uses
    everywhere to make sure this account only ever sees its own data."""
    email = "supplier@supplychain.ai"
    if db.query(User).filter(User.email == email).first():
        return
    linked_supplier = next((s for s in suppliers if s.name == "Colombo Textile Mills"), suppliers[0])
    db.add(
        User(
            name=f"{linked_supplier.name} Portal User",
            email=email,
            password_hash=hash_password("supplier123"),
            role=UserRole.SUPPLIER,
            supplier_id=linked_supplier.id,
        )
    )
    db.commit()
    print(f"Seeded supplier portal user linked to '{linked_supplier.name}'.")


def seed_suppliers(db) -> list[Supplier]:
    suppliers = []
    for name, category, country, on_time, defect, cancel, lead_time, volume in SUPPLIER_SEEDS:
        existing = db.query(Supplier).filter(Supplier.name == name).first()
        if existing:
            suppliers.append(existing)
            continue
        supplier = Supplier(
            name=name,
            contact_email=f"contact@{_email_slug(name)}.com",
            contact_phone=fake.phone_number()[:20],
            country=country,
            category=category,
            on_time_delivery_rate=on_time,
            defect_rate=defect,
            cancellation_rate=cancel,
            avg_lead_time_days=lead_time,
            order_volume_last_year=volume,
        )
        db.add(supplier)
        suppliers.append(supplier)
    db.commit()
    for s in suppliers:
        db.refresh(s)
    print(f"Seeded {len(suppliers)} suppliers.")
    return suppliers


def seed_materials(db, suppliers: list[Supplier]) -> list[RawMaterial]:
    materials = []
    for supplier in suppliers:
        names = MATERIAL_NAMES.get(supplier.category, ["Generic Material"])
        for name in names:
            existing = db.query(RawMaterial).filter(
                RawMaterial.name == name, RawMaterial.supplier_id == supplier.id
            ).first()
            if existing:
                materials.append(existing)
                continue
            on_hand = random.uniform(20, 600)
            reorder = random.uniform(80, 250)
            material = RawMaterial(
                name=name,
                category=supplier.category,
                unit=random.choice(["kg", "meters", "units", "rolls"]),
                quantity_on_hand=round(on_hand, 1),
                reorder_level=round(reorder, 1),
                unit_cost=round(random.uniform(0.8, 12.0), 2),
                lead_time_days=int(supplier.avg_lead_time_days),
                supplier_id=supplier.id,
            )
            db.add(material)
            materials.append(material)
    db.commit()
    for m in materials:
        db.refresh(m)
    print(f"Seeded {len(materials)} raw materials.")

    reorder_count = 0
    for m in materials:
        smart_contract_service.evaluate_raw_material_stock(db, m)
        if recommendation_service.recommend_reorder(db, m):
            reorder_count += 1
    print(f"Triggered reorder alerts for {reorder_count} low-stock materials.")

    return materials


def seed_purchase_orders_and_shipments(db, suppliers: list[Supplier], materials: list[RawMaterial]) -> None:
    materials_by_supplier: dict[int, list[RawMaterial]] = {}
    for m in materials:
        materials_by_supplier.setdefault(m.supplier_id, []).append(m)

    po_count, shipment_count = 0, 0
    today = date.today()

    for supplier in suppliers:
        supplier_materials = materials_by_supplier.get(supplier.id, [])
        if not supplier_materials:
            continue

        for i in range(random.randint(2, 4)):
            material = random.choice(supplier_materials)
            days_ago = random.randint(-20, 120)
            order_date = today - timedelta(days=days_ago)
            lead = int(supplier.avg_lead_time_days + random.uniform(-3, 5))
            expected = order_date + timedelta(days=max(lead, 3))
            quantity = round(random.uniform(100, 1500), 1)

            po_number = f"PO-{supplier.id:03d}-{i + 1:02d}"
            if db.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_number).first():
                continue

            is_past = expected < today
            status = (
                PurchaseOrderStatus.COMPLETED
                if is_past
                else random.choice([PurchaseOrderStatus.PENDING_APPROVAL, PurchaseOrderStatus.APPROVED])
            )

            po = PurchaseOrder(
                po_number=po_number,
                supplier_id=supplier.id,
                raw_material_id=material.id,
                quantity=quantity,
                unit_price=material.unit_cost,
                order_date=order_date,
                expected_delivery_date=expected,
                status=status,
            )
            db.add(po)
            db.commit()
            db.refresh(po)
            po_count += 1

            shipment_code = f"SHP-{supplier.id:03d}-{i + 1:02d}"
            if db.query(Shipment).filter(Shipment.shipment_code == shipment_code).first():
                continue

            shipment_status = ShipmentStatus.PENDING
            actual_delivery = None
            if is_past:
                actual_delay = max(0, int(random.gauss(supplier.avg_lead_time_days * 0.15, 4)))
                actual_delivery = expected + timedelta(days=actual_delay)
                shipment_status = ShipmentStatus.DELIVERED if actual_delay <= 3 else ShipmentStatus.DELAYED
            elif days_ago > -5:
                shipment_status = ShipmentStatus.IN_TRANSIT

            shipment = Shipment(
                shipment_code=shipment_code,
                supplier_id=supplier.id,
                purchase_order_id=po.id,
                origin=f"{supplier.country} Port",
                destination="Colombo, Sri Lanka",
                quantity=quantity,
                order_date=order_date,
                expected_delivery_date=expected,
                actual_delivery_date=actual_delivery,
                status=shipment_status,
            )
            db.add(shipment)
            shipment_count += 1

        db.commit()

    print(f"Seeded {po_count} purchase orders and {shipment_count} shipments.")


def run_ai_scoring(db) -> None:
    if not ai_predict.models_are_trained():
        print("AI models not trained yet -- skipping scoring (run app once to auto-train, or `python -m app.ai.train`).")
        return

    suppliers = db.query(Supplier).all()
    for s in suppliers:
        _score_supplier(db, s)
    print(f"Scored {len(suppliers)} suppliers with the AI Risk Prediction Engine.")

    shipments = db.query(Shipment).filter(Shipment.status.in_(["pending", "in_transit"])).all()
    for sh in shipments:
        _predict_shipment(db, sh)
    print(f"Ran delay/anomaly prediction on {len(shipments)} active shipments.")


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_rules_seeded(db)
        seed_users(db)
        suppliers = seed_suppliers(db)
        seed_supplier_portal_user(db, suppliers)
        materials = seed_materials(db, suppliers)
        seed_purchase_orders_and_shipments(db, suppliers, materials)
        run_ai_scoring(db)
        print("\nSeed complete. Demo login: admin@supplychain.ai / admin123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
