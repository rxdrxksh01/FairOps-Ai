# FairCare AI

Bias-aware medical loan decision support system with:
- a FastAPI backend for scoring + fairness mitigation + audit logging
- a React frontend for dashboard, simulation, and audit review
- an LLM explainer layer that generates plain-language case reports

## What This Project Does

FairCare AI runs a deterministic decision pipeline first, then asks an LLM agent to explain the result.

Core flow:
1. Applicant profile is submitted from the `Predict` page.
2. Backend model computes approval probability.
3. Fairness engine adjusts threshold rules for known disadvantaged patterns.
4. Final decision is set (`APPROVED` / `DENIED`) with policy flag (`GREEN` / `YELLOW` / `RED`).
5. LLM agent generates a structured explanation with counterfactuals.
6. Full record is written to audit log and shown in `Audit Trail`.

## Repository Structure

```text
faircare-ai/
  backend/
    main.py                 # FastAPI app and routes
    fairness_engine.py      # threshold-based mitigation + fairness metrics
    agent.py                # LLM explainer orchestration
    audit_log.py            # file-backed audit trail (JSONL)
    offline_investigate.py  # one-time/offline artifact generation
    requirements.txt
  frontend/
    src/
      pages/
        Landing.jsx
        Dashboard.jsx
        Predict.jsx
        AuditTrail.jsx
      App.jsx
    package.json
  data/
    sample_medical_loans.csv
```

## Product Workflow (UI)

### 1) Dashboard (`/insights`)
- Shows dataset-level approval patterns by region/employment.
- Shows fairness scorecard (DI ratio + severity by dimension).
- Helps reviewers understand systemic bias before case-level simulation.

### 2) Predict (`/simulate`)
- Enter applicant profile fields.
- Runs full backend pipeline.
- Returns:
  - final decision
  - confidence
  - policy flag details
  - full explanation sections (decision, thresholds, fairness check, recommendation, what-if changes)

### 3) Audit Trail (`/audit`)
- Displays every previous prediction entry.
- Stores and shows full explanation for each case.
- Supports refresh/clear for operational review.

## Backend Architecture

### Deterministic Fairness Decision
`backend/fairness_engine.py`:
- Computes `raw_score` via model `predict_proba`
- Applies threshold rules:
  - single-feature thresholds
  - composite thresholds (intersectional conditions)
- Produces:
  - `original_decision`
  - `final_decision`
  - `mitigation_applied`
  - `policy_flag`
  - `disadvantaged_groups`

### LLM Explanation Layer
`backend/agent.py`:
- Loads tools (`feature importance`, `counterfactual`, approval-by-group signals)
- Builds a constrained explanation prompt
- Explains the deterministic fairness decision (does not override it)

### Audit Logging
`backend/audit_log.py`:
- Persists every prediction to `backend/audit_trail.jsonl`
- Stores applicant snapshot, decision, summary, full analysis, and fairness metadata

## API Endpoints

Base URL: `http://localhost:8000`

- `GET /` - service info and readiness
- `GET /health` - health + artifacts loaded + key presence check
- `GET /dataset-info` - dataset summary and investigation report
- `GET /fairness-config` - threshold and disadvantaged-group config
- `GET /fairness-metrics` - dataset-level fairness metrics
- `POST /predict` - full simulation pipeline for one applicant
- `GET /audit-log` - all audit entries (newest first)
- `DELETE /audit-log` - clear audit entries

## Local Setup

## Prerequisites
- Python 3.12+
- Node.js 18+
- npm

## 1) Backend setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:

```bash
GROQ_API_KEY=your_key_here
```

## 2) Frontend setup

```bash
cd frontend
npm install
```

## 3) Start services

Backend:

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

Open:
- Frontend: `http://localhost:5173`
- Backend docs: `http://localhost:8000/docs`

## Offline Artifacts (Important)

`main.py` expects offline artifacts (model + findings) to be available at startup.

If backend reports artifacts are not loaded, run:

```bash
cd backend
source venv/bin/activate
python3 offline_investigate.py
```

This should generate:
- `backend/model.pkl`
- `backend/label_encoders.pkl`
- `backend/offline_findings.json`

## Troubleshooting

- `Backend not connected` in UI:
  - Ensure backend is running on port `8000`
  - Check `GET /health`

- `Artifacts not loaded` from API:
  - Run `offline_investigate.py`
  - Confirm files listed above exist

- Predict route failing with LLM error:
  - Verify `GROQ_API_KEY` is valid
  - Restart backend after editing `.env`

- Audit list empty:
  - Run at least one simulation from `/simulate`

## Tech Stack

- Backend: FastAPI, scikit-learn, pandas, fairlearn, LangGraph/LangChain
- Frontend: React, Vite, Recharts, Axios, React Router
- Storage: JSONL audit file

## Notes

- This project supports decision transparency, not fully autonomous lending approval.
- Policy `RED` outcomes are designed to trigger human review.
