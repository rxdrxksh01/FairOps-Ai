import { NavLink } from 'react-router-dom'

const HIGHLIGHTS = [
  {
    title: 'Bias-aware review',
    body: 'Surface fairness issues early without making the interface feel heavy or difficult to scan.',
    tag: '01',
  },
  {
    title: 'Clear predictions',
    body: 'Run an applicant check and read the reasoning in plain language instead of decoding complex output.',
    tag: '02',
  },
  {
    title: 'Simple audit trail',
    body: 'Track what happened, when it happened, and why, in a format that is easy to revisit.',
    tag: '03',
  },
]

const PREVIEW_ROWS = [
  {
    label: 'Dashboard',
    detail: 'See approval rate, applicant count, and key bias signals at a glance.',
    meta: 'Best for daily review',
  },
  {
    label: 'Prediction',
    detail: 'Submit one applicant profile and get a decision with explanation.',
    meta: 'Best for case analysis',
  },
  {
    label: 'Audit log',
    detail: 'Review previous outcomes and expand any case when you need context.',
    meta: 'Best for traceability',
  },
]

export default function Landing() {
  return (
    <div className="landing-page">
      <header className="landing-nav">
        <NavLink className="brand" to="/">
          <span className="brand__mark">F</span>
          <span>
            <strong>FairCare AI</strong>
            <em>Bias-aware loan review</em>
          </span>
        </NavLink>

        <nav className="landing-nav__links">
          <a href="#capabilities">Capabilities</a>
          <a href="#preview">Preview</a>
        </nav>
      </header>

      <main>
        <section className="hero">
          <div className="hero__copy">
            <p className="eyebrow">Bias-aware loan review for real teams</p>
            <h1>
              Fair lending tools that stay <span>clear under pressure.</span>
            </h1>
            <p className="hero__description">
              FairCare AI brings your key review tasks into one consistent workspace:
              understand bias signals, test an applicant, and inspect every past decision.
            </p>
            <div className="hero__actions">
              <NavLink className="button" to="/insights">
                Open workspace
              </NavLink>
            </div>
            <div className="hero__stats">
              <div>
                <strong>3 pages</strong>
                <span>dashboard, prediction, audit</span>
              </div>
              <div>
                <strong>Live flow</strong>
                <span>ready to connect and test</span>
              </div>
              <div>
                <strong>Focused UX</strong>
                <span>built for review work</span>
              </div>
            </div>
          </div>

          <div className="hero__visual" aria-hidden="true">
            <div className="hero__panel hero__panel--large">
              <span>One place to work</span>
              <strong>Review the data, run a case, and check the audit trail without jumping between unrelated screens.</strong>
            </div>
            <div className="hero__panel hero__panel--metric">
              <span>Main view</span>
              <strong>Dashboard first</strong>
            </div>
            <div className="hero__panel hero__panel--metric hero__panel--metric-alt">
              <span>Primary goal</span>
              <strong>Better decisions</strong>
            </div>
          </div>
        </section>

        <section className="feature-strip" id="capabilities">
          {HIGHLIGHTS.map((item) => (
            <article key={item.title} className="feature-row">
              <div className="feature-row__index">{item.tag}</div>
              <div className="feature-row__content">
                <h2>{item.title}</h2>
                <p>{item.body}</p>
              </div>
            </article>
          ))}
        </section>

        <section className="landing-map" id="preview">
          <article className="landing-map__main">
            <div className="landing-map__header">
              <div>
                <p className="eyebrow">Workspace preview</p>
                <h2>Three pages, one consistent flow.</h2>
                <p className="landing-map__copy">
                  The experience is organized around the three things a user actually needs to do, in the order they usually do them.
                </p>
              </div>
            </div>

            <div className="workspace-flow">
              {PREVIEW_ROWS.map((row, index) => (
                <div key={row.label} className="workspace-flow__item">
                  <div className="workspace-flow__step">0{index + 1}</div>
                  <div className="workspace-flow__body">
                    <strong>{row.label}</strong>
                    <span>{row.detail}</span>
                    <em>{row.meta}</em>
                  </div>
                </div>
              ))}
            </div>
          </article>
        </section>
      </main>
    </div>
  )
}
