"""
offline_investigate.py — Run this ONCE before launching FairCare AI.
Trains model + runs full agent investigation + saves to disk.
Never needs to run again unless dataset changes.

Usage:
    cd ~/Desktop/faircare-ai/backend
    source venv/bin/activate
    python3 offline_investigate.py
"""

import os
import sys
import json
import pickle
import pandas as pd
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
sys.path.insert(0, os.path.dirname(__file__))

from tools import set_dataframe, train_and_set_model, get_model
from agent import _get_agent, SYSTEM_PROMPT

# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────

BACKEND_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BACKEND_DIR, "..", "data", "sample_medical_loans.csv")
MODEL_PATH = os.path.join(BACKEND_DIR, "model.pkl")
ENCODERS_PATH = os.path.join(BACKEND_DIR, "label_encoders.pkl")
FINDINGS_PATH = os.path.join(BACKEND_DIR, "offline_findings.json")

# ─────────────────────────────────────────────
# Step 1 — Load Dataset
# ─────────────────────────────────────────────

print("\n" + "="*60)
print("FAIRCARE AI — OFFLINE INVESTIGATION")
print("="*60)

print("\n[1/4] Loading dataset...")
df = pd.read_csv(DATA_PATH)
set_dataframe(df)
print(f"✅ Loaded {len(df)} rows, {len(df.columns)} columns")
print(f"   Columns: {list(df.columns)}")

# ─────────────────────────────────────────────
# Step 2 — Train Model
# ─────────────────────────────────────────────

print("\n[2/4] Training RandomForest model...")
training_summary = train_and_set_model()
print(f"✅ Model trained")
print(f"   Target column: {training_summary['target_column']}")
print(f"   Features: {training_summary['feature_columns']}")
print(f"   Accuracy: {training_summary['accuracy']}")

# Save model + encoders to disk
model, feature_names, label_encoders = get_model()

with open(MODEL_PATH, "wb") as f:
    pickle.dump({
        "model": model,
        "feature_names": feature_names,
    }, f)

with open(ENCODERS_PATH, "wb") as f:
    pickle.dump(label_encoders, f)

print(f"✅ Model saved → {MODEL_PATH}")
print(f"✅ Encoders saved → {ENCODERS_PATH}")

# ─────────────────────────────────────────────
# Step 3 — Run Agent Investigation
# ─────────────────────────────────────────────

print("\n[3/4] Running full agent investigation...")
print("   This will use ~97k tokens. Running once only.")
print("   Estimated time: 2-4 minutes...\n")
import time
agent = _get_agent()

# Small delay to avoid TPM limits
time.sleep(5)

result = agent.invoke({
    "messages": [
        {
            "role": "user",
            "content": (
                "A medical loan dataset has been loaded for bias investigation. "
                "Run your complete 6-step investigation protocol now. "
                "Follow ALL steps in exact order. Do not skip any step. "
                "Call get_approval_by_group for EVERY categorical column. "
                "Run counterfactual in auto mode for every biased group you find. "
                "Produce the complete investigation report at the end."
            )
        }
    ]
})

investigation_report = result["messages"][-1].content
print("✅ Investigation complete")

# ─────────────────────────────────────────────
# Step 4 — Save Findings
# ─────────────────────────────────────────────

print("\n[4/4] Saving findings to disk...")

findings = {
    "training_summary": training_summary,
    "dataset_summary": {
        "total_rows": len(df),
        "columns": list(df.columns),
        "approval_rate": round(float(df[training_summary["target_column"]].mean()), 3),
        "approval_by_region": df.groupby("region")["approved"].mean().round(3).to_dict(),
        "approval_by_employment": df.groupby("employment_type")["approved"].mean().round(3).to_dict(),
        "approval_by_gender": df.groupby("gender")["approved"].mean().round(3).to_dict(),
    },
    "investigation_report": investigation_report,
    "feature_names": feature_names,
}

with open(FINDINGS_PATH, "w") as f:
    json.dump(findings, f, indent=2)

print(f"✅ Findings saved → {FINDINGS_PATH}")

print("\n" + "="*60)
print("OFFLINE INVESTIGATION COMPLETE")
print("="*60)
print(f"\nFiles saved:")
print(f"  model.pkl             ← trained RandomForest")
print(f"  label_encoders.pkl    ← categorical encoders")
print(f"  offline_findings.json ← full bias investigation report")
print(f"\nYou can now run the API:")
print(f"  uvicorn main:app --reload --port 8000")
print("="*60 + "\n")