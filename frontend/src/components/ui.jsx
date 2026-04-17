export function PageHero({ eyebrow, title, description, actions, aside }) {
  return (
    <section className="page-hero">
      <div className="page-hero__copy">
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        <p className="page-hero__description">{description}</p>
        {actions ? <div className="page-hero__actions">{actions}</div> : null}
      </div>
      {aside ? <div className="page-hero__aside">{aside}</div> : null}
    </section>
  )
}

export function Panel({ children, className = '', tone = 'default' }) {
  const classes = ['panel', tone !== 'default' ? `panel--${tone}` : '', className]
    .filter(Boolean)
    .join(' ')

  return <section className={classes}>{children}</section>
}

export function SectionLabel({ children }) {
  return <p className="section-label">{children}</p>
}

export function StatCard({ label, value, hint, accent = 'gold' }) {
  return (
    <article className={`stat-card stat-card--${accent}`}>
      <span className="section-label">{label}</span>
      <strong>{value}</strong>
      {hint ? <p>{hint}</p> : null}
    </article>
  )
}

export function LoadingState({ title = 'Loading...', detail = 'Please wait a moment.' }) {
  return (
    <Panel className="state-card">
      <div className="orb-spinner" />
      <strong>{title}</strong>
      <p>{detail}</p>
    </Panel>
  )
}

export function EmptyState({ title, detail }) {
  return (
    <Panel className="state-card">
      <strong>{title}</strong>
      <p>{detail}</p>
    </Panel>
  )
}
