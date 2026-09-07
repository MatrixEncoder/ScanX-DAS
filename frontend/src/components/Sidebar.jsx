import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Target, Radar, MapPin, FileText, Zap, Github, Shield, Crosshair
} from 'lucide-react'

const navItems = [
  { to: '/app',          icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/app/assess',   icon: Shield,          label: 'Assess' },
  { to: '/app/targets',  icon: Target,          label: 'Targets' },
  { to: '/app/crawls',   icon: Radar,           label: 'Crawls' },
  { to: '/app/endpoints',icon: MapPin,          label: 'Endpoints' },
  { to: '/app/github',   icon: Github,          label: 'GitHub Scan' },
  { to: '/app/attack-surface', icon: Crosshair, label: 'Attack Surface' },
  { to: '/app/reports',  icon: FileText,        label: 'Reports' },
]

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <img src="/scanx-logo.png" alt="Scan-X" style={{ height: 40, maxWidth: 100, objectFit: 'contain', marginBottom: 4 }} />
        <div className="logo-sub">Security Assessment v3.0</div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-title">Main</div>
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/app'}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
          <Zap size={12} color="var(--accent)" />
          <span style={{ color: 'var(--accent)', fontSize: 11, fontWeight: 700 }}>Scan-X</span>
        </div>
        <div>Security Assessment Platform</div>
        <div>Final Year Project 2026</div>
      </div>
    </aside>
  )
}
