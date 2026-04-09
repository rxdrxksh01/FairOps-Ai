import pandas as pd
import numpy as np
from langchain_core.tools import tool
from tools.overview import get_dataframe

@tool
def get_correlation(input_json: str) -> dict:
    """
    STEP 5 — Call this after get_feature_importance.
    Returns raw correlation between any two columns in the dataset.
    Use this to detect indirect bias — e.g. if 'region' strongly
    correlates with 'income', then even removing 'region' from the
    model may not fix bias because 'income' acts as a proxy.

    Call this for every pair of:
    - demographic column vs target column
    - demographic column vs financial column
    - financial column vs target column

    This helps distinguish direct discrimination from proxy discrimination.
    No interpretation. Just raw correlation numbers.

    Args:
        input_json: JSON string:
        {
            "col1": "region",
            "col2": "income_monthly"
        }

    Returns:
        - pearson_correlation: numeric correlation (-1 to 1)
        - col1_value_counts: if categorical
        - col2_stats: if numeric
        - crosstab: if both categorical, raw counts per group pair
        - col1_vs_col2_means: if col1 categorical + col2 numeric,
          mean of col2 per group of col1

    Raises:
        ValueError: if dataset not loaded.
        ValueError: if either column not found.
    """
    df = get_dataframe()
    if df is None:
        raise ValueError("No dataset loaded.")

    try:
        import json
        params = json.loads(input_json)
        col1 = params["col1"]
        col2 = params["col2"]
    except Exception:
        raise ValueError("input_json must be valid JSON with 'col1' and 'col2' keys.")

    if col1 not in df.columns:
        raise ValueError(f"Column '{col1}' not found. Available: {list(df.columns)}")
    if col2 not in df.columns:
        raise ValueError(f"Column '{col2}' not found. Available: {list(df.columns)}")

    result = {
        "col1": col1,
        "col2": col2,
        "col1_dtype": str(df[col1].dtype),
        "col2_dtype": str(df[col2].dtype),
    }

    # Both numeric — pearson correlation
    if pd.api.types.is_numeric_dtype(df[col1]) and pd.api.types.is_numeric_dtype(df[col2]):
        corr = round(float(df[col1].corr(df[col2])), 4)
        result["pearson_correlation"] = corr
        result["kind"] = "numeric_vs_numeric"

    # col1 categorical, col2 numeric — mean of col2 per group
    elif (df[col1].dtype == object or df[col1].nunique() <= 15) and pd.api.types.is_numeric_dtype(df[col2]):
        means = df.groupby(col1)[col2].mean().round(2).to_dict()
        std = df.groupby(col1)[col2].std().round(2).to_dict()
        result["col1_vs_col2_means"] = means
        result["col1_vs_col2_std"] = std
        result["kind"] = "categorical_vs_numeric"

        # Point biserial style — encode col1 and correlate
        from sklearn.preprocessing import LabelEncoder
        encoded = LabelEncoder().fit_transform(df[col1].astype(str))
        corr = round(float(pd.Series(encoded).corr(df[col2])), 4)
        result["encoded_correlation"] = corr

    # Both categorical — crosstab
    elif df[col1].dtype == object and df[col2].dtype == object:
        crosstab = pd.crosstab(df[col1], df[col2])
        result["crosstab"] = crosstab.to_dict()
        result["kind"] = "categorical_vs_categorical"

    # col1 numeric, col2 categorical
    elif pd.api.types.is_numeric_dtype(df[col1]) and (df[col2].dtype == object or df[col2].nunique() <= 15):
        means = df.groupby(col2)[col1].mean().round(2).to_dict()
        result["col2_vs_col1_means"] = means
        result["kind"] = "numeric_vs_categorical"
        from sklearn.preprocessing import LabelEncoder
        encoded = LabelEncoder().fit_transform(df[col2].astype(str))
        corr = round(float(df[col1].corr(pd.Series(encoded))), 4)
        result["encoded_correlation"] = corr

    else:
        result["kind"] = "unknown"
        result["note"] = "Could not determine correlation type for these columns."

    return result