"""
Produces the three large, deliberately messy source CSV files that the preprocessing
notebooks (backend/ml_pipeline/notebooks/) clean, analyze, and train models from.

This is a synthetic dataset -- genuine confidential company data was never available for
this student project (documented in the main README) and remains unavailable now. What
this script does is generate data at real-company scale, engineered to *look and behave*
like an actual ERP export: the same messiness (missing values, duplicate rows, inconsistent
text, mixed date formats, numbers stored as strings, outliers) a real company's system
would produce, on top of a genuinely learnable ground-truth signal (reused unchanged from
app/ai/data_generation.py -- nothing about the underlying business logic is invented here,
only the surface-level export mess is).

Run directly:
    python -m ml_pipeline.build_source_datasets
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.ai.data_generation import (  # noqa: E402
    generate_material_demand_raw_facts,
    generate_materials,
    generate_shipments_raw_facts,
    generate_suppliers,
    suppliers_to_raw_facts,
)
from ml_pipeline import data_quality_simulator as dq  # noqa: E402

RAW_DIR = Path(__file__).resolve().parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

N_SUPPLIERS = 1_000
N_SHIPMENTS = 60_000
N_MATERIALS = 3_000
N_DEMAND_RECORDS = 45_000


def build_supplier_performance_dataset() -> None:
    suppliers = generate_suppliers(n=N_SUPPLIERS, seed=42)
    df = suppliers_to_raw_facts(suppliers, seed=42)

    df = dq.inject_missing(
        df,
        rates={
            "defect_rate": 0.08,
            "cancellation_rate": 0.10,
            "avg_lead_time_days": 0.05,
            "order_volume_last_year": 0.06,
            "on_time_delivery_rate": 0.04,
        },
        seed=101,
    )
    df = dq.corrupt_categorical(df, "country", dq.COUNTRY_VARIANTS, corrupt_rate=0.35, seed=102)
    df = dq.corrupt_categorical(df, "category", dq.CATEGORY_VARIANTS, corrupt_rate=0.30, seed=103)
    df = dq.numbers_as_messy_strings(df, "on_time_delivery_rate", frac=0.15, seed=104, style="percent")
    df = dq.numbers_as_messy_strings(df, "avg_lead_time_days", frac=0.10, seed=105, style="padded")
    df = dq.inject_outliers(df, "cancellation_rate", frac=0.01, seed=106, kind="extreme_multiplier")
    df = dq.inject_outliers(df, "order_volume_last_year", frac=0.01, seed=107, kind="negative")
    df = dq.add_free_text_notes(df, seed=108, fill_rate=0.12)
    df = dq.add_stray_index_column(df, seed=110)
    df = dq.add_duplicate_rows(
        df, exact_frac=0.02, near_frac=0.015, near_jitter_cols=["defect_rate", "cancellation_rate"], seed=109
    )

    path = RAW_DIR / "supplier_performance_records.csv"
    df.to_csv(path, index=False)
    print(f"Wrote {path} -- {df.shape[0]:,} rows x {df.shape[1]} cols")


def build_shipment_logistics_dataset() -> None:
    suppliers = generate_suppliers(n=max(N_SUPPLIERS, 650), seed=7)
    df = generate_shipments_raw_facts(suppliers, n=N_SHIPMENTS, seed=7)

    df = dq.inject_missing(
        df,
        rates={
            "quantity": 0.03,
            "supplier_defect_rate": 0.05,
            "supplier_cancellation_rate": 0.06,
            "delay_days": 0.02,
        },
        seed=201,
    )
    df = dq.corrupt_categorical(df, "supplier_country", dq.COUNTRY_VARIANTS, corrupt_rate=0.30, seed=202)
    df = dq.corrupt_categorical(df, "supplier_category", dq.CATEGORY_VARIANTS, corrupt_rate=0.25, seed=203)
    df = dq.inject_outliers(df, "quantity", frac=0.005, seed=206, kind="negative")
    df = dq.numbers_as_messy_strings(df, "quantity", frac=0.12, seed=204, style="thousands")
    df = dq.numbers_as_messy_strings(df, "supplier_on_time_delivery_rate", frac=0.10, seed=205, style="percent")
    df = dq.corrupt_dates_mixed_format(df, "order_date", seed=207)
    df = dq.corrupt_dates_mixed_format(df, "expected_delivery_date", seed=208)
    df = dq.add_free_text_notes(df, seed=209, fill_rate=0.08)
    df = dq.add_stray_index_column(df, seed=211)
    df = dq.add_duplicate_rows(
        df, exact_frac=0.015, near_frac=0.01, near_jitter_cols=["quantity", "delay_days"], seed=210
    )

    path = RAW_DIR / "shipment_logistics_records.csv"
    df.to_csv(path, index=False)
    print(f"Wrote {path} -- {df.shape[0]:,} rows x {df.shape[1]} cols")


def build_inventory_demand_dataset() -> None:
    materials = generate_materials(n=N_MATERIALS, seed=21)
    df = generate_material_demand_raw_facts(materials, n=N_DEMAND_RECORDS, seed=21)

    df = dq.inject_missing(
        df,
        rates={
            "unit_cost": 0.05,
            "supplier_on_time_rate": 0.06,
            "quantity_on_hand": 0.03,
            "actual_demand_next_30_days": 0.02,
        },
        seed=301,
    )
    df = dq.corrupt_categorical(df, "material_category", dq.CATEGORY_VARIANTS, corrupt_rate=0.30, seed=302)
    df = dq.numbers_as_messy_strings(df, "unit_cost", frac=0.15, seed=303, style="currency")
    df = dq.numbers_as_messy_strings(df, "supplier_on_time_rate", frac=0.10, seed=304, style="percent")
    df = dq.inject_outliers(df, "quantity_on_hand", frac=0.01, seed=305, kind="negative")
    df = dq.inject_outliers(df, "lead_time_days", frac=0.005, seed=306, kind="extreme_multiplier")
    df = dq.corrupt_dates_mixed_format(df, "as_of_date", seed=307)
    df = dq.add_free_text_notes(df, seed=308, fill_rate=0.10)
    df = dq.add_stray_index_column(df, seed=310)
    df = dq.add_duplicate_rows(
        df, exact_frac=0.02, near_frac=0.015, near_jitter_cols=["quantity_on_hand", "actual_demand_next_30_days"], seed=309
    )

    path = RAW_DIR / "inventory_demand_records.csv"
    df.to_csv(path, index=False)
    print(f"Wrote {path} -- {df.shape[0]:,} rows x {df.shape[1]} cols")


def main() -> None:
    build_supplier_performance_dataset()
    build_shipment_logistics_dataset()
    build_inventory_demand_dataset()


if __name__ == "__main__":
    main()
