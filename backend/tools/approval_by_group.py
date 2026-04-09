from langchain_core.tools import tool
from tools.overview import get_dataframe

@tool
def get_approval_by_group(column_name: str) -> dict:
    """
    STEP 2 — Call this for every categorical column found in get_dataset_overview.
    Given any column name, returns raw approval/outcome counts and rates per group.
    No interpretation. No thresholds. Just raw numbers.

    Args:
        column_name: any categorical column from the dataset.
                     e.g. 'region', 'gender', 'employment_type', 'caste'

    Raises:
        ValueError: if column not found.
        ValueError: if column has more than 20 unique values.
        ValueError: if no binary target column found.
        ValueError: if dataset not loaded.
    """
    df = get_dataframe()
    if df is None:
        raise ValueError("No dataset loaded.")

    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' not found. Available: {list(df.columns)}")

    if df[column_name].nunique() > 20:
        raise ValueError(
            f"Column '{column_name}' has {df[column_name].nunique()} unique values. "
            f"Too many for group analysis. Use a column with under 20 unique values."
        )

    # Auto detect binary target column
    target_col = None
    for col in df.columns:
        if col == column_name:
            continue
        unique_vals = sorted(df[col].dropna().unique().tolist())
        if unique_vals == [0, 1] or unique_vals == [0.0, 1.0]:
            target_col = col
            break

    if target_col is None:
        raise ValueError(
            "No binary outcome column found. "
            "Dataset needs a column like 'approved' or 'decision' with values 0 and 1."
        )

    total = len(df)
    overall_rate = round(float(df[target_col].mean()), 3)
    by_group = {}

    for group in df[column_name].dropna().unique():
        subset = df[df[column_name] == group]
        approved = int(subset[target_col].sum())
        denied = int(len(subset) - approved)
        by_group[str(group)] = {
            "approval_rate": round(float(subset[target_col].mean()), 3),
            "total": len(subset),
            "approved": approved,
            "denied": denied,
            "share_of_dataset": round(len(subset) / total, 3),
        }

    return {
        "group_column": column_name,
        "target_column": target_col,
        "overall_approval_rate": overall_rate,
        "by_group": by_group,
    }