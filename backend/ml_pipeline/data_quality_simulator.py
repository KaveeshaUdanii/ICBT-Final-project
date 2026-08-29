"""
Shared corruption utilities used by build_source_datasets.py to turn the app's clean
synthetic generators (app/ai/data_generation.py) into "raw, as-exported-from-an-ERP"
CSV files -- the messy starting point the preprocessing notebooks then have to clean.

Every function takes a DataFrame and returns a new DataFrame with a *documented*, tunable
amount of a specific real-world data quality issue injected into specific columns. Nothing
here touches the underlying ground-truth signal the ML models learn from (that lives in
data_generation.py, untouched) -- this module only corrupts the *surface representation*,
exactly the way a real export pipeline (manual entry, legacy system quirks, re-exports)
would, without destroying the learnable relationship between features and targets.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Realistic messy variants of clean categorical values seen across this project's data.
COUNTRY_VARIANTS: dict[str, list[str]] = {
    "Sri Lanka": ["Sri Lanka", "SRI LANKA", "sri lanka", " Sri Lanka", "Srilanka", "LK", "Sri  Lanka"],
    "India": ["India", "INDIA", "india", " India ", "IN"],
    "China": ["China", "CHINA", "china", "P.R. China", "CN"],
    "Bangladesh": ["Bangladesh", "BANGLADESH", "bangladesh", "Bangla Desh", "BD"],
    "Vietnam": ["Vietnam", "VIETNAM", "vietnam", "Viet Nam", "VN"],
    "Indonesia": ["Indonesia", "INDONESIA", "indonesia", "Indonesai", "ID"],
    "Pakistan": ["Pakistan", "PAKISTAN", "pakistan", "Pakisthan", "PK"],
}

CATEGORY_VARIANTS: dict[str, list[str]] = {
    "fabric": ["fabric", "Fabric", "FABRIC", " fabric", "febric", "fabric "],
    "buttons": ["buttons", "Buttons", "BUTTONS", "buton", " buttons"],
    "zippers": ["zippers", "Zippers", "ZIPPERS", "zipers", "zippers "],
    "thread": ["thread", "Thread", "THREAD", " thread", "thred"],
    "packaging": ["packaging", "Packaging", "PACKAGING", "packageing", " packaging"],
    "trims": ["trims", "Trims", "TRIMS", "trim", " trims"],
    "dye_chemicals": ["dye_chemicals", "Dye Chemicals", "DYE-CHEMICALS", "dye chemicals", "dyechemicals"],
}

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y", "%d-%b-%Y", "%Y/%m/%d"]


def inject_missing(df: pd.DataFrame, rates: dict[str, float], seed: int) -> pd.DataFrame:
    """Sets cells to NaN in the given columns at the given per-column rates (0-1)."""
    out = df.copy()
    rng = np.random.default_rng(seed)
    for col, rate in rates.items():
        if col not in out.columns or rate <= 0:
            continue
        mask = rng.random(len(out)) < rate
        out.loc[mask, col] = np.nan
    return out


def add_duplicate_rows(df: pd.DataFrame, exact_frac: float, near_frac: float, near_jitter_cols: list[str], seed: int) -> pd.DataFrame:
    """Appends exact duplicate rows (simulating a re-exported batch overlapping the previous
    one) and near-duplicate rows (same identity, one numeric field re-measured slightly
    differently -- e.g. stock re-counted a day later)."""
    rng = np.random.default_rng(seed)
    n_exact = int(len(df) * exact_frac)
    n_near = int(len(df) * near_frac)

    exact_dupes = df.sample(n=n_exact, random_state=seed, replace=True) if n_exact else df.iloc[0:0]

    near_dupes = pd.DataFrame()
    if n_near:
        near_dupes = df.sample(n=n_near, random_state=seed + 1, replace=True).copy()
        for col in near_jitter_cols:
            if col in near_dupes.columns and pd.api.types.is_numeric_dtype(df[col]):
                jitter = rng.normal(1.0, 0.03, size=len(near_dupes))
                near_dupes[col] = near_dupes[col] * jitter

    combined = pd.concat([df, exact_dupes, near_dupes], ignore_index=True)
    return combined.sample(frac=1.0, random_state=seed + 2).reset_index(drop=True)


def corrupt_categorical(df: pd.DataFrame, col: str, variants: dict[str, list[str]], corrupt_rate: float, seed: int) -> pd.DataFrame:
    """Replaces a fraction of a clean categorical column's values with a randomly chosen
    messy real-world variant (case, whitespace, abbreviation, or typo)."""
    if col not in df.columns:
        return df
    out = df.copy()
    rng = np.random.default_rng(seed)
    mask = rng.random(len(out)) < corrupt_rate

    def pick_variant(value):
        options = variants.get(value)
        if not options:
            return value
        return rng.choice(options)

    out.loc[mask, col] = out.loc[mask, col].map(pick_variant)
    return out


def numbers_as_messy_strings(df: pd.DataFrame, col: str, frac: float, seed: int, style: str = "currency") -> pd.DataFrame:
    """Converts a fraction of a numeric column's values into strings with stray formatting
    (currency symbols, thousands separators, percent signs, or stray whitespace) -- the
    classic "Excel exported this as text" problem that breaks a naive pd.read_csv dtype."""
    if col not in df.columns:
        return df
    out = df.copy()
    out[col] = out[col].astype(object)
    rng = np.random.default_rng(seed)
    idx = out.sample(frac=frac, random_state=seed).index

    for i in idx:
        val = out.at[i, col]
        if pd.isna(val):
            continue
        if style == "currency":
            out.at[i, col] = f"${val:,.2f}"
        elif style == "percent":
            out.at[i, col] = f"{val * 100:.1f}%"
        elif style == "thousands":
            out.at[i, col] = f"{val:,.0f}"
        elif style == "padded":
            out.at[i, col] = f"  {val}  "
    return out


def inject_outliers(df: pd.DataFrame, col: str, frac: float, seed: int, kind: str = "extreme_multiplier") -> pd.DataFrame:
    """Injects a handful of clearly-wrong values (data entry errors), not more of the
    same natural variance the generator already produces -- e.g. a negative quantity,
    or a rate typed as 850 instead of 8.50."""
    if col not in df.columns:
        return df
    out = df.copy()
    rng = np.random.default_rng(seed)
    idx = out.sample(frac=frac, random_state=seed).index
    for i in idx:
        val = out.at[i, col]
        if pd.isna(val):
            continue
        if kind == "extreme_multiplier":
            out.at[i, col] = val * float(rng.choice([-1, 100, 1000]))
        elif kind == "negative":
            out.at[i, col] = -abs(val)
    return out


def corrupt_dates_mixed_format(df: pd.DataFrame, col: str, seed: int) -> pd.DataFrame:
    """Re-renders every date value in a random (but valid) format from DATE_FORMATS,
    simulating an export pulled from several systems/locales over time."""
    if col not in df.columns:
        return df
    out = df.copy()
    rng = np.random.default_rng(seed)

    def render(value):
        if pd.isna(value):
            return value
        ts = pd.Timestamp(value)
        fmt = rng.choice(DATE_FORMATS)
        return ts.strftime(fmt)

    out[col] = out[col].map(render)
    return out


def add_stray_index_column(df: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Adds a leftover 'Unnamed: 0' style column, exactly what pandas produces when a
    previous export was saved with `df.to_csv(...)` (no index=False) and re-read."""
    out = df.copy()
    out.insert(0, "Unnamed: 0", range(len(out)))
    return out


def add_free_text_notes(df: pd.DataFrame, seed: int, fill_rate: float = 0.15) -> pd.DataFrame:
    """Adds a free-text 'notes' column, mostly empty, occasionally containing an
    inconsistent operator remark -- realistic ERP clutter that a cleaning pass should drop
    or explicitly decide not to use as a model feature."""
    rng = np.random.default_rng(seed)
    notes_pool = [
        "urgent", "re-check qty", "phone confirmed", "see email", "n/a", "TBC",
        "customer requested rush", "", "", "", "",
    ]
    out = df.copy()
    out["notes"] = ""
    mask = rng.random(len(out)) < fill_rate
    out.loc[mask, "notes"] = [rng.choice(notes_pool) for _ in range(int(mask.sum()))]
    return out
