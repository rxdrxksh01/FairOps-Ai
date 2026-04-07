"""
fairness_engine.py — Threshold-based bias mitigation for FairCare AI.

Two mitigation strategies:
  Type 1: Single-feature thresholds — one demographic triggers threshold adjustment.
  Type 2: Composite thresholds — multiple features together trigger more aggressive adjustment.

Pipeline:
  model predict_proba → threshold lookup → adjusted decision → fairness metrics → policy flag
"""

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

DEFAULT_THRESHOLD = 0.50

# ─────────────────────────────────────────────
# Type 1 — Single-Feature Thresholds
# ─────────────────────────────────────────────
# Each maps one demographic feature value to a lowered threshold.
# Calibrated from dataset stats:
#   Rural approval: 21.7% vs Urban: 80.5%
#   Daily Wage: 18.3% vs Salaried: 80.0%
#   Gender gap: negligible (60.2% vs 60.4%)

FEATURE_THRESHOLDS = {
    "region": {
        "Rural":      0.35,
        "Semi-Urban": 0.45,
        "Urban":      0.50,   # privileged — no adjustment
    },
    "employment_type": {
        "Daily Wage":    0.35,
        "Self-Employed": 0.45,
        "Unemployed":    0.45,
        "Salaried":      0.50,  # privileged — no adjustment
    },
    "gender": {
        "Female": 0.48,
        "Male":   0.50,
    },
}

# ─────────────────────────────────────────────
# Type 2 — Composite Group Thresholds
# ─────────────────────────────────────────────
# Multiple features together → more aggressive adjustment.
# Checked in order; first full match wins (most specific first).

COMPOSITE_THRESHOLDS = [
    {
        "name": "Rural + Daily Wage + Low Credit",
        "conditions": {"region": "Rural", "employment_type": "Daily Wage"},
        "numeric_conditions": {"credit_score": {"below": 600}},
        "threshold": 0.22,
        "reason": (
            "Triple intersectional disadvantage: Rural location, daily-wage "
            "employment, and low credit score — all three are systemic barriers "
            "to medical loan access in India."
        ),
    },
    {
        "name": "Rural + Daily Wage",
        "conditions": {"region": "Rural", "employment_type": "Daily Wage"},
        "numeric_conditions": {},
        "threshold": 0.28,
        "reason": (
            "Intersectional disadvantage: both region and employment type "
            "show severe bias in the dataset (21.7% and 18.3% approval rates "
            "respectively vs 80%+ for privileged groups)."
        ),
    },
    {
        "name": "Rural + Low Credit + Low Income",
        "conditions": {"region": "Rural"},
        "numeric_conditions": {
            "credit_score": {"below": 600},
            "income_monthly": {"below": 15000},
        },
        "threshold": 0.25,
        "reason": (
            "Rural location compounds with financial indicators that may "
            "reflect systemic access barriers, not individual creditworthiness."
        ),
    },
    {
        "name": "Daily Wage + Low Credit",
        "conditions": {"employment_type": "Daily Wage"},
        "numeric_conditions": {"credit_score": {"below": 600}},
        "threshold": 0.30,
        "reason": (
            "Employment instability combined with low credit — often a "
            "systemic issue, not individual failure."
        ),
    },
    {
        "name": "Rural + Low Income",
        "conditions": {"region": "Rural"},
        "numeric_conditions": {"income_monthly": {"below": 15000}},
        "threshold": 0.32,
        "reason": (
            "Rural applicants with low income face compounded barriers to "
            "credit access."
        ),
    },
]

# ─────────────────────────────────────────────
# Known disadvantaged groups (for policy gate)
# ─────────────────────────────────────────────

DISADVANTAGED_VALUES = {
    "region": ["Rural"],
    "employment_type": ["Daily Wage"],
}


# ═════════════════════════════════════════════
# Core Functions
# ═════════════════════════════════════════════

def _check_numeric_conditions(applicant: dict, numeric_conditions: dict) -> bool:
    """Check if all numeric conditions are met."""
    for col, rule in numeric_conditions.items():
        val = applicant.get(col)
        if val is None:
            return False
        try:
            val = float(val)
        except (TypeError, ValueError):
            return False
        if "below" in rule and val >= rule["below"]:
            return False
        if "above" in rule and val <= rule["above"]:
            return False
    return True


