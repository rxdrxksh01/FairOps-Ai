import { NavLink } from 'react-router-dom'

const CAPABILITIES = [
  'Dataset fairness dashboard',
  'Applicant-level prediction review',
  'Decision audit trail',
]

const PREVIEW_METRICS = [
  { label: 'Applicants', value: '1,248' },
  { label: 'Approval rate', value: '61.8%' },
  { label: 'High-risk groups', value: '3' },
  { label: 'Audit entries', value: 'Live' },
]

const QUEUE = [
  { name: 'Rural · Daily Wage', status: 'Bias review', tone: 'danger' },
  { name: 'Semi-Urban · Salaried', status: 'Clear', tone: 'success' },
  { name: 'Urban · Self-Employed', status: 'Check income', tone: 'warn' },
]

export default function Landing() {
  return (
    <div className="landing-page">
      <header className="landing-nav">
        <NavLink className="brand" to="/">
          <span className="brand__mark">F</span>
          <span>
            <strong>FairCare AI</strong>
            <em>Loan fairness operations</em>
          </span>
        </NavLink>

        <nav className="landing-nav__links">
          <a href="#product">Product</a>
          <a href="#controls">Controls</a>
        </nav>
      </header>

      <main>
        <section className="saas-hero">
          <div className="saas-hero__copy">
            <p className="eyebrow">Medical loan decisions with fairness checks</p>
            <h1>Review loan risk before bias becomes policy.</h1>
            <p>
              FairCare AI gives lending teams a focused command center for approval
              trends, applicant simulations, and traceable decision history.
            </p>
            <NavLink className="button" to="/insights">
              Launch dashboard
            </NavLink>
          </div>

          <div className="product-preview" id="product" aria-label="FairCare AI dashboard preview">
            <div className="product-preview__top">
              <div>
                <span>Fairness dashboard</span>
                <strong>Portfolio health</strong>
              </div>
              <b>Critical review</b>
            </div>

            <div className="preview-metrics">
              {PREVIEW_METRICS.map((metric) => (
                <div key={metric.label}>
                  <span>{metric.label}</span>
                  <strong>{metric.value}</strong>
                </div>
              ))}
            </div>

            <div className="preview-board">
              <div className="preview-chart">
                <span style={{ height: '34%' }} />
                <span style={{ height: '58%' }} />
                <span style={{ height: '82%' }} />
                <span style={{ height: '46%' }} />
                <span style={{ height: '68%' }} />
              </div>

              <div className="preview-queue">
                {QUEUE.map((item) => (
                  <div key={item.name} className="preview-queue__row">
                    <span className={`status-dot status-dot--${item.tone}`} />
                    <div>
                      <strong>{item.name}</strong>
                      <small>{item.status}</small>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="capability-band" id="controls">
          <p className="eyebrow">What teams can do</p>
          <div className="capability-band__grid">
            {CAPABILITIES.map((item) => (
              <div key={item} className="capability-item">
                <span />
                <strong>{item}</strong>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}
