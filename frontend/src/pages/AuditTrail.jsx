import { useEffect, useState } from 'react'
import axios from 'axios'
import { EmptyState, PageHero, Panel, SectionLabel, StatCard } from '../components/ui'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const FLAG_COLORS = {
  GREEN: '#7ec29a',
  YELLOW: '#e0a55a',
  RED: '#f08b92',
}

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

export default function AuditTrail() {
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(null)

  const load = (showSpinner = true) => {
    if (showSpinner) {
      setLoading(true)
    }
    axios
      .get(`${API}/audit-log`)
      .then((response) => setEntries(response.data.entries || []))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    axios
      .get(`${API}/audit-log`)
      .then((response) => setEntries(response.data.entries || []))
      .finally(() => setLoading(false))
  }, [])

  const clear = async () => {
    await axios.delete(`${API}/audit-log`)
    setEntries([])
  }

  const approved = entries.filter((entry) => entry.decision === 'APPROVED').length
  const denied = entries.filter((entry) => entry.decision === 'DENIED').length
  const mitigated = entries.filter((entry) => entry.fairness?.mitigation_applied).length

  return (
    <div className="page-stack">
      <PageHero
        eyebrow="Decision archive"
        title="Review previous decisions."
        description="A clean history of what happened, when it happened, and what reasoning supported the outcome."
        actions={
          <>
            <button className="button button--ghost" onClick={load}>
              Refresh log
            </button>
            <button className="button button--danger" onClick={clear}>
              Clear log
            </button>
          </>
        }
      />

      <section className="stats-grid stats-grid--4">
        <StatCard label="Total decisions" value={entries.length} hint="All logged evaluations." accent="clear" />
        <StatCard label="Approved" value={approved} hint="Positive outcomes." accent="soft" />
        <StatCard label="Denied" value={denied} hint="Cases needing further review." accent="warm" />
        <StatCard label="Mitigated" value={mitigated} hint="Decisions changed by fairness layer." accent="clear" />
      </section>

      {loading ? (
        <Panel className="state-card">
          <div className="orb-spinner" />
          <strong>Loading audit entries</strong>
        </Panel>
      ) : null}

      {!loading && entries.length === 0 ? (
        <EmptyState
          title="No decisions logged yet"
          detail="Run a prediction first and it will appear here."
        />
      ) : null}

      <div className="audit-list">
        {entries.map((entry) => {
          const fairness = entry.fairness
          const flagColor = fairness ? FLAG_COLORS[fairness.policy_flag] || '#aab3c4' : null

          return (
            <Panel key={entry.id} className="audit-entry">
              <button
                className="audit-entry__summary"
                onClick={() => setExpanded(expanded === entry.id ? null : entry.id)}
                type="button"
              >
                <div className={`audit-badge audit-badge--${entry.decision?.toLowerCase() || 'denied'}`}>
                  {entry.decision}
                </div>

                {/* Policy flag dot */}
                {flagColor ? (
                  <span
                    style={{
                      width: '0.65rem',
                      height: '0.65rem',
                      borderRadius: '999px',
                      background: flagColor,
                      boxShadow: `0 0 6px ${flagColor}`,
                      flexShrink: 0,
                    }}
                    title={`Policy: ${fairness.policy_flag}`}
                  />
                ) : null}

                <div className="audit-entry__meta">
                  <strong>
                    {entry.applicant?.region} · {entry.applicant?.employment_type} · Age {entry.applicant?.age}
                  </strong>
                  <span>
                    #{entry.id} · ₹{entry.applicant?.income_monthly?.toLocaleString()}/mo ·{' '}
                    {new Date(entry.timestamp).toLocaleString()}
                    {fairness?.mitigation_applied ? ' · ⚖ Mitigated' : ''}
                  </span>
                </div>
                <span className="audit-entry__toggle">{expanded === entry.id ? 'Hide' : 'Open'}</span>
              </button>

              {expanded === entry.id ? (
                <div className="audit-entry__detail">
                  {fairness?.mitigation_applied ? (
                    <div className="mitigation-note" style={{ marginBottom: '1.5rem', marginTop: 0 }}>
                      <span className="mitigation-note__icon">⚖</span>
                      <div>
                        <strong>Fairness adjustment applied</strong>
                        <p style={{ margin: 0 }}>
                          Without fairness adjustment this would have been <strong>{fairness.original_decision}</strong>. 
                          Adjusted for: <em>{fairness.mitigation_rule}</em>.
                        </p>
                      </div>
                    </div>
                  ) : null}

                  <SectionLabel>Explanation</SectionLabel>
                  <AnalysisView text={entry.full_analysis || entry.analysis_preview} />
                </div>
              ) : null}
            </Panel>
          )
        })}
      </div>
    </div>
  )
}
