import os
import sys
import json
import pickle
from langgraph.prebuilt import create_react_agent
from langchain_groq import ChatGroq

sys.path.insert(0, os.path.dirname(__file__))
from tools import ALL_TOOLS

# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────

BACKEND_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BACKEND_DIR, "model.pkl")
ENCODERS_PATH = os.path.join(BACKEND_DIR, "label_encoders.pkl")
FINDINGS_PATH = os.path.join(BACKEND_DIR, "offline_findings.json")

# ─────────────────────────────────────────────
# Load offline artifacts on startup
# ─────────────────────────────────────────────

def load_offline_artifacts():
    """
    Load model, encoders, and offline findings from disk.
    Called once on server startup.
    Injects model + data back into tools global state.
    """
    from tools.overview import set_dataframe
    from tools.feature_importance import _model, _feature_names, _label_encoders
    import tools.feature_importance as fi
    import pandas as pd

    # Load model
    with open(MODEL_PATH, "rb") as f:
        model_data = pickle.load(f)
    fi._model = model_data["model"]
    fi._feature_names = model_data["feature_names"]

    # Load encoders
    with open(ENCODERS_PATH, "rb") as f:
        fi._label_encoders = pickle.load(f)

    # Load findings
    with open(FINDINGS_PATH, "r") as f:
        findings = json.load(f)

    # Reload dataset into global state for tools
    DATA_PATH = os.path.join(BACKEND_DIR, "..", "data", "sample_medical_loans.csv")
    df = pd.read_csv(DATA_PATH)
    set_dataframe(df)

    return findings


# ─────────────────────────────────────────────
# System Prompt Builder
# ─────────────────────────────────────────────

def _build_system_prompt(findings: dict) -> str:
    report = findings.get("investigation_report", "")
    dataset_summary = findings.get("dataset_summary", {})
    feature_names = findings.get("feature_names", [])

    return f"""
You are FairCare Agent — an AI explainer for a bias-aware medical loan approval system in India.

IMPORTANT: You are NOT the decision-maker. The decision has already been made by the
Fairness Engine (a deterministic ML pipeline with bias-mitigation thresholds).
Your job is to EXPLAIN the decision clearly and honestly.

═══════════════════════════════════════════
OFFLINE INVESTIGATION FINDINGS
═══════════════════════════════════════════

DATASET SUMMARY:
{json.dumps(dataset_summary, indent=2)}

FULL INVESTIGATION REPORT:
{report}

AVAILABLE FEATURES IN MODEL:
{feature_names}

═══════════════════════════════════════════
YOUR JOB — EXPLAIN THE DECISION
═══════════════════════════════════════════

You will receive:
1. The applicant's profile
2. The Fairness Engine result (raw score, threshold, mitigation details, policy flag)

You must analyze this specific person using your tools, then write a clear explanation.

FOLLOW THIS EXACT PROTOCOL:

STEP 1 — Call get_feature_importance("")
         Get SHAP values to understand which features drove this specific decision.

STEP 2 — Call run_counterfactual in MANUAL mode with this applicant.
         Test these combinations:
         - Each demographic attribute changed individually:
           region, gender, employment_type
         - Two demographic attributes changed together:
           region + employment_type
           region + gender
         - Demographic + financial improvement:
           region + credit_score improved
           employment_type + income_monthly improved

STEP 3 — Synthesize everything and write your explanation report.

═══════════════════════════════════════════
RULES — NEVER VIOLATE
═══════════════════════════════════════════

- NEVER make up numbers. Only use numbers from tools and the fairness engine result.
- NEVER override the Fairness Engine decision. You EXPLAIN, you don't DECIDE.
- NEVER use technical jargon. Write for a village panchayat leader.
- ALWAYS mention if mitigation was applied and what it did.
- ALWAYS connect findings to real human impact.
- ALWAYS compare this applicant's situation to the known bias
  patterns from the offline investigation.
- If this applicant is Rural or Daily Wage, flag immediately
  that they belong to a known discriminated group.

═══════════════════════════════════════════
OUTPUT FORMAT — ALWAYS USE THIS EXACTLY
═══════════════════════════════════════════

## DECISION
[APPROVED or DENIED] — [confidence %]

## MODEL SCORE & THRESHOLD
[Raw model score: X.XX]
[Standard threshold: 0.50]
[Adjusted threshold: X.XX (if mitigation applied)]
[Rule applied: name of the rule]

## WHY THIS DECISION
[Top 3 features that drove this decision, in plain language.
 Example: "Your credit score was the biggest factor at X impact.
 Your region added Y impact against you."]

## FAIRNESS CHECK
[Was mitigation applied? YES/NO]
[If YES: explain what the original decision would have been and why it was changed]
[If NO: explain why no adjustment was needed]
[Does this person belong to a known discriminated group?
 Compare their approval rate to overall dataset averages.
 Be direct — say YES or NO and why.]

## POLICY FLAG
[GREEN / YELLOW / RED]
[Explain what this means:
 GREEN = standard decision, no concerns
 YELLOW = mitigation changed the outcome, transparency required
 RED = denied despite mitigation + disadvantaged group, human review needed]

## WHAT WOULD CHANGE THIS DECISION
[List every counterfactual combination that flipped the decision.
 Example: "If your region was Urban instead of Rural → APPROVED"
 If nothing flips it → say what financial improvements would help.]

## RECOMMENDATION
[One concrete actionable step this person can take.
 Plain language. What a village panchayat leader would understand.]
"""


