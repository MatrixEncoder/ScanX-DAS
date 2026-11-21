import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Target, Radar, MapPin, FileText, Zap, Github, Shield
} from 'lucide-react'

const navItems = [
  { to: '/app',          icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/app/assess',   icon: Shield,          label: 'Assess' },
  { to: '/app/targets',  icon: Target,          label: 'Targets' },
  { to: '/app/crawls',   icon: Radar,           label: 'Crawls' },
  { to: '/app/endpoints',icon: MapPin,          label: 'Endpoints' },
  { to: '/app/github',   icon: Github,          label: 'GitHub Scan' },
  { to: '/app/reports',  icon: FileText,        label: 'Reports' },
]

export default function Sidebar() {
  return (
    <aside className="sidebar">
      {/* Cyber Blue Wavy Lines Effect Matching the UI Mockup */}
      <svg className="sidebar-waves-bg" viewBox="0 0 220 220" preserveAspectRatio="none">
        <defs>
          <linearGradient id="waveCyanGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00d4ff" stopOpacity="0.4" />
            <stop offset="50%" stopColor="#0284c7" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#0369a1" stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Dynamic layered sine-wave mesh */}
        <path
          d="M-20,180 C40,110 80,210 140,130 C180,70 200,100 240,60"
          fill="none"
          stroke="#00d4ff"
          strokeWidth="1.2"
          strokeOpacity="0.55"
        />
        <path
          d="M-20,190 C35,125 75,205 135,140 C175,85 195,110 240,70"
          fill="none"
          stroke="#00d4ff"
          strokeWidth="1.0"
          strokeOpacity="0.45"
        />
        <path
          d="M-20,200 C30,140 70,200 130,150 C170,100 190,120 240,80"
          fill="none"
          stroke="#00d4ff"
          strokeWidth="0.9"
          strokeOpacity="0.38"
        />
        <path
          d="M-20,210 C25,155 65,195 125,160 C165,115 185,130 240,90"
          fill="none"
          stroke="#00d4ff"
          strokeWidth="0.8"
          strokeOpacity="0.3"
        />
        <path
          d="M-20,218 C20,170 60,190 120,170 C160,130 180,140 240,100"
          fill="none"
          stroke="#00d4ff"
          strokeWidth="0.7"
          strokeOpacity="0.22"
        />
        <path
          d="M-20,225 C15,185 55,185 115,180 C155,145 175,150 240,110"
          fill="none"
          stroke="#00d4ff"
          strokeWidth="0.6"
          strokeOpacity="0.18"
        />
        <path
          d="M-20,230 C10,200 50,180 110,190 C150,160 170,160 240,120"
          fill="none"
          stroke="#00d4ff"
          strokeWidth="0.5"
          strokeOpacity="0.12"
        />
      </svg>

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
          <span style={{ color: 'var(--accent)', fontSize: 12, fontWeight: 700 }}>Scan-X</span>
        </div>
        <div>Security Assessment Platform</div>
        <div>Final Year Project 2026</div>
      </div>
    </aside>
  )
}
