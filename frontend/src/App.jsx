import { BrowserRouter, Navigate, NavLink, Outlet, Route, Routes } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Predict from './pages/Predict'
import AuditTrail from './pages/AuditTrail'
import Landing from './pages/Landing'

const WORK_NAV = [
  { to: '/', label: 'Landing', eyebrow: 'Overview' },
  { to: '/insights', label: 'Dashboard', eyebrow: 'Dataset pulse' },
  { to: '/simulate', label: 'Predict loan', eyebrow: 'Applicant testing' },
  { to: '/audit', label: 'Audit trail', eyebrow: 'Decision history' },
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
            <em>AI-powered loan decisions</em>
          </span>
        </NavLink>

        <div className="sidebar__group">
          <p className="sidebar__label">Workspace</p>
          <nav className="sidebar__nav">
            {WORK_NAV.map(({ to, label, eyebrow }) => (
              <NavLink key={to} className="nav-card" to={to} end={to === '/'}>
                <span className="nav-card__eyebrow">{eyebrow}</span>
                <span className="nav-card__title">{label}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="sidebar__callout">
          <p>AI model status</p>
          <strong>Operational and ready for bias-aware lending review.</strong>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div>
            <p className="topbar__eyebrow">FairCare AI workspace</p>
            <h1>Bias-aware lending operations</h1>
          </div>
        </header>

        <main className="workspace__content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