# ─────────────────────────────────────────────
# Agent Factory
# ─────────────────────────────────────────────

def _get_agent(findings: dict):
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.environ.get("GROQ_API_KEY"),
        temperature=0,
    )
    agent = create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=_build_system_prompt(findings),
    )
    return agent


# ─────────────────────────────────────────────
# Online Entry Point — Individual Applicant
# ─────────────────────────────────────────────

def investigate_applicant(applicant: dict, findings: dict, fair_result: dict = None) -> dict:
    """
    Called on every /predict request.
    findings: loaded from offline_findings.json by main.py on startup.
    applicant: dict of applicant attributes from user form.
    fair_result: output from fairness_engine.apply_fair_decision().
    Returns structured analysis.
    """
    agent = _get_agent(findings)

    # Build context message including fairness engine output
    fairness_context = ""
    if fair_result:
        fairness_context = f"""

═══════════════════════════════════════════
FAIRNESS ENGINE RESULT (already decided — do NOT override)
═══════════════════════════════════════════
Raw Model Score: {fair_result['raw_score']}
Default Threshold: {fair_result['default_threshold']}
Adjusted Threshold: {fair_result['adjusted_threshold']}
Original Decision (before mitigation): {fair_result['original_decision']}
Final Decision (after mitigation): {fair_result['final_decision']}
Confidence: {fair_result['confidence']}
Mitigation Applied: {fair_result['mitigation_applied']}
Mitigation Rule: {fair_result['mitigation_details']['rule_name']}
Mitigation Reason: {fair_result['mitigation_details']['reason']}
Policy Flag: {fair_result['policy_flag']['level']} — {fair_result['policy_flag']['label']}
Policy Detail: {fair_result['policy_flag']['detail']}
Is Disadvantaged Group: {fair_result['is_disadvantaged']}
Disadvantaged Labels: {fair_result['disadvantaged_groups']}
"""

    result = agent.invoke({
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Analyze this individual loan applicant:\n"
                    f"{json.dumps(applicant, indent=2)}\n"
                    f"{fairness_context}\n\n"
                    f"Follow your investigation protocol exactly. "
                    f"Run get_feature_importance first, then run_counterfactual "
                    f"in manual mode with all combinations listed. "
                    f"Then write your full explanation report. "
                    f"Remember: the decision is ALREADY MADE by the Fairness Engine. "
                    f"You are explaining it, not deciding."
                )
            }
        ]
    })

    final_message = result["messages"][-1].content

    return {
        "applicant": applicant,
        "analysis": final_message,
        "status": "complete"
    }