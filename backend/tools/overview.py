import pandas as pd

# ─────────────────────────────────────────────
# Global State
# ─────────────────────────────────────────────

_df: pd.DataFrame = None

def set_dataframe(df: pd.DataFrame):
    global _df
    _df = df

def get_dataframe() -> pd.DataFrame:
    return _df

# ─────────────────────────────────────────────
# Tool
# ─────────────────────────────────────────────

from langchain_core.tools import tool

@tool
def get_dataset_overview(dummy: str = "") -> dict:
    """
    STEP 1 — Always call this first. No exceptions.
    Returns raw dataset stats — column names, dtypes, 
    value counts for categorical columns, basic numeric stats,
    binary columns (potential target/outcome columns),
    null counts, and first 5 rows as sample.
    No interpretation. Just raw facts.
    """
    if _df is None:
        raise ValueError("No dataset loaded.")
    if len(_df) < 50:
        raise ValueError(f"Dataset too small ({len(_df)} rows). Need at least 50.")

    result = {
        "total_rows": len(_df),
        "total_columns": len(_df.columns),
        "column_names": list(_df.columns),
        "sample_rows": _df.head(5).to_dict(orient="records"),
        "columns": {},
        "binary_columns": [],
        "null_warnings": [],
    }

    for col in _df.columns:
        info = {
            "dtype": str(_df[col].dtype),
            "null_count": int(_df[col].isnull().sum()),
            "unique_count": int(_df[col].nunique()),
        }

        if _df[col].dtype == object or _df[col].nunique() <= 15:
            info["kind"] = "categorical"
            info["value_counts"] = _df[col].value_counts().head(15).to_dict()

        if pd.api.types.is_numeric_dtype(_df[col]):
            info["kind"] = "numeric"
            info["min"] = round(float(_df[col].min()), 2)
            info["max"] = round(float(_df[col].max()), 2)
            info["mean"] = round(float(_df[col].mean()), 2)
            info["median"] = round(float(_df[col].median()), 2)

            unique_vals = sorted(_df[col].dropna().unique().tolist())
            if unique_vals == [0, 1] or unique_vals == [0.0, 1.0]:
                result["binary_columns"].append({
                    "column": col,
                    "positive_rate": round(float(_df[col].mean()), 3),
                    "positive_count": int(_df[col].sum()),
                    "negative_count": int((1 - _df[col]).sum()),
                })

        if _df[col].isnull().mean() > 0.2:
            result["null_warnings"].append(
                f"Column '{col}' has {_df[col].isnull().mean():.0%} missing values."
            )

        result["columns"][col] = info

    return result