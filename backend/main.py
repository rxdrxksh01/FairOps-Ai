"""
main.py — FairCare AI API
No CSV upload. Loads offline artifacts on startup.
Pipeline: Model decides → Fairness engine adjusts → LLM explains.
"""

import os
import sys
import json
import traceback
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import load_offline_artifacts, investigate_applicant
from audit_log import log_decision, get_audit_log, clear_audit_log
from fairness_engine import (
    apply_fair_decision,
    compute_fairness_metrics,
    get_threshold_config,
)

# ─────────────────────────────────────────────
# App
# ─────────────────────────────────────────────

app = FastAPI(
    title="FairCare AI",
    description="Autonomous AI bias investigator for medical loan approvals",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Load artifacts on startup
# ─────────────────────────────────────────────

_findings: dict = {}
_model = None
_feature_names = None
_label_encoders = None

@app.on_event("startup")
def startup():
    global _findings, _model, _feature_names, _label_encoders
    try:
        _findings = load_offline_artifacts()

        # Also grab model refs for fairness engine
        from tools.feature_importance import get_model
        _model, _feature_names, _label_encoders = get_model()

        print("✅ Offline artifacts loaded successfully")
        print(f"   Approval rate: {_findings['dataset_summary']['approval_rate']}")
        print(f"   Rural approval: {_findings['dataset_summary']['approval_by_region']['Rural']}")
        print(f"   Fairness engine: ACTIVE")
    except Exception as e:
        print(f"❌ Failed to load artifacts: {e}")
        print("   Run python3 offline_investigate.py first")

# ─────────────────────────────────────────────
# Request Models
# ─────────────────────────────────────────────

class PredictRequest(BaseModel):
    applicant: dict

# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "name": "FairCare AI",
        "version": "3.0.0",
        "status": "ready" if _findings else "not ready — run offline_investigate.py first",
        "fairness_engine": "active",
    }

@app.get("/health")
def health():
    return {
        "status": "ok",
        "artifacts_loaded": bool(_findings),
        "groq_key_set": bool(os.environ.get("GROQ_API_KEY")),
        "fairness_engine": "active",
    }

@app.get("/dataset-info")
def dataset_info():
    if not _findings:
        raise HTTPException(status_code=503, detail="Artifacts not loaded.")
    return {
        "dataset_summary": _findings.get("dataset_summary"),
        "feature_names": _findings.get("feature_names"),
        "investigation_report": _findings.get("investigation_report"),
    }


@app.get("/fairness-config")
def fairness_config():
    """Return current threshold configuration."""
    return get_threshold_config()


@app.get("/fairness-metrics")
def fairness_metrics():
    """Return dataset-level fairness metrics (DP, DI, EO)."""
    if not _findings:
        raise HTTPException(status_code=503, detail="Artifacts not loaded.")
    return compute_fairness_metrics(_findings.get("dataset_summary", {}))


@app.post("/predict")
async def predict(request: PredictRequest):
    """
    Full pipeline:
    1. Fairness engine scores + applies threshold mitigation
    2. LLM agent explains the decision with full context
    3. Audit log records everything
    """
    if not _findings:
        raise HTTPException(
            status_code=503,
            detail="Offline artifacts not loaded. Run offline_investigate.py first."
        )
    if _model is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")

    applicant = request.applicant
    if not applicant:
        raise HTTPException(status_code=400, detail="Applicant data cannot be empty.")

    try:
        # ─── Step 1: Fairness Engine (deterministic) ───
        fair_result = apply_fair_decision(
            applicant=applicant,
            model=_model,
            feature_names=_feature_names,
            label_encoders=_label_encoders,
        )

        # ─── Step 2: LLM Agent (explanation) ───
        result = investigate_applicant(applicant, _findings, fair_result)

    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}\n{tb}")

    analysis = result.get("analysis", "")

    # ─── Step 3: Audit Log ───
    entry = log_decision(
        applicant=applicant,
        analysis=analysis,
        timestamp=datetime.utcnow().isoformat() + "Z",
        fairness_result=fair_result,
    )

    return {
        "status": "complete",
        "applicant": applicant,
        "decision": fair_result["final_decision"],
        "analysis": analysis,
        "audit_id": entry["id"],
        "fairness": {
            "raw_score": fair_result["raw_score"],
            "default_threshold": fair_result["default_threshold"],
            "adjusted_threshold": fair_result["adjusted_threshold"],
            "original_decision": fair_result["original_decision"],
            "final_decision": fair_result["final_decision"],
            "confidence": fair_result["confidence"],
            "mitigation_applied": fair_result["mitigation_applied"],
            "mitigation_details": fair_result["mitigation_details"],
            "policy_flag": fair_result["policy_flag"],
            "is_disadvantaged": fair_result["is_disadvantaged"],
            "disadvantaged_groups": fair_result["disadvantaged_groups"],
        },
    }

@app.get("/audit-log")
def audit_log():
    entries = get_audit_log()
    return {
        "total": len(entries),
        "entries": entries,
    }

@app.delete("/audit-log")
def clear_audit():
    clear_audit_log()
    return {"status": "cleared"}