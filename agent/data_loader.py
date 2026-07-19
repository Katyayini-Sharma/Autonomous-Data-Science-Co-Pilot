import io
import json
import os

import pandas as pd
import numpy as np


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}


def load_dataframe(file_path: str = None, file_bytes: bytes = None, filename: str = None) -> pd.DataFrame:
    if file_path is not None:
        ext = os.path.splitext(file_path)[1].lower()
        name = file_path
    elif file_bytes is not None and filename is not None:
        ext = os.path.splitext(filename)[1].lower()
        name = filename
    else:
        raise ValueError("Provide either file_path, or file_bytes + filename.")

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '{ext}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}")

    source = file_path if file_path is not None else io.BytesIO(file_bytes)

    if ext == ".csv":
        df = pd.read_csv(source)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(source)
    elif ext == ".json":
        raw = json.load(open(file_path)) if file_path else json.loads(file_bytes)
        if isinstance(raw, list):
            df = pd.json_normalize(raw)
        elif isinstance(raw, dict):
            list_values = [v for v in raw.values() if isinstance(v, list)]
            df = pd.json_normalize(list_values[0]) if list_values else pd.json_normalize(raw)
        else:
            raise ValueError("JSON file must contain an object or array of records.")
    else:
        raise ValueError(f"Unhandled extension '{ext}'")

    if df.empty:
        raise ValueError(f"'{name}' loaded but contains no rows.")

    return df



def basic_clean(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    log = []
    original_shape = df.shape

    empty_cols = [c for c in df.columns if df[c].isna().all()]
    if empty_cols:
        df = df.drop(columns=empty_cols)
        log.append(f"Dropped {len(empty_cols)} fully-empty column(s): {empty_cols}")

    n_dupes = df.duplicated().sum()
    if n_dupes:
        df = df.drop_duplicates()
        log.append(f"Removed {n_dupes} duplicate row(s)")

    na_tokens = {"", "na", "n/a", "null", "none", "nan", "-"}
    text_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].apply(lambda v: np.nan if v.lower() in na_tokens else v)

    date_like = [c for c in df.columns if any(k in c.lower() for k in ("date", "time", "timestamp"))]
    for col in date_like:
        try:
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().mean() > 0.7:
                df[col] = parsed
                log.append(f"Parsed '{col}' as datetime")
        except Exception:
            pass

    if df.shape != original_shape:
        log.append(f"Shape changed from {original_shape} to {df.shape}")
    if not log:
        log.append("No cleaning needed — data was already tidy.")

    return df, log




def profile_dataframe(df: pd.DataFrame, max_categories: int = 8) -> dict:
    profile = {"n_rows": int(len(df)), "n_columns": int(len(df.columns)), "columns": {}}

    for col in df.columns:
        s = df[col]
        col_info = {"dtype": str(s.dtype), "missing_pct": round(float(s.isna().mean() * 100), 2)}
        if pd.api.types.is_numeric_dtype(s):
            desc = s.describe()
            col_info.update({
                "min": _safe_float(desc.get("min")),
                "max": _safe_float(desc.get("max")),
                "mean": _safe_float(desc.get("mean")),
                "std": _safe_float(desc.get("std")),
            })
        elif pd.api.types.is_datetime64_any_dtype(s):
            col_info.update({"min": str(s.min()), "max": str(s.max())})
        else:
            top_vals = s.dropna().value_counts().head(max_categories)
            col_info["top_values"] = {str(k): int(v) for k, v in top_vals.items()}
            col_info["n_unique"] = int(s.nunique())
        profile["columns"][col] = col_info

    return profile


def _safe_float(x):
    try:
        return None if x is None or pd.isna(x) else round(float(x), 4)
    except Exception:
        return None