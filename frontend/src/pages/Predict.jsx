import { useState } from 'react'
import axios from 'axios'
import { PageHero, Panel, SectionLabel } from '../components/ui'

const API = 'http://localhost:8000'

const DEFAULTS = {
  age: 45,
  gender: 'Male',
  region: 'Rural',
  employment_type: 'Daily Wage',
  income_monthly: 12000,
  credit_score: 620,
  loan_amount_requested: 150000,
  existing_loans: 1,
  medical_condition: 'Cardiac',
}

const FIELD_GROUPS = [
  { key: 'age', label: 'Age', type: 'number' },
  { key: 'gender', label: 'Gender', options: ['Male', 'Female'] },
  { key: 'region', label: 'Region', options: ['Rural', 'Semi-Urban', 'Urban'] },
  { key: 'employment_type', label: 'Employment type', options: ['Daily Wage', 'Salaried', 'Self-Employed', 'Unemployed'] },
  { key: 'income_monthly', label: 'Monthly income (₹)', type: 'number' },
  { key: 'credit_score', label: 'Credit score', type: 'number' },
  { key: 'loan_amount_requested', label: 'Loan amount (₹)', type: 'number' },
  { key: 'existing_loans', label: 'Existing loans', type: 'number' },
  { key: 'medical_condition', label: 'Medical condition', options: ['Cardiac', 'Cancer', 'Orthopedic', 'Neurological', 'General'] },
]

const FLAG_MAP = {
  GREEN:  { icon: '✓', label: 'Standard decision',      color: '#7ec29a', bg: 'rgba(126,194,154,0.08)', border: 'rgba(126,194,154,0.22)' },
  YELLOW: { icon: '⚖', label: 'Fairness-adjusted',       color: '#e0a55a', bg: 'rgba(224,165,90,0.08)',  border: 'rgba(224,165,90,0.22)' },
  RED:    { icon: '⚑', label: 'Needs human review', color: '#f08b92', bg: 'rgba(240,139,146,0.08)', border: 'rgba(240,139,146,0.22)' },
}

/* ── tiny markdown-ish renderer for ## headings + paragraphs ── */
function AnalysisView({ text }) {
  if (!text) return null
  const blocks = text.split(/\n(?=## )/)
  return (
    <div className="analysis-sections">
      {blocks.map((block, i) => {
        const lines = block.trim().split('\n')
        const heading = lines[0]?.startsWith('## ') ? lines[0].replace('## ', '') : null
        const body = heading ? lines.slice(1).join('\n').trim() : block.trim()
        return (
          <div key={i} className="analysis-block">
            {heading ? <h3 className="analysis-heading">{heading}</h3> : null}
            {body ? <p className="analysis-body">{body}</p> : null}
          </div>
        )
      })}
    </div>
  )
}

export default function Predict() {
  const [form, setForm] = useState(DEFAULTS)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const update = (key, value) => setForm((c) => ({ ...c, [key]: value }))

  const submit = async () => {
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const r = await axios.post(`${API}/predict`, { applicant: form })
      setResult(r.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Prediction failed')
    } finally {
      setLoading(false)
    }
  }

  const f = result?.fairness
  const flag = f ? FLAG_MAP[f.policy_flag?.level] || FLAG_MAP.GREEN : null

  return (
    <div className="page-stack">
      <PageHero
        eyebrow="Applicant simulation"
        title="Test an applicant with bias-aware review."
        description="Enter a profile, run the fairness-aware model, and review the outcome with full explanation."
      />

      <section className="predict-layout">
        {/* ── Form ── */}
        <Panel className="predict-form-panel">
          <SectionLabel>Applicant details</SectionLabel>
          <div className="form-grid">
            {FIELD_GROUPS.map((fd) => (
              <label className="field" key={fd.key}>
                <span>{fd.label}</span>
                {fd.options ? (
                  <select value={form[fd.key]} onChange={(e) => update(fd.key, e.target.value)}>
                    {fd.options.map((o) => <option key={o}>{o}</option>)}
                  </select>
                ) : (
                  <input
                    type="number"
                    value={form[fd.key]}
                    onChange={(e) => update(fd.key, Number.parseInt(e.target.value || '0', 10))}
                  />
                )}
              </label>
            ))}
          </div>
          <button className="button button--full" disabled={loading} onClick={submit}>
            {loading ? 'Running analysis…' : 'Analyze application'}
          </button>
        </Panel>

        {/* ── Results ── */}
        <div className="result-stack">
          {loading ? (
            <Panel className="state-card">
              <div className="orb-spinner" />
              <strong>Running fairness-aware analysis</strong>
              <p>Scoring, checking bias thresholds, generating explanation…</p>
            </Panel>
          ) : null}

          {error ? (
            <Panel tone="danger" className="state-card state-card--compact">
              <strong>Error</strong>
              <p>{error}</p>
            </Panel>
          ) : null}

          {result ? (
            <>
              {/* ── Hero decision card ── */}
              <div className={`verdict-card verdict-card--${result.decision?.toLowerCase() || 'denied'}`}>
                <div className="verdict-card__top">
                  <span className="verdict-card__label">Decision</span>
                  <span className="verdict-card__id">#{result.audit_id}</span>
                </div>
                <strong className="verdict-card__decision">{result.decision}</strong>
                {f ? (
                  <span className="verdict-card__confidence">
                    {(f.confidence * 100).toFixed(0)}% confidence
                  </span>
                ) : null}
              </div>

              {/* ── Policy flag pill ── */}
              {flag ? (
                <div className="flag-pill" style={{ background: flag.bg, borderColor: flag.border }}>
                  <span className="flag-pill__icon" style={{ color: flag.color }}>{flag.icon}</span>
                  <div className="flag-pill__text">
                    <strong style={{ color: flag.color }}>{flag.label}</strong>
                    <span>{f.policy_flag?.detail}</span>
                  </div>
                </div>
              ) : null}

              {/* ── Mitigation note (only if applied) ── */}
              {f?.mitigation_applied ? (
                <div className="mitigation-note">
                  <span className="mitigation-note__icon">⚖</span>
                  <div>
                    <strong>Bias mitigation changed this outcome</strong>
                    <p>
                      Without fairness adjustment this would have been <strong>{f.original_decision}</strong>.
                      The threshold was adjusted for <em>{f.mitigation_details?.rule_name}</em> to
                      correct for known bias patterns.
                    </p>
                  </div>
                </div>
              ) : null}

              {/* ── Analysis ── */}
              <Panel>
                <SectionLabel>Full analysis</SectionLabel>
                <AnalysisView text={result.analysis} />
              </Panel>
            </>
          ) : null}

          {!loading && !error && !result ? (
            <Panel className="result-placeholder">
              <SectionLabel>Prediction output</SectionLabel>
              <strong>No simulation yet</strong>
              <p>Fill out the applicant profile and run the analysis.</p>
              <div className="result-placeholder__steps">
                <span>1 ·  Enter applicant details</span>
                <span>2 ·  Run the bias-aware analysis</span>
                <span>3 ·  Review decision and explanation</span>
              </div>
            </Panel>
          ) : null}
        </div>
      </section>
    </div>
  )
}
