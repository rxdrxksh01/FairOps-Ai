import pandas as pd
import numpy as np
from langchain_core.tools import tool
from tools.overview import get_dataframe
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import shap

# ─────────────────────────────────────────────
# Global Model State
# ─────────────────────────────────────────────

_model = None
_feature_names = None
_label_encoders = {}

def get_model():
    return _model, _feature_names, _label_encoders

def train_and_set_model() -> dict:
    """
    Trains RandomForest on loaded dataset.
    Called automatically on CSV upload. Not a tool — internal function.
    """
    global _model, _feature_names, _label_encoders

    df = get_dataframe()
    if df is None:
        raise ValueError("No dataset loaded.")

    # Auto detect target column
    target_col = None
    for col in df.columns:
        unique_vals = sorted(df[col].dropna().unique().tolist())
        if unique_vals == [0, 1] or unique_vals == [0.0, 1.0]:
            target_col = col
            break

    if target_col is None:
        raise ValueError("No binary target column found.")

    d = df.copy()
    _label_encoders = {}
    feature_cols = []

    for col in d.columns:
        if col == target_col:
            continue
        if col == "applicant_id":
            continue
        if d[col].dtype == object or d[col].nunique() <= 15:
            le = LabelEncoder()
            d[col] = le.fit_transform(d[col].astype(str))
            _label_encoders[col] = le
        feature_cols.append(col)

    X = d[feature_cols]
    y = d[target_col]

    _model = RandomForestClassifier(n_estimators=100, random_state=42)
    _model.fit(X, y)
    _feature_names = feature_cols

    preds = _model.predict(X)
    accuracy = round(float((preds == y).mean()), 3)

    return {
        "status": "Model trained",
        "target_column": target_col,
        "feature_columns": feature_cols,
        "training_rows": len(d),
        "accuracy": accuracy,
    }


# ─────────────────────────────────────────────
# Tool
# ─────────────────────────────────────────────

@tool
def get_feature_importance(dummy: str = "") -> dict:
    """
    STEP 3 — Call this after get_approval_by_group.
    Returns raw SHAP feature importance values for the trained model.
    Shows which features drive model decisions the most.
    No interpretation. Just raw SHAP numbers per feature.

    Args:
        dummy: ignored. pass empty string.

    Raises:
        ValueError: if model not trained yet.
        ValueError: if dataset not loaded.
    """
    if _model is None:
        raise ValueError("No model trained yet. Upload CSV first.")

    df = get_dataframe()
    if df is None:
        raise ValueError("No dataset loaded.")

    d = df.copy()
    for col in _feature_names:
        if col in _label_encoders:
            d[col] = _label_encoders[col].transform(d[col].astype(str))

    X = d[_feature_names]

    explainer = shap.TreeExplainer(_model)
    shap_values = explainer.shap_values(X)

    if isinstance(shap_values, list):
        sv = shap_values[1]
    else:
        sv = shap_values

    mean_shap = np.abs(sv).mean(axis=0)
    # Flatten in case SHAP returns multi-dim arrays (newer shap versions)
    mean_shap = np.array(mean_shap).flatten()
    importance = {
        feat: round(float(np.squeeze(val)), 4)
        for feat, val in zip(_feature_names, mean_shap)
    }

    ranked = sorted(importance.items(), key=lambda x: -x[1])

    return {
        "feature_importance": importance,
        "ranked_features": [{"feature": f, "importance": v} for f, v in ranked],
        "total_features": len(_feature_names),
    }