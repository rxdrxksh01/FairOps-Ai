"""
audit_log.py — In-memory + file-backed audit trail for FairCare AI.
Every /predict call is logged here. Core judging criterion.
Now includes fairness engine results: raw score, threshold, mitigation, policy flag.
"""

import json
import os
from datetime import datetime
from typing import Optional

# ─────────────────────────────────────────────
# Storage
# ─────────────────────────────────────────────

_log: list = []
LOG_FILE = os.path.join(os.path.dirname(__file__), "audit_trail.jsonl")


def _load_from_file():
    """Load existing entries from file on startup."""
    global _log
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        _log.append(json.loads(line))
                    except Exception:
                        pass


_load_from_file()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _extract_decision(analysis: str) -> str:
    """
    Heuristic: scan first 600 chars of analysis for APPROVED/DENIED.
    Returns 'APPROVED', 'DENIED', or 'UNKNOWN'.
    """
    snippet = analysis.upper()[:600]
    if "APPROVED" in snippet:
        return "APPROVED"
    elif "DENIED" in snippet:
        return "DENIED"
    return "UNKNOWN"


def _write_to_file(entry: dict):
    """Append single entry to JSONL file."""
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def log_decision(
    applicant: dict,
    analysis: str,
    timestamp: Optional[str] = None,
    fairness_result: Optional[dict] = None,
) -> dict:
    """
    Log a single prediction. Called from main.py after every /predict.
    Returns the log entry dict.
    Now includes fairness engine fields when available.
    """
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat() + "Z"

    # Use fairness engine decision if available, else fallback to heuristic
    if fairness_result:
        decision = fairness_result.get("final_decision", _extract_decision(analysis))
    else:
        decision = _extract_decision(analysis)

    entry = {
        "id": len(_log) + 1,
        "timestamp": timestamp,
        "decision": decision,
        "applicant": applicant,
        "analysis_preview": analysis[:400] + ("..." if len(analysis) > 400 else ""),
        "full_analysis": analysis,
    }

    # Add fairness engine fields
    if fairness_result:
        entry["fairness"] = {
            "raw_score": fairness_result.get("raw_score"),
            "adjusted_threshold": fairness_result.get("adjusted_threshold"),
            "original_decision": fairness_result.get("original_decision"),
            "final_decision": fairness_result.get("final_decision"),
            "mitigation_applied": fairness_result.get("mitigation_applied"),
            "mitigation_rule": fairness_result.get("mitigation_details", {}).get("rule_name"),
            "policy_flag": fairness_result.get("policy_flag", {}).get("level"),
            "is_disadvantaged": fairness_result.get("is_disadvantaged"),
        }

    _log.append(entry)
    _write_to_file(entry)
    return entry


def get_audit_log() -> list:
    """Return all log entries, newest first."""
    return list(reversed(_log))


def clear_audit_log():
    """Clear in-memory log and delete file. Used for testing."""
    global _log
    _log = []
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
