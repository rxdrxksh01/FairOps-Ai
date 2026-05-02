import { useEffect, useState } from 'react'
import axios from 'axios'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { LoadingState, Panel, SectionLabel } from '../components/ui'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const SEV = {
  CRITICAL: { color: '#f08b92', bg: 'rgba(240,139,146,0.10)' },
  HIGH:     { color: '#e0a55a', bg: 'rgba(224,165,90,0.10)' },
  MODERATE: { color: '#e0d06e', bg: 'rgba(224,208,110,0.10)' },
  LOW:      { color: '#7ec29a', bg: 'rgba(126,194,154,0.10)' },
}

function ReportView({ text }) {
  if (!text) return null

  const blocks = text
    .split(/\n(?=## )/)
    .map((block) => block.trim())
    .filter(Boolean)

  return (
    <div className="report-sections">
      {blocks.map((block, idx) => {
        const lines = block.split('\n')
        const rawHeading = lines[0]?.startsWith('## ') ? lines[0].replace('## ', '').trim() : 'Report'
        const heading = rawHeading.replace(/[^\x20-\x7E]/g, '').trim() || rawHeading
        const contentLines = lines.slice(1).filter((line) => line.trim())
        const listItems = contentLines.filter((line) => line.trim().startsWith('- '))
        const bodyText = contentLines
          .filter((line) => !line.trim().startsWith('- '))
          .join('\n')
          .trim()

        return (
          <article key={`${heading}-${idx}`} className="report-block">
            <h3 className="report-heading">{heading}</h3>
            {bodyText ? <p className="report-body">{bodyText}</p> : null}
            {listItems.length ? (
              <ul className="report-list">
                {listItems.map((item, i) => (
                  <li key={`${idx}-${i}`}>{item.replace(/^- /, '').trim()}</li>
                ))}
              </ul>
            ) : null}
          </article>
        )
      })}
    </div>
  )
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
        <p>Make sure the API is running and reachable.</p>
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
  const reviewQueue = [
    { label: 'Worst disparate impact', value: metrics?.worst_disparate_impact || 'n/a' },
    { label: 'Severity', value: overall },
    { label: 'Action', value: overall === 'LOW' ? 'Monitor' : 'Review cases' },
  ]

  return (
    <div className="dashboard-page">
      <section className="dashboard-header">
        <div>
          <p className="eyebrow">Fairness dashboard</p>
          <h2>Portfolio overview</h2>
          <p>Track approval patterns, exposed groups, and fairness metrics before individual cases are reviewed.</p>
        </div>
        <div className={`severity-badge severity-badge--${overall.toLowerCase()}`}>
          {overall}
        </div>
      </section>

      <section className="kpi-strip">
        <div className="kpi-card">
          <span>Total applicants</span>
          <strong>{dataset_summary.total_rows?.toLocaleString() || '0'}</strong>
          <p>Current dataset</p>
        </div>
        <div className="kpi-card">
          <span>Approval rate</span>
          <strong>{Math.round((dataset_summary.approval_rate || 0) * 100)}%</strong>
          <p>Portfolio baseline</p>
        </div>
        <div className="kpi-card">
          <span>Bias status</span>
          <strong>{overall}</strong>
          <p>{metrics ? `DI ratio ${metrics.worst_disparate_impact}` : 'Awaiting metrics'}</p>
        </div>
        <div className="kpi-card kpi-card--accent">
          <span>Next step</span>
          <strong>{overall === 'LOW' ? 'Monitor' : 'Review'}</strong>
          <p>Use prediction page for case checks</p>
        </div>
      </section>

      <section className="dashboard-grid">
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

        <Panel className="review-panel">
          <SectionLabel>Review queue</SectionLabel>
          <div className="review-list">
            {reviewQueue.map((item) => (
              <div key={item.label} className="review-list__row">
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>
        </Panel>
      </section>

      {metrics ? (
        <Panel>
          <SectionLabel>Fairness scorecard</SectionLabel>
          <p className="panel-subtitle">
            Formal metrics by demographic dimension.
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

      <Panel className="report-panel">
        <SectionLabel>Investigation narrative</SectionLabel>
        <ReportView text={investigation_report} />
      </Panel>
    </div>
  )
}
