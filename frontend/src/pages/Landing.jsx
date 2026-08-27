import { Link } from 'react-router-dom'
import { Shield, Globe, Github, Crosshair, ArrowRight, Zap } from 'lucide-react'

export default function Landing() {
  return (
    <div className="landing-page">
      <div className="watermark" />
      <nav className="landing-nav">
        <div className="landing-nav-logo">
          <img src="/scanx-logo.png" alt="Scan-X" style={{ height: 36, maxWidth: 120, objectFit: 'contain' }} />
        </div>
        <div className="landing-nav-links">
          <Link to="/app" className="btn btn-primary" style={{ textDecoration: 'none' }}>
            Open Dashboard <ArrowRight size={16} />
          </Link>
        </div>
      </nav>

      <div className="landing-hero">
        <h1>Security Assessment<br />Platform</h1>
        <p>
          Discover endpoints, analyze source code, and correlate vulnerabilities
          — all in one place. Built for penetration testers who need fast,
          reliable reconnaissance.
        </p>
        <div className="landing-actions">
          <Link to="/app" className="btn btn-primary" style={{ textDecoration: 'none' }}>
            <Zap size={18} /> Get Started
          </Link>
          <a href="/api/docs" className="btn btn-ghost" target="_blank" rel="noreferrer" style={{ textDecoration: 'none' }}>
            API Docs
          </a>
        </div>
      </div>

      <div className="landing-features">
        <div className="landing-feature">
          <div className="landing-feature-icon">🌐</div>
          <h3>Web Reconnaissance</h3>
          <p>Deep crawling, form discovery, JavaScript endpoint extraction, and technology fingerprinting.</p>
        </div>
        <div className="landing-feature">
          <div className="landing-feature-icon">📦</div>
          <h3>Repository Analysis</h3>
          <p>40+ security rules detecting secrets, injection, XSS, SSRF, and misconfigurations in source code.</p>
        </div>
        <div className="landing-feature">
          <div className="landing-feature-icon">🔗</div>
          <h3>Correlation Engine</h3>
          <p>Link discovered endpoints to source files and findings with evidence-based confidence scoring.</p>
        </div>
      </div>

      <div className="landing-footer">
        Scan-X — Security Assessment Platform — Final Year Project 2025
      </div>
    </div>
  )
}
