import { useEffect, useState } from 'react'
import axios from 'axios'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { LoadingState, PageHero, Panel, SectionLabel, StatCard } from '../components/ui'

const API = 'http://localhost:8000'

const SEV = {
  CRITICAL: { color: '#f08b92', bg: 'rgba(240,139,146,0.10)' },
  HIGH:     { color: '#e0a55a', bg: 'rgba(224,165,90,0.10)' },
  MODERATE: { color: '#e0d06e', bg: 'rgba(224,208,110,0.10)' },
  LOW:      { color: '#7ec29a', bg: 'rgba(126,194,154,0.10)' },
}

export default function Dashboard() {
  const [info, setInfo] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      axios.get(`${API}/dataset-info`).then((r) => r.data).catch(() => null),
      axios.get(`${API}/fairness-metrics`).then((r) => r.data).catch(() => null),
    ]).then(([infoData, metricsData]) => {
      setInfo(infoData)
      setMetrics(metricsData)
      setLoading(false)
    })
  }, [])

  if (loading) {
    return (
      <LoadingState
        title="Loading investigation report"
        detail="Pulling dataset signals and fairness findings."
      />
    )
  }

  if (!info) {
    return (
      <Panel tone="danger" className="state-card state-card--compact">
        <strong>Backend not connected</strong>
        <p>Make sure the API is running on localhost:8000.</p>
      </Panel>
    )
  }

  const { dataset_summary, investigation_report } = info
  const regionData = Object.entries(dataset_summary.approval_by_region || {}).map(([name, rate]) => ({
    name,
    rate: Math.round(rate * 100),
  }))
  const employmentData = Object.entries(dataset_summary.approval_by_employment || {}).map(
    ([name, rate]) => ({ name, rate: Math.round(rate * 100) }),
  )

  const overall = metrics?.overall_severity || 'Unknown'
  const sev = SEV[overall] || SEV.LOW

  return (
    <div className="page-stack">
      <PageHero
        eyebrow="Investigation report"
        title="Dataset fairness at a glance."
        description="Headline numbers, approval patterns, and formal bias metrics — everything a reviewer needs before testing individual applicants."
        aside={
          <div className="mini-metrics">
            <div>
              <span>Rows</span>
              <strong>{dataset_summary.total_rows?.toLocaleString()}</strong>
            </div>
            <div>
              <span>Approval</span>
              <strong>{Math.round((dataset_summary.approval_rate || 0) * 100)}%</strong>
            </div>
          </div>
        }
      />

      {/* ── Headline Stats ── */}
      <section className="stats-grid">
        <StatCard
          label="Total applicants"
          value={dataset_summary.total_rows?.toLocaleString() || '0'}
          hint="Included in the current snapshot."
          accent="clear"
        />
        <StatCard
          label="Overall approval"
          value={`${Math.round((dataset_summary.approval_rate || 0) * 100)}%`}
          hint="Baseline before comparing groups."
          accent="soft"
        />
        <StatCard
          label="Bias status"
          value={overall}
          hint={metrics ? `Disparate impact: ${metrics.worst_disparate_impact}` : ''}
          accent="warm"
        />
      </section>

      {/* ── Approval Charts ── */}
      <section className="chart-grid">
        <Panel>
          <SectionLabel>Approval by region</SectionLabel>
          <div className="chart-frame">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={regionData}>
                <XAxis dataKey="name" tick={{ fill: '#aab3c4', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#808a9d', fontSize: 12 }} domain={[0, 100]} axisLine={false} tickLine={false} unit="%" />
                <Tooltip
                  cursor={{ fill: 'rgba(143,168,255,0.06)' }}
                  contentStyle={{ background: '#1c202a', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '12px', color: '#edf1f7' }}
                  formatter={(v) => [`${v}%`, 'Approval']}
                />
                <Bar dataKey="rate" radius={[10, 10, 4, 4]}>
                  {regionData.map((e) => (
                    <Cell key={e.name} fill={e.rate < 30 ? '#f08b92' : e.rate < 60 ? '#e0a55a' : '#7ec29a'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel>
          <SectionLabel>Approval by employment</SectionLabel>
          <div className="chart-frame">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={employmentData}>
                <XAxis dataKey="name" tick={{ fill: '#aab3c4', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#808a9d', fontSize: 12 }} domain={[0, 100]} axisLine={false} tickLine={false} unit="%" />
                <Tooltip
                  cursor={{ fill: 'rgba(143,168,255,0.06)' }}
                  contentStyle={{ background: '#1c202a', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '12px', color: '#edf1f7' }}
                  formatter={(v) => [`${v}%`, 'Approval']}
                />
                <Bar dataKey="rate" radius={[10, 10, 4, 4]}>
                  {employmentData.map((e) => (
                    <Cell key={e.name} fill={e.rate < 30 ? '#f08b92' : e.rate < 60 ? '#e0a55a' : '#7ec29a'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </section>

      {/* ── Fairness Scorecard — clean summary only ── */}
      {metrics ? (
        <Panel>
          <SectionLabel>Fairness scorecard</SectionLabel>
          <p className="panel-subtitle">
            Formal metrics per demographic dimension.
          </p>

          <div className="scorecard-grid">
            {Object.entries(metrics.metrics_by_group || {}).map(([key, m]) => {
              const s = SEV[m.severity] || SEV.LOW
              return (
                <div key={key} className="scorecard-item">
                  <div className="scorecard-item__head">
                    <strong>{m.label}</strong>
                    <span className="scorecard-pill" style={{ background: s.bg, color: s.color }}>
                      {m.severity}
                    </span>
                  </div>

                  {/* Mini group bars */}
                  <div className="scorecard-bars">
                    {Object.entries(m.group_details || {}).map(([group, d]) => (
                      <div key={group} className="scorecard-bar-row">
                        <span>{group}</span>
                        <div className="scorecard-track">
                          <div
                            className="scorecard-fill"
                            style={{
                              width: `${d.rate * 100}%`,
                              background: d.gap_vs_privileged < -0.2
                                ? '#f08b92'
                                : d.gap_vs_privileged < -0.05
                                  ? '#e0a55a'
                                  : '#7ec29a',
                            }}
                          />
                        </div>
                        <strong>{(d.rate * 100).toFixed(0)}%</strong>
                      </div>
                    ))}
                  </div>

                  <div className="scorecard-footer">
                    <span>DI ratio <strong style={{ color: m.four_fifths_rule_pass ? '#7ec29a' : '#f08b92' }}>{m.disparate_impact}</strong></span>
                    <span>Status <strong style={{ color: m.four_fifths_rule_pass ? '#7ec29a' : '#f08b92' }}>{m.four_fifths_rule_pass ? 'Pass' : 'Review'}</strong></span>
                  </div>
                </div>
              )
            })}
          </div>
        </Panel>
      ) : null}

      {/* ── Investigation Narrative ── */}
      <Panel className="report-panel">
        <SectionLabel>Investigation narrative</SectionLabel>
        <p className="report-copy">{investigation_report}</p>
      </Panel>
    </div>
  )
}