def get_adjusted_threshold(applicant: dict) -> dict:
    """
    Determine the approval threshold for this applicant.
    Returns which rule matched and the adjusted threshold.

    Priority: composite thresholds > single-feature thresholds.
    For single-feature, takes the LOWEST (most favorable to applicant).
    """

    # --- Check composite thresholds first (most specific wins) ---
    for rule in COMPOSITE_THRESHOLDS:
        cat_match = all(
            applicant.get(col) == val
            for col, val in rule["conditions"].items()
        )
        num_match = _check_numeric_conditions(
            applicant, rule.get("numeric_conditions", {})
        )
        if cat_match and num_match:
            return {
                "threshold": rule["threshold"],
                "rule_type": "composite",
                "rule_name": rule["name"],
                "reason": rule["reason"],
                "default_threshold": DEFAULT_THRESHOLD,
                "adjustment": round(DEFAULT_THRESHOLD - rule["threshold"], 3),
            }

    # --- Fall back to single-feature thresholds ---
    matched_thresholds = []
    matched_features = []

    for feature, mapping in FEATURE_THRESHOLDS.items():
        val = applicant.get(feature)
        if val is not None and val in mapping:
            t = mapping[val]
            if t < DEFAULT_THRESHOLD:
                matched_thresholds.append(t)
                matched_features.append(f"{feature}={val}")

    if matched_thresholds:
        best = min(matched_thresholds)
        idx = matched_thresholds.index(best)
        return {
            "threshold": best,
            "rule_type": "single_feature",
            "rule_name": matched_features[idx],
            "reason": (
                f"Threshold adjusted for {matched_features[idx]} — "
                f"this group shows significantly lower approval rates in the dataset."
            ),
            "default_threshold": DEFAULT_THRESHOLD,
            "adjustment": round(DEFAULT_THRESHOLD - best, 3),
        }

    # --- No adjustment needed ---
    return {
        "threshold": DEFAULT_THRESHOLD,
        "rule_type": "none",
        "rule_name": "default",
        "reason": "No mitigation rule triggered — standard threshold applied.",
        "default_threshold": DEFAULT_THRESHOLD,
        "adjustment": 0.0,
    }


def apply_fair_decision(
    applicant: dict,
    model,
    feature_names: list,
    label_encoders: dict,
) -> dict:
    """
    Full mitigation pipeline for one applicant.
    Returns raw score, threshold, decisions (before & after), and mitigation details.
    """

    # --- Encode and score ---
    row = pd.Series(applicant)
    if "applicant_id" in feature_names and "applicant_id" not in row.index:
        row["applicant_id"] = 0

    d = row.to_frame().T.copy()
    for col in feature_names:
        if col in label_encoders:
            d[col] = label_encoders[col].transform(d[col].astype(str))

    X = d[feature_names]
    proba = model.predict_proba(X)[0]
    # proba[1] = probability of approval (class 1)
    raw_score = float(proba[1])

    # --- Get threshold ---
    threshold_info = get_adjusted_threshold(applicant)
    adjusted_threshold = threshold_info["threshold"]

    # --- Decisions ---
    original_decision = "APPROVED" if raw_score >= DEFAULT_THRESHOLD else "DENIED"
    final_decision = "APPROVED" if raw_score >= adjusted_threshold else "DENIED"
    mitigation_applied = (original_decision != final_decision)

    # --- Policy flag ---
    is_disadvantaged = _is_disadvantaged(applicant)
    policy_flag = _compute_policy_flag(
        original_decision, final_decision, mitigation_applied,
        is_disadvantaged, raw_score, adjusted_threshold
    )

    # --- Confidence ---
    if final_decision == "APPROVED":
        confidence = round(raw_score, 3)
    else:
        confidence = round(1.0 - raw_score, 3)

    return {
        "raw_score": round(raw_score, 4),
        "default_threshold": DEFAULT_THRESHOLD,
        "adjusted_threshold": adjusted_threshold,
        "original_decision": original_decision,
        "final_decision": final_decision,
        "confidence": confidence,
        "mitigation_applied": mitigation_applied,
        "mitigation_details": threshold_info,
        "policy_flag": policy_flag,
        "is_disadvantaged": is_disadvantaged,
        "disadvantaged_groups": _get_disadvantaged_labels(applicant),
    }


def _is_disadvantaged(applicant: dict) -> bool:
    """Check if applicant belongs to any known disadvantaged group."""
    for feature, values in DISADVANTAGED_VALUES.items():
        if applicant.get(feature) in values:
            return True
    return False


def _get_disadvantaged_labels(applicant: dict) -> list:
    """Return list of disadvantaged group labels this applicant belongs to."""
    labels = []
    for feature, values in DISADVANTAGED_VALUES.items():
        if applicant.get(feature) in values:
            labels.append(f"{feature}={applicant[feature]}")
    return labels


