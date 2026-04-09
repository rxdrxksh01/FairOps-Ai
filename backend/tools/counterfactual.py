import pandas as pd
import json
from langchain_core.tools import tool
from tools.overview import get_dataframe
from tools.feature_importance import get_model

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _encode_row(row: pd.Series, feature_names: list, label_encoders: dict) -> pd.DataFrame:
    d = row.to_frame().T.copy()
    for col in feature_names:
        if col in label_encoders:
            d[col] = label_encoders[col].transform(d[col].astype(str))
    return d[feature_names]

def _predict_row(row: pd.Series, model, feature_names: list, label_encoders: dict) -> dict:
    encoded = _encode_row(row, feature_names, label_encoders)
    decision = int(model.predict(encoded)[0])
    confidence = float(model.predict_proba(encoded)[0][decision])
    return {
        "decision": "APPROVED" if decision == 1 else "DENIED",
        "confidence": round(confidence, 3)
    }

# ─────────────────────────────────────────────
# Tool
# ─────────────────────────────────────────────

@tool
def run_counterfactual(input_json: str) -> dict:
    """
    STEP 4 — Call this after get_feature_importance for any group
    that shows suspicious approval rate gaps.

    Takes an applicant (real or provided) and a list of attribute
    change combinations. Applies each combination, reruns model,
    returns raw before/after predictions.

    Two modes:
    - auto: agent picks real denied applicants from a disadvantaged
            group automatically. No user input needed.
    - manual: user provided a specific applicant to test.

    Args:
        input_json: JSON string with structure:

        AUTO MODE:
        {
            "mode": "auto",
            "disadvantaged_group": {"column": "region", "value": "Rural"},
            "flip_combinations": [
                [["region", "Urban"]],
                [["employment_type", "Salaried"]],
                [["region", "Urban"], ["employment_type", "Salaried"]],
                [["region", "Urban"], ["employment_type", "Salaried"], ["credit_score", 700]]
            ]
        }

        MANUAL MODE:
        {
            "mode": "manual",
            "applicant": {
                "age": 45,
                "gender": "Male",
                "region": "Rural",
                "employment_type": "Daily Wage",
                "income_monthly": 12000,
                "credit_score": 620,
                "loan_amount_requested": 150000,
                "existing_loans": 1
            },
            "flip_combinations": [
                [["region", "Urban"]],
                [["employment_type", "Salaried"]],
                [["region", "Urban"], ["employment_type", "Salaried"]],
                [["region", "Urban"], ["employment_type", "Salaried"], ["income_monthly", 50000]]
            ]
        }

    Returns raw before/after predictions for each combination.
    No verdicts. No interpretation. Just numbers.

    Raises:
        ValueError: if model not trained.
        ValueError: if input_json malformed.
        ValueError: if columns not found in dataset.
        ValueError: if fewer than 5 denied applicants in group (auto mode).
    """
    model, feature_names, label_encoders = get_model()
    if model is None:
        raise ValueError("No model trained yet. Upload CSV first.")

    df = get_dataframe()
    if df is None:
        raise ValueError("No dataset loaded.")

    try:
        params = json.loads(input_json)
    except Exception:
        raise ValueError(f"input_json must be valid JSON.")

    mode = params.get("mode", "auto")
    flip_combinations = params.get("flip_combinations", [])

    if not flip_combinations:
        raise ValueError("flip_combinations cannot be empty.")

    # Normalize flip_combinations — LLM sends inconsistent formats:
    # Format A (correct):  [ [["region","Urban"]], [["region","Urban"],["employment_type","Salaried"]] ]
    # Format B (flat):     [ ["region","Urban"], ["employment_type","Salaried"] ]  ← single combo
    # Format C (dicts):    [ [{"column":"region","value":"Urban"}] ]
    
    def parse_single_change(item):
        """Parse one col→val change from any format."""
        if isinstance(item, dict):
            col = item.get("column") or item.get("col") or item.get("feature") or item.get("attribute")
            val = item.get("value") or item.get("val") or item.get("new_value")
            return (col, val)
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            return (item[0], item[1])
        elif isinstance(item, str):
            return None  # string — means the combo itself is [col, val]
        return None

    def normalize_combo(combo):
        """Turn any combo format into list of (col, val) tuples."""
        # If combo is [col_string, val] — flat single change
        if (isinstance(combo, (list, tuple)) and len(combo) == 2
                and isinstance(combo[0], str) and not isinstance(combo[1], (list, tuple, dict))):
            return [(combo[0], combo[1])]
        # If combo is a list of changes
        result = []
        for item in combo:
            parsed = parse_single_change(item)
            if parsed and parsed[0]:
                result.append(parsed)
        return result if result else [(str(combo[0]), combo[1])]

    flip_combinations = [normalize_combo(combo) for combo in flip_combinations]
    # Remove any empty combos
    flip_combinations = [c for c in flip_combinations if c]

    if not flip_combinations:
        raise ValueError("flip_combinations parsed to empty. Check format.")

    # Validate columns exist
    for combo in flip_combinations:
        for col, val in combo:
            if col not in df.columns:
                raise ValueError(f"Column '{col}' not found. Available: {list(df.columns)}")

    # Auto detect target column
    target_col = None
    for col in df.columns:
        unique_vals = sorted(df[col].dropna().unique().tolist())
        if unique_vals == [0, 1] or unique_vals == [0.0, 1.0]:
            target_col = col
            break

    # ─────────────────────────────────────────────
    # AUTO MODE
    # ─────────────────────────────────────────────
    if mode == "auto":
        dis_group = params.get("disadvantaged_group", {})
        dis_col = dis_group.get("column")
        dis_val = dis_group.get("value")

        if not dis_col or not dis_val:
            raise ValueError("auto mode needs 'disadvantaged_group' with 'column' and 'value'.")
        if dis_col not in df.columns:
            raise ValueError(f"Column '{dis_col}' not found.")

        denied = df[
            (df[dis_col].astype(str) == str(dis_val)) &
            (df[target_col] == 0)
        ]

        if len(denied) < 5:
            raise ValueError(
                f"Only {len(denied)} denied applicants in '{dis_col}={dis_val}'. Need at least 5."
            )

        sample = denied.sample(min(10, len(denied)), random_state=42)
        combo_results = []

        for combo in flip_combinations:
            combo_label = " + ".join([f"{c}={v}" for c, v in combo])
            details = []

            for idx, row in sample.iterrows():
                original = _predict_row(row, model, feature_names, label_encoders)
                flipped_row = row.copy()
                for col, val in combo:
                    flipped_row[col] = val
                flipped = _predict_row(flipped_row, model, feature_names, label_encoders)

                details.append({
                    "applicant_id": str(row.get("applicant_id", idx)),
                    "before": original,
                    "after": flipped,
                    "decision_changed": original["decision"] != flipped["decision"],
                })

            flips = sum(1 for d in details if d["decision_changed"])
            combo_results.append({
                "combination": combo_label,
                "total_tested": len(sample),
                "flips": flips,
                "flip_rate": round(flips / len(sample), 3),
                "details": details,
            })

        return {
            "mode": "auto",
            "disadvantaged_group": f"{dis_col}={dis_val}",
            "sample_size": len(sample),
            "total_denied_in_group": len(denied),
            "combo_results": combo_results,
        }

    # ─────────────────────────────────────────────
    # MANUAL MODE
    # ─────────────────────────────────────────────
    else:
        applicant = params.get("applicant")
        if not applicant:
            raise ValueError("manual mode needs 'applicant' dict.")

        applicant_row = pd.Series(applicant)
        missing = [f for f in feature_names if f not in applicant_row.index and f != "applicant_id"]
        if missing:
            raise ValueError(f"Applicant missing columns: {missing}")
        # Fill applicant_id with dummy if not provided
        if "applicant_id" in feature_names and "applicant_id" not in applicant_row.index:
            applicant_row["applicant_id"] = 0

        original = _predict_row(applicant_row, model, feature_names, label_encoders)
        combo_results = []

        for combo in flip_combinations:
            combo_label = " + ".join([f"{c}={v}" for c, v in combo])
            flipped_row = applicant_row.copy()
            for col, val in combo:
                flipped_row[col] = val
            flipped = _predict_row(flipped_row, model, feature_names, label_encoders)

            combo_results.append({
                "combination": combo_label,
                "before": original,
                "after": flipped,
                "decision_changed": original["decision"] != flipped["decision"],
            })

        return {
            "mode": "manual",
            "original": original,
            "combo_results": combo_results,
        }