import { BrowserRouter, Navigate, NavLink, Outlet, Route, Routes } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Predict from './pages/Predict'
import AuditTrail from './pages/AuditTrail'
import Landing from './pages/Landing'

const WORK_NAV = [
  { to: '/insights', label: 'Dashboard', eyebrow: 'Overview' },
  { to: '/simulate', label: 'Predict', eyebrow: 'Case review' },
  { to: '/audit', label: 'Audit trail', eyebrow: 'History' },
]

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route element={<WorkLayout />}>
          <Route path="/insights" element={<Dashboard />} />
          <Route path="/simulate" element={<Predict />} />
          <Route path="/predict" element={<Navigate to="/simulate" replace />} />
          <Route path="/audit" element={<AuditTrail />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

function WorkLayout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink className="brand brand--sidebar" to="/">
          <span className="brand__mark">F</span>
          <span>
            <strong>FairCare AI</strong>
            <em>Loan fairness operations</em>
          </span>
        </NavLink>

        <div className="sidebar__group">
          <p className="sidebar__label">Workspace</p>
          <nav className="sidebar__nav">
            {WORK_NAV.map(({ to, label, eyebrow }) => (
              <NavLink key={to} className="nav-card" to={to}>
                <span className="nav-card__title">{label}</span>
                <span className="nav-card__eyebrow">{eyebrow}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="sidebar__callout">
          <p>Model status</p>
          <strong>Ready for review</strong>
          <span>API-backed decisions and audit history.</span>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div>
            <p className="topbar__eyebrow">FairCare AI</p>
            <h1>Decision operations</h1>
          </div>
          <div className="topbar__status">
            <span />
            Operational
          </div>
        </header>

        <main className="workspace__content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