def _compute_policy_flag(
    original: str, final: str, mitigated: bool,
    is_disadvantaged: bool, raw_score: float, threshold: float,
) -> dict:
    """
    Policy flag:
      GREEN  — clean decision, no mitigation needed
      YELLOW — mitigation flipped DENIED → APPROVED (transparency required)
      RED    — still DENIED after mitigation + disadvantaged group → HUMAN REVIEW
    """
    if mitigated and final == "APPROVED":
        return {
            "level": "YELLOW",
            "label": "Mitigation Applied",
            "detail": (
                f"Original decision was DENIED (score {raw_score:.3f} < 0.50). "
                f"Fairness-adjusted threshold ({threshold:.2f}) changed outcome to APPROVED."
            ),
        }
    elif final == "DENIED" and is_disadvantaged:
        return {
            "level": "RED",
            "label": "Human Review Required",
            "detail": (
                f"Applicant belongs to a disadvantaged group and was DENIED "
                f"even after mitigation (score {raw_score:.3f} < {threshold:.2f}). "
                f"A human reviewer should evaluate this case."
            ),
        }
    else:
        return {
            "level": "GREEN",
            "label": "Standard Decision",
            "detail": (
                f"Decision reached through standard process. "
                f"Score {raw_score:.3f} {'≥' if final == 'APPROVED' else '<'} "
                f"threshold {threshold:.2f}."
            ),
        }


# ═════════════════════════════════════════════
# Dataset-Level Fairness Metrics
# ═════════════════════════════════════════════

def compute_fairness_metrics(dataset_summary: dict) -> dict:
    """
    Compute formal fairness metrics from the pre-computed dataset summary.
    Returns Demographic Parity, Disparate Impact, and gap analysis
    for region, employment_type, and gender.
    """
    metrics = {}

    # --- Region ---
    region_rates = dataset_summary.get("approval_by_region", {})
    if region_rates:
        metrics["region"] = _compute_group_metrics(
            region_rates,
            privileged="Urban",
            label="Region",
        )

    # --- Employment ---
    emp_rates = dataset_summary.get("approval_by_employment", {})
    if emp_rates:
        metrics["employment_type"] = _compute_group_metrics(
            emp_rates,
            privileged="Salaried",
            label="Employment Type",
        )

    # --- Gender ---
    gender_rates = dataset_summary.get("approval_by_gender", {})
    if gender_rates:
        metrics["gender"] = _compute_group_metrics(
            gender_rates,
            privileged="Male",
            label="Gender",
        )

    # --- Overall severity ---
    all_di = [
        m["disparate_impact"]
        for m in metrics.values()
        if m.get("disparate_impact") is not None
    ]
    worst_di = min(all_di) if all_di else 1.0

    if worst_di < 0.5:
        severity = "CRITICAL"
    elif worst_di < 0.8:
        severity = "HIGH"
    elif worst_di < 0.9:
        severity = "MODERATE"
    else:
        severity = "LOW"

    return {
        "metrics_by_group": metrics,
        "overall_severity": severity,
        "worst_disparate_impact": round(worst_di, 3),
    }


def _compute_group_metrics(
    rates: dict, privileged: str, label: str
) -> dict:
    """
    Compute fairness metrics for one demographic dimension.
    """
    priv_rate = rates.get(privileged, 0)
    overall_rate = sum(rates.values()) / len(rates) if rates else 0

    # Demographic Parity gap: max_rate - min_rate
    max_rate = max(rates.values())
    min_rate = min(rates.values())
    dp_gap = round(max_rate - min_rate, 3)

    # Disparate Impact: min_rate / max_rate (4/5ths rule: must be >= 0.8)
    di = round(min_rate / max_rate, 3) if max_rate > 0 else 0.0

    # Equal Opportunity gap (simplified): spread across groups
    group_gaps = {
        group: {
            "rate": round(rate, 3),
            "gap_vs_privileged": round(rate - priv_rate, 3),
            "ratio_vs_privileged": round(rate / priv_rate, 3) if priv_rate > 0 else 0,
        }
        for group, rate in rates.items()
    }

    # Severity for this dimension
    if di < 0.5:
        dim_severity = "CRITICAL"
    elif di < 0.8:
        dim_severity = "HIGH"
    elif di < 0.9:
        dim_severity = "MODERATE"
    else:
        dim_severity = "LOW"

    return {
        "label": label,
        "privileged_group": privileged,
        "privileged_rate": round(priv_rate, 3),
        "demographic_parity_gap": dp_gap,
        "disparate_impact": di,
        "four_fifths_rule_pass": di >= 0.8,
        "severity": dim_severity,
        "group_details": group_gaps,
    }


def get_threshold_config() -> dict:
    """Return the current threshold configuration for display/API."""
    return {
        "default_threshold": DEFAULT_THRESHOLD,
        "feature_thresholds": FEATURE_THRESHOLDS,
        "composite_thresholds": [
            {
                "name": rule["name"],
                "conditions": rule["conditions"],
                "numeric_conditions": rule.get("numeric_conditions", {}),
                "threshold": rule["threshold"],
                "reason": rule["reason"],
            }
            for rule in COMPOSITE_THRESHOLDS
        ],
        "disadvantaged_groups": DISADVANTAGED_VALUES,
    }
