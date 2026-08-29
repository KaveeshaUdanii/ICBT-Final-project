"""
CSV bulk-import support (module addition): most real ERP systems bring data in via a CSV file
upload rather than one-by-one manual entry through a form. This module provides the generic
mechanics shared by every entity's /import-csv endpoint -- parsing, per-row validation isolation,
error collection, and a single summary blockchain block for the whole batch -- while each router
supplies only its entity-specific row-building logic (field validation via the existing Pydantic
Create schema, plus any human-friendly name-to-id lookups).
"""

import io
from typing import Callable

import pandas as pd
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.services import blockchain_service

MAX_REPORTED_ERRORS = 50


def row_payload(row: dict, allowed_fields: set[str]) -> dict:
    """Drops NaN/None cells and any column not in the target schema, so a missing CSV cell lets
    the Pydantic schema's own default apply instead of failing validation with an explicit None."""
    return {k: v for k, v in row.items() if k in allowed_fields and pd.notna(v)}


def cell(row: dict, column: str):
    """Reads an optional lookup column (e.g. `supplier_name`) safely -- a missing column, or a
    present-but-empty CSV cell, both come back as pandas NaN, which is truthy in plain Python
    (`bool(float("nan")) is True`), so callers must use this instead of `row.get(column)` directly."""
    value = row.get(column)
    return value if pd.notna(value) else None


async def import_csv(
    db: Session,
    file: UploadFile,
    entity_type: str,
    row_builder: Callable[[dict], object],
    performed_by: str,
) -> dict:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please upload a .csv file.")

    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not parse CSV: {exc}") from exc

    if df.empty:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The CSV file has no data rows.")

    imported = 0
    errors: list[dict] = []

    for i, row in df.iterrows():
        row_dict = row.to_dict()
        # Each row gets its own SAVEPOINT so one bad row can be rolled back without discarding
        # the rows already successfully imported earlier in the same file.
        try:
            with db.begin_nested():
                obj = row_builder(row_dict)
                db.add(obj)
                db.flush()
            imported += 1
        except Exception as exc:  # noqa: BLE001 -- deliberately broad: any row-level failure is reported, not fatal
            if len(errors) < MAX_REPORTED_ERRORS:
                errors.append({"row": int(i) + 2, "error": str(exc)})  # +2: header row + 1-indexing

    db.commit()

    blockchain_service.add_block(
        db,
        event_type=f"{entity_type}.bulk_imported",
        payload={"entity_type": entity_type, "imported": imported, "failed": len(df) - imported},
        performed_by=performed_by,
    )

    return {"imported": imported, "failed": len(df) - imported, "errors": errors}
